import simpy
import numpy as np
import csv
import json 
from config import *
from clases import Usuario,Maquina,Recepcionista,Entrenador,Tecnico
from layout import tiempo_desplazamiento, distancia, interpolar_posicion

#para manejar qué y cuando ocurre
class Gimnasio:
    def __init__(self,env,seed=0):
        self.env = env
        self.rng = np.random.default_rng(seed)

        self.replica_log = 1
        self.secuencia_log = 0
        self.eventos_log = []
        self.aviso_reparacion = self.env.event() #para avisar que tecnico termina reparacion de maquina que estan esperando

        self.usuarios_dentro = 0
        self.total_llegadas = 0
        self.admitidos = 0
        self.rechazados = 0
        self.area_ocupacion = 0
        self.tiempo_capacidad = 0
        self.ultimo_cambio_ocupacion = 0
        self.espera_operacional = 0

        self.maquinas = []
        self.crear_maquinas()

        self.recepcionistas = []
        self.cola_recepcion = simpy.PriorityStore(env)
        self.contador_tareas_recepcion = 0
        self.crear_recepcionistas()
        self.entrenadores = []
        self.cola_entrenadores = simpy.Store(env)
        self.crear_entrenadores()

        self.agua = simpy.Container(env,capacity=CAPACIDAD_AGUA,init=CAPACIDAD_AGUA)
        self.toallas = simpy.Container(env,capacity=CAPACIDAD_TOALLAS,init=CAPACIDAD_TOALLAS)

        self.punto_agua = simpy.Resource(env,capacity=1)
        self.punto_toallas = simpy.Resource(env,capacity=1)

    def registrar_log(self, evento, usuario=None, tipo_entidad="user", identificador="", ubicacion=None, recurso="", detalles=None):
        #atualizar numerodel evento
        self.secuencia_log += 1
        perfil = ""
        if usuario is not None:
            perfil = PERFILES_LOG[usuario.perfil]
            if tipo_entidad == "user":
                identificador = f"U-{usuario.id:04d}"
            if ubicacion is None:
                ubicacion = usuario.posicion
        #convertir tiempo
        segundos_totales = round(self.env.now * 60)
        hora = 7 + segundos_totales // 3600
        minuto = (segundos_totales % 3600) // 60
        segundo = segundos_totales % 60
        hora_reloj = f"{hora:02d}:{minuto:02d}:{segundo:02d}"
        tiempo = f"{self.env.now:.4f}".replace(".", ",")
        if ubicacion is None:
            celda = ""
        elif isinstance(ubicacion, tuple):
            celda = json.dumps({"x": round(float(ubicacion[0]), 4), "y": round(float(ubicacion[1]), 4)})
        else:
            celda = str(float(ubicacion)).replace(".", ",")
        if detalles is None:
            detalles = {}
        # Agregar evento
        self.eventos_log.append([self.replica_log, self.secuencia_log, tiempo,
            hora_reloj, evento, tipo_entidad, identificador, perfil, celda,
            recurso, json.dumps(detalles, ensure_ascii=False, sort_keys=True)])

    def guardar_log(self, nombre_archivo = "log_jornada.csv", generar_log=True):
        if not generar_log:
            return
        columnas = ["replication", "event_seq", "minute", "clock_time", "event", "entity_type", "entity_id", "profile", "location", "resource", "details"]
        with open(nombre_archivo, "w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.writer(archivo, delimiter=";")
            escritor.writerow(columnas)
            escritor.writerows(self.eventos_log)

    def identificador_maquina(self, maquina):
        nombre = EJERCICIOS_LOG[maquina.tipo]
        return f"{nombre}-{maquina.id:02d}"

    def crear_maquinas(self):
        for tipo,posiciones in MAQUINAS.items():
            for i,posicion in enumerate(posiciones):
                maquina = Maquina(self.env,tipo,i+1,posicion)
                self.maquinas.append(maquina)

    def notificar_reparacion(self):
        aviso = self.aviso_reparacion
        self.aviso_reparacion = self.env.event()
        if not aviso.triggered:
            aviso.succeed()

    def esperar_operatividad(self, usuario, ejercicios, tolerancia=None):
        inicio_espera = self.env.now
        limite = min(usuario.hora_limite, CIERRE)
        self.registrar_log(evento="operational_wait_start", usuario=usuario, detalles={"exercises": [EJERCICIOS_LOG[e] for e in ejercicios],"tolerance": tolerancia})
        while True:
            #revisar limites de tiempo
            if self.env.now >= limite:
                if self.env.now >= CIERRE:
                    resultado_final = "cierre"
                else:
                    resultado_final = "permanencia máxima"
            else:
                #revisa si hay alguna amquina de ese tipo operayiva
                hay_operativa = False
                for ejercicio in ejercicios:
                    maquina = self.seleccionar_maquina(usuario, ejercicio)
                    if maquina is not None:
                        hay_operativa = True
                        break
                if hay_operativa:
                    resultado_final = "disponible"
                else:
                    tiempo_disponible = limite - self.env.now
                    #tolerancia estandar
                    if tolerancia is not None:
                        espera_acumulada = self.env.now - inicio_espera
                        restante = tolerancia - espera_acumulada
                        if restante <= 1e-9:
                            resultado_final = "tolerancia"
                            break

                        tiempo_disponible = min(tiempo_disponible, restante)
                    #esperar que se arregle o limite de tiempo
                    aviso = self.aviso_reparacion
                    inicio = self.env.now
                    yield aviso | self.env.timeout(tiempo_disponible)
                    espera = self.env.now - inicio

                    usuario.espera_operacional += espera
                    usuario.espera_maquinas += espera
                    usuario.espera_total += espera
                    #comprobar condiciones de nuevo
                    continue
            break
        self.registrar_log(evento="operational_wait_end", usuario=usuario, detalles={"exercises": [EJERCICIOS_LOG[e] for e in ejercicios], "duration": round(self.env.now - inicio_espera, 4), "result": resultado_final})
        return resultado_final

    def registrar_cambio_ocupacion(self):
        ahora = min(self.env.now, CIERRE)
        tiempo = ahora- self.ultimo_cambio_ocupacion
        if tiempo > 0:
            self.area_ocupacion += self.usuarios_dentro * tiempo
            if self.usuarios_dentro == CAPACIDAD_GIMNASIO:
                self.tiempo_capacidad += tiempo
            self.ultimo_cambio_ocupacion = ahora

    def omitir_ejercicio_express(self, usuario, ejercicio, resultado):
        if usuario.perfil == "X" and resultado == "tolerancia":
            usuario.pendientes.remove(ejercicio)
            usuario.omitidos.append(ejercicio)
            self.registrar_log(evento="exercise_omitted", usuario=usuario, recurso=EJERCICIOS_LOG[ejercicio], detalles={"reason": "tolerance"})

    def seleccionar_maquina(self, usuario, ejercicio):
        maquinas_disponibles = []
        for maquina in self.maquinas:
            if maquina.tipo == ejercicio and maquina.operativa:
                maquinas_disponibles.append(maquina)
        #si no hay operatvias
        if len(maquinas_disponibles) == 0:
            return None
        #busco las libres
        maquinas_libres = []
        for maquina in maquinas_disponibles:
            if maquina.recurso.count == 0 and len(maquina.recurso.queue) == 0:
                maquinas_libres.append(maquina)
        #si hay libres, debo elegir la que esta mas cerca
        if len(maquinas_libres) > 0:
            mejor_maquina = None
            menor_distancia = float("inf")
            for maquina in maquinas_libres:
                dist = distancia(usuario.posicion, maquina.posicion)
                if dist < menor_distancia: 
                    mejor_maquina = maquina
                    menor_distancia =  dist
                elif dist == menor_distancia:
                    if maquina.posicion < mejor_maquina.posicion:
                        mejor_maquina = maquina
            return mejor_maquina
        #caso de todas ocupadas
        mejor_maquina = None
        mejor_criterio = None
        for maquina in maquinas_disponibles:
            dist = distancia(usuario.posicion, maquina.posicion)
            cola = len(maquina.recurso.queue)
            if usuario.perfil == "F":
                criterio = (cola, dist, maquina.posicion)
            else:
                criterio = (dist, maquina.posicion)
            if mejor_criterio is None or criterio < mejor_criterio:
                mejor_maquina = maquina
                mejor_criterio = criterio
        return mejor_maquina

    def seleccionar_siguiente_ejercicio(self, usuario):
        if len(usuario.pendientes) == 0:
            return None, None
        if usuario.perfil in ["E", "X", "I"]:
            ejercicio = usuario.pendientes[0]
            maquina = self.seleccionar_maquina(usuario, ejercicio)
            return ejercicio, maquina
        #para el flexible
        opciones = []
        for i, ejercicio in enumerate(usuario.pendientes): 
            maquina = self.seleccionar_maquina(usuario, ejercicio)
            if maquina is not None:
                libre = (maquina.recurso.count == 0 and len(maquina.recurso.queue) == 0)
                espera_acumulada = usuario.espera_por_ejercicio.get(ejercicio,0)
                tolerancia_restante = usuario.tolerancia-espera_acumulada
                if libre or tolerancia_restante > 1e-9:
                    opciones.append((0 if libre else 1, len(maquina.recurso.queue), distancia(usuario.posicion,maquina.posicion), maquina.posicion, i, ejercicio, maquina))
        #caso de ningun ejercicio tiene maquina operat
        if len(opciones) == 0:
            return None, None
        mejor = min(opciones)
        return mejor[5], mejor[6]        

    def duracion_fuerza(self, perfil, ejercicio):
        grupo = GRUPO_FUERZA[ejercicio]
        parametros = PARAMETROS_FUERZA[grupo][perfil]
        if perfil == "E":
            forma, escala = parametros
            return self.rng.gamma(forma, escala)
        elif perfil == "X":
            alpha, beta, minimo, maximo = parametros
            return minimo + (maximo-minimo) * self.rng.beta(alpha, beta)
        elif perfil == "F":
            forma, escala = parametros
            return self.rng.gamma(forma, escala)
        elif perfil == "I":
            forma, escala = parametros
            return self.rng.gamma(forma, escala)

    def intentar_ejercicio(self, usuario, ejercicio, maquina, tolerancia=None):
        #primero se revisa si el usuario tiene el tiempo suficiente 
        if self.env.now >= CIERRE:
            return "cierre"
        if self.env.now >= usuario.hora_limite:
            return "permanencia máxima"
        if maquina is None:
            return "sin_maquina_operativa"
        
        #en caso de que pueda, mover al usuario
        llego = yield self.env.process(self.mover_usuario(usuario, maquina.posicion))
        if not llego:
            if self.env.now >= CIERRE:
                return "cierre"
            return "permanencia máxima"
        #revisar que cuado llege tenga tiempo aun
        if self.env.now >= CIERRE:
            return "cierre"
        if self.env.now >= usuario.hora_limite:
            return "permanencia máxima"
        if not maquina.operativa:
            return "maquina_averiada"

        #entonce sis tiene el tiempo, vemos el tiempoq ue puede esperar
        if tolerancia is None:
            tiempo_tolerancia = usuario.tolerancia
        else:
            tiempo_tolerancia = tolerancia

        maquina_libre = maquina.recurso.count == 0 and len(maquina.recurso.queue) == 0
        if maquina_libre:
            tiempo_tolerancia = float("inf")
        elif tiempo_tolerancia <= 1e-9:
            return "tolerancia"

        tiempo_permanencia = usuario.hora_limite-self.env.now
        tiempo_cierre = CIERRE-self.env.now
        tiempo_dispo = min(tiempo_tolerancia,tiempo_permanencia,tiempo_cierre)

        if tiempo_dispo <= 0:
            if tiempo_permanencia <= 0:
                return "permanencia máxima"
            return "cierre"
        inicio_espera = self.env.now
        with maquina.recurso.request() as solicitud_maquina:
            if not solicitud_maquina.triggered:
                self.registrar_log(evento="machine_queue_enter", usuario=usuario, recurso=self.identificador_maquina(maquina), detalles={"machine_type": EJERCICIOS_LOG[maquina.tipo], "queue_length": len(maquina.recurso.queue)})
            resultado = yield solicitud_maquina | self.env.timeout(tiempo_dispo)
            espera = self.env.now - inicio_espera
            usuario.espera_maquinas = usuario.espera_maquinas + espera
            usuario.espera_total = usuario.espera_total + espera
            if self.env.now >= CIERRE:
                return "cierre"
            if self.env.now >= usuario.hora_limite:
                return "permanencia máxima"
            if solicitud_maquina not in resultado:
                if tiempo_dispo == tiempo_tolerancia:
                    return "tolerancia"
                elif tiempo_dispo == tiempo_permanencia:
                    return "permanencia máxima"
                else:
                    return "cierre"
            #caso en que la maquina se echa a perder mientras espera
            if not maquina.operativa:
                return "maquina_averiada"

            self.registrar_log(evento="machine_acquired", usuario=usuario, recurso=self.identificador_maquina(maquina), detalles={"machine_type": EJERCICIOS_LOG[maquina.tipo], "queue_wait": round(float(espera), 4)})
            #si pasa todo lo anterior, es porqie pieede realizar ele ejercicio, primero se asigna la maquina
            maquina.usuario_actual = usuario.id
            pedido = None
            #en caso de neecsitar asistencia, se llama al entrenador
            if usuario.asistencia.get(ejercicio, False):
                self.registrar_log(evento="trainer_request", usuario=usuario, recurso=self.identificador_maquina(maquina))
                pedido = yield self.env.process(self.solicitar_entrenador(usuario, maquina))
                #caso de cuando no llega un entrenador antes del lmite de tempo
                if pedido is None:
                    maquina.usuario_actual = None
                    if self.env.now >= CIERRE:
                        return "cierre"
                    return "permanencia máxima"
            #comenzar ejerciico
            duracion = self.duracion_fuerza(usuario.perfil, ejercicio)
            self.registrar_log(evento="exercise_start", usuario=usuario, recurso=self.identificador_maquina(maquina),detalles={"machine_type": EJERCICIOS_LOG[maquina.tipo],"duration": round(float(duracion), 4),"assistance": bool(usuario.asistencia.get(ejercicio, False))})
            yield self.env.timeout(duracion)
            #registrar
            usuario.completados.append(ejercicio)
            usuario.pendientes.remove(ejercicio)
            maquina.tiempo_uso += duracion
            maquina.usuario_actual = None
            self.registrar_log(evento="exercise_end", usuario=usuario, recurso=self.identificador_maquina(maquina), detalles={"machine_type": EJERCICIOS_LOG[maquina.tipo], "duration": round(float(duracion), 4)})
            #liberar al entrenador en caso de que se haya neesitado
            if pedido is not None:
                pedido["fin"].succeed()
            return "completado"

    def crear_entrenadores(self):
        for i in range(N_ENTRENADORES):
            entrenador = Entrenador(i+1, self.velocidad_trabajador("entrenador"), CELDA_ENTRENADORES)
            self.entrenadores.append(entrenador)
            self.env.process(self.proceso_entrenador(entrenador))

    def retirar_toallas(self,usuario):
        limite = min(usuario.hora_limite,CIERRE)
        if self.env.now >= limite:
            return False
        llego = yield self.env.process(self.mover_usuario(usuario, CELDA_TOALLAS))
        if not llego:
            return False
        if self.env.now >= limite:
            return False
        inicio_espera = self.env.now
        with self.punto_toallas.request() as req:
            tiempo_disponible = limite-self.env.now
            resultado = yield req | self.env.timeout(tiempo_disponible)
            espera = self.env.now-inicio_espera
            usuario.espera_toallas += espera
            usuario.espera_total += espera
            if req not in resultado:
                return False
            if self.toallas.level <= 0:
                self.registrar_log(evento="towels_stockout", tipo_entidad="supply", identificador="towels", ubicacion=CELDA_TOALLAS, recurso="towels", detalles={"remaining_stock": self.toallas.level})
                return False
            cantidad = min(MAX_TOALLAS_RETIRO,int(self.toallas.level))
            stock_anterior = self.toallas.level
            yield self.toallas.get(cantidad)
            yield self.env.timeout(TIEMPO_RETIRO_TOALLAS)
            usuario.toallas += cantidad
            self.registrar_log(evento="towels_pickup_end", usuario=usuario, recurso="towels", detalles={"amount": cantidad, "pickup_duration": TIEMPO_RETIRO_TOALLAS, "stock_before": stock_anterior, "remaining_stock": self.toallas.level, "towels_personal": usuario.toallas})
        return True
    
    def preparar_ejercicio(self,usuario):
        if usuario.toallas >= TOALLAS_MINIMAS:
            return True
        return (yield self.env.process(self.retirar_toallas(usuario)))

    def consumo_agua(self,usuario,ejercicio):
        categoria = CATEGORIA_EJERCICIO[ejercicio]
        forma,escala = CONSUMO_AGUA[usuario.perfil][categoria]
        requerido = self.rng.gamma(forma,escala)
        consumido = min(requerido,usuario.agua)
        usuario.agua -= consumido
        if usuario.agua < 1e-9:
            usuario.agua = 0
        self.registrar_log(evento="water_consumption", usuario=usuario, recurso=EJERCICIOS_LOG[ejercicio], detalles={"water_required_liters": round(float(requerido), 4), "water_consumed_liters": round(float(consumido), 4), "bottle_level_liters": round(float(usuario.agua), 4)})
        if usuario.agua == 0:
            yield self.env.process(self.rellenar_agua(usuario))

    def rellenar_agua(self,usuario):
        limite = min(usuario.hora_limite,CIERRE)
        if self.env.now >= limite:
            return False
        llego = yield self.env.process(self.mover_usuario(usuario, CELDA_AGUA))
        if not llego:
            return False
        if self.env.now >= limite:
            return False
        inicio_espera = self.env.now
        with self.punto_agua.request() as req:
            tiempo_disponible = limite-self.env.now
            resultado = yield req | self.env.timeout(tiempo_disponible)
            espera = self.env.now-inicio_espera
            usuario.espera_agua += espera
            usuario.espera_total += espera
            if req not in resultado:
                return False
            if self.agua.level <= 0:
                self.registrar_log(evento="water_stockout", tipo_entidad="supply", identificador="water", ubicacion=CELDA_AGUA, recurso="water", detalles={"remaining_stock": self.agua.level})
                return False
            cantidad = min(usuario.capacidad_botella-usuario.agua, self.agua.level)
            stock_anterior = self.agua.level
            yield self.agua.get(cantidad)
            yield self.env.timeout(TIEMPO_RETIRO_AGUA)
            usuario.agua += cantidad
            self.registrar_log(evento="water_pickup_end", usuario=usuario, recurso="water", detalles={"amount": round(float(cantidad), 4), "pickup_duration": TIEMPO_RETIRO_AGUA, "stock_before": round(float(stock_anterior), 4), "remaining_stock": round(float(self.agua.level), 4), "bottle_level_liters": round(float(usuario.agua), 4)})
        return True

    def intentar_estandar(self, usuario, ejercicio):
        espera_inicial = usuario.espera_maquinas
        while True:
            #lo que le queda de tolerancia
            espera_usada = usuario.espera_maquinas - espera_inicial
            tolerancia_restante = max(0, usuario.tolerancia - espera_usada)
            maquina = self.seleccionar_maquina(usuario, ejercicio)
            #caso en que no hay maquinas operativas
            if maquina is None:
                resultado = yield self.env.process(self.esperar_operatividad(usuario, [ejercicio], tolerancia_restante))
                if resultado == "disponible":
                    continue
                return resultado
            resultado = yield self.env.process(self.intentar_ejercicio(usuario, ejercicio, maquina, tolerancia_restante))
            if resultado == "maquina_averiada":
                continue
            return resultado

    def rutina_fuerza(self,usuario):
        if usuario.perfil == "E":
            for ejercicio in usuario.rutina:
                if ejercicio not in usuario.pendientes:
                    continue
                puede_continuar = yield self.env.process(self.preparar_ejercicio(usuario))
                if not puede_continuar:
                    return
                resultado = yield self.env.process(self.intentar_estandar(usuario, ejercicio))
                if resultado == "completado":
                    yield self.env.process(self.finalizar_ejercicio(usuario,ejercicio))
                elif resultado == "tolerancia":
                    self.registrar_log(evento="exercise_postponed", usuario=usuario, recurso=EJERCICIOS_LOG[ejercicio], detalles={"attempt": 1})
                if resultado in ["cierre","permanencia máxima"]:
                    return
            pendientes_reintento = [ejercicio for ejercicio in usuario.rutina if ejercicio in usuario.pendientes]
            for ejercicio in pendientes_reintento:
                puede_continuar = yield self.env.process(self.preparar_ejercicio(usuario))
                if not puede_continuar:
                    return
                resultado = yield self.env.process(self.intentar_estandar(usuario, ejercicio))
                if resultado == "completado":
                    #descontar insumos
                    yield self.env.process(self.finalizar_ejercicio(usuario, ejercicio))
                elif resultado == "tolerancia":
                    usuario.cardio_permitido = False
                    self.registrar_log(evento="standard_retry_failed", usuario=usuario, recurso=EJERCICIOS_LOG[ejercicio], detalles={"cardio_forbidden": True})
                    for pendiente in usuario.pendientes.copy():
                        usuario.pendientes.remove(pendiente)
                        usuario.omitidos.append(pendiente)
                        self.registrar_log(evento="exercise_omitted", usuario=usuario, recurso=EJERCICIOS_LOG[pendiente], detalles={"reason": "standard_retry_failed"})
                    return 
                elif resultado in ["cierre", "permanencia máxima"]:
                    return
            return
                
        if usuario.perfil == "X":
            while len(usuario.pendientes) > 0:
                ejercicio = usuario.pendientes[0]
                puede_continuar = yield self.env.process(
                    self.preparar_ejercicio(usuario))
                if not puede_continuar:
                    return
                maquina = self.seleccionar_maquina(usuario,ejercicio)
                if maquina is None:
                    usuario.pendientes.remove(ejercicio)
                    usuario.omitidos.append(ejercicio)
                    self.registrar_log(evento="exercise_omitted", usuario=usuario, recurso=EJERCICIOS_LOG[ejercicio], detalles={"reason": "no_operational_machine"})
                    continue
                resultado = yield self.env.process(self.intentar_ejercicio(usuario,ejercicio,maquina))

                if resultado == "completado":
                    yield self.env.process(self.finalizar_ejercicio(usuario,ejercicio))

                elif resultado == "tolerancia":
                    self.omitir_ejercicio_express(usuario, ejercicio, resultado)

                elif resultado in ["cierre","permanencia máxima"]:
                    return

            return
        
        if usuario.perfil == "F":
            while len(usuario.pendientes) > 0:
                ejercicio,maquina = self.seleccionar_siguiente_ejercicio(usuario)
                if ejercicio is None:
                    #revisar si hay maquinas operativas
                    hay_operativa = False
                    for pendiente in usuario.pendientes:
                        maquina_disponible = self.seleccionar_maquina(usuario, pendiente)
                        if maquina_disponible is not None:
                            hay_operativa = True
                            break
                    if not hay_operativa: 
                        resultado = yield self.env.process(self.esperar_operatividad(usuario, usuario.pendientes))
                        if resultado == "disponible":
                            continue
                        return
                    #hay maquinas operativas pero no alcanza la tolerancia
                    for pendiente in usuario.pendientes:
                        self.registrar_log(evento="exercise_pending", usuario=usuario, recurso=EJERCICIOS_LOG[pendiente], detalles={"reason": "no_available_alternative"})
                    return
                puede_continuar = yield self.env.process(self.preparar_ejercicio(usuario))
                if not puede_continuar:
                    return
                maquina = self.seleccionar_maquina(usuario,ejercicio)
                espera_acumulada = usuario.espera_por_ejercicio.get(ejercicio,0)
                tolerancia_restante = usuario.tolerancia-espera_acumulada
                if tolerancia_restante < 1e-9:
                    tolerancia_restante = 0
                espera_antes = usuario.espera_maquinas
                resultado = yield self.env.process(
                    self.intentar_ejercicio(usuario, ejercicio, maquina,tolerancia_restante))
                if resultado == "completado":
                    yield self.env.process(self.finalizar_ejercicio(usuario,ejercicio))
                espera_intento = usuario.espera_maquinas-espera_antes
                usuario.espera_por_ejercicio[ejercicio] = min(usuario.tolerancia, espera_acumulada+espera_intento)
                if resultado == "tolerancia":
                    self.registrar_log(evento="exercise_wait_limit", usuario=usuario, recurso=EJERCICIOS_LOG[ejercicio], detalles={"exercise_wait_accumulated": round(float(usuario.espera_por_ejercicio[ejercicio]), 4)})
                if resultado in ["cierre","permanencia máxima"]:
                    return
            return

        if usuario.perfil == "I":
            while len(usuario.pendientes) > 0:
                ejercicio = usuario.pendientes[0]
                puede_continuar = yield self.env.process(self.preparar_ejercicio(usuario))
                if not puede_continuar:
                    return
                maquina = self.seleccionar_maquina(usuario,ejercicio)
                if maquina is None:
                    return
                resultado = yield self.env.process(
                    self.intentar_ejercicio(usuario, ejercicio, maquina, float("inf")))
                if resultado == "completado":
                    yield self.env.process(self.finalizar_ejercicio(usuario,ejercicio))
                if resultado in ["cierre","permanencia máxima"]:
                    return
            return


    def proceso_entrenador(self, entrenador):
        while True:
            pedido = yield self.cola_entrenadores.get()
            if pedido["cancelado"]:
                continue
            usuario = pedido["usuario"]
            maquina = pedido["maquina"]
            limite = min(usuario.hora_limite, CIERRE)
            if self.env.now >= limite:
                continue
            entrenador.ocupado = True
            entrenador.tarea_actual = "asistencia"
            origen = entrenador.posicion
            destino = maquina.posicion
            tiempo = tiempo_desplazamiento(origen, destino, entrenador.velocidad)
            inicio = self.env.now
            self.registrar_log(evento="worker_travel_start", tipo_entidad="worker", identificador=f"PT-{entrenador.id:02d}", ubicacion=origen, recurso="trainers", detalles={"origin": origen, "destination": destino, "duration": round(float(tiempo), 4)})
            #esperr vosje completo o que se cancele
            viaje = self.env.timeout(tiempo)
            resultado = yield (viaje | pedido["cancelacion"])
            tiempo_recorrido = self.env.now - inicio
            #si el usuario cancelo durante el viaje
            if (pedido["cancelado"] or pedido["cancelacion"] in resultado or self.env.now >= limite):
                if tiempo > 0:
                    fraccion = min(1, tiempo_recorrido / tiempo)
                else:
                    fraccion = 1

                entrenador.posicion = interpolar_posicion(origen, destino, fraccion)
                self.registrar_log(evento="worker_travel_interrupted", tipo_entidad="worker", identificador=f"PT-{entrenador.id:02d}", ubicacion=entrenador.posicion, recurso="trainers", detalles={"origin": origen, "destination": destino, "elapsed_time": round(float(tiempo_recorrido), 4), "fraction": round(float(fraccion), 4), "user_id": f"U-{usuario.id:04d}"})
                entrenador.ocupado = False
                entrenador.tarea_actual = None
                continue

            # si el entrenador completa el viaje
            entrenador.posicion = destino

            self.registrar_log(evento="worker_travel_end", tipo_entidad="worker", identificador=f"PT-{entrenador.id:02d}", ubicacion=destino, recurso="trainers", detalles={"origin": origen, "destination": destino, "duration": round(float(tiempo), 4)})
            self.registrar_log(evento="trainer_arrival",usuario=usuario, tipo_entidad="worker", identificador=f"PT-{entrenador.id:02d}", ubicacion=destino, recurso=self.identificador_maquina(maquina), detalles={"user_id": f"U-{usuario.id:04d}", "user_wait": round(float(self.env.now - pedido["inicio_espera"]), 4)})

            pedido["llegada"].succeed(entrenador)
            #esperar a que termine la ayuda del entrenador almusuario
            yield pedido["fin"]
            self.registrar_log(evento="trainer_assistance_end", usuario=usuario, tipo_entidad="worker", identificador=f"PT-{entrenador.id:02d}", ubicacion=entrenador.posicion, recurso=self.identificador_maquina(maquina))
            entrenador.ocupado = False
            entrenador.tarea_actual = None
           
    def solicitar_entrenador(self, usuario, maquina):
        limite = min(usuario.hora_limite, CIERRE)
        tiempo_disponible = limite - self.env.now
        if tiempo_disponible <= 0:
            return None
        pedido = {"usuario": usuario, "maquina": maquina, "llegada": self.env.event(), "fin": self.env.event(), "cancelacion": self.env.event(), "cancelado": False, "inicio_espera": self.env.now}
        inicio_espera = self.env.now
        yield self.cola_entrenadores.put(pedido)
        resultado = yield (pedido["llegada"] | self.env.timeout(tiempo_disponible))
        espera = self.env.now - inicio_espera
        usuario.espera_entrenador += espera
        usuario.espera_total += espera
        #caso de que el user cancela porque alcanzo su limite
        if pedido["llegada"] not in resultado or self.env.now >= limite:
            pedido["cancelado"] = True
            #avisar al entrenador
            if not pedido["cancelacion"].triggered:
                pedido["cancelacion"].succeed()
            self.registrar_log(evento="trainer_request_cancelled", usuario=usuario, recurso=self.identificador_maquina(maquina), detalles={"reason": "time_limit", "wait": round(float(espera), 4)})
            #si el entrenador ya estaba en la maquina, queda libre
            if pedido["llegada"].triggered and not pedido["fin"].triggered:
                pedido["fin"].succeed()
            return None
        return pedido
            
    def crear_recepcionistas(self):
        for i in range(N_RECEPCIONISTAS):
            recepcionista = Recepcionista(i+1,self.velocidad_trabajador("recepcionista"),CELDA_RECEPCION)
            self.recepcionistas.append(recepcionista)
            self.env.process(self.proceso_recepcionista(recepcionista))

    def velocidad_usuario(self,perfil):
        minimo,moda,maximo = VELOCIDADES[perfil]
        return self.rng.triangular(minimo,moda,maximo)

    def tiempo_registro(self,perfil):
        if perfil == "E" or perfil == "F":
            if self.rng.random() < 0.85:
                return self.rng.gamma(10,0.16)
            return self.rng.lognormal(1.05,0.22)
        if perfil == "X":
            return min(2.2,self.rng.lognormal(0.05,0.28))
        if perfil == "I":
            if self.rng.random() < 0.75:
                return self.rng.gamma(9,0.25)
            return self.rng.lognormal(1.25,0.20)

    def velocidad_trabajador(self,tipo):
        minimo,moda,maximo = VELOCIDADES_TRABAJADORES[tipo]
        return self.rng.triangular(minimo,moda,maximo)

    def tasa_actual(self,perfil,tiempo):
        for inicio,fin,tasa in TASAS_LLEGADA[perfil]:
            if inicio <= tiempo < fin:
                return tasa,fin
        return None,None

    def iniciar(self):
        for perfil in ["E","X","F","I"]:
            self.env.process(self.llegadas(perfil))

    def llegadas(self,perfil):
        while self.env.now < FIN_ADMISION:
            tasa,fin_bloque = self.tasa_actual(perfil,self.env.now)
            if tasa is None:
                break
            tiempo = self.rng.exponential(60/tasa)
            if self.env.now+tiempo >= fin_bloque:
                yield self.env.timeout(fin_bloque-self.env.now)
                continue
            yield self.env.timeout(tiempo)
            if self.env.now >= FIN_ADMISION:
                break
            self.total_llegadas += 1
            usuario = Usuario(self.total_llegadas,perfil,self.env.now,self.velocidad_usuario(perfil))
            self.env.process(self.proceso_usuario(usuario))

    def proceso_usuario(self,usuario):
        self.registrar_log(evento="arrival", usuario=usuario, detalles={"walking_speed_m_per_min": round(float(usuario.velocidad), 4)})
        if self.usuarios_dentro >= CAPACIDAD_GIMNASIO:
            self.rechazados += 1
            self.registrar_log(evento="rejection_capacity", usuario=usuario, detalles={"capacity": CAPACIDAD_GIMNASIO, "occupancy": self.usuarios_dentro})
            return
        self.registrar_cambio_ocupacion()
        usuario.admitido = True
        self.admitidos += 1
        self.usuarios_dentro += 1

        self.configurar_usuario(usuario)
        self.registrar_log(evento="admission", usuario=usuario, detalles={"occupancy": self.usuarios_dentro})
        for destino in [CELDA_PASO, CELDA_RECEPCION]:
            llego = yield self.env.process(self.mover_usuario(usuario, destino))
            if not llego:
                yield self.env.process(self.salir_usuario(usuario))
                return
            
        yield self.env.process(self.registrar_usuario(usuario))
        
        if self.env.now >= min(usuario.hora_limite, CIERRE):
            yield self.env.process(self.salir_usuario(usuario))
            return

        for destino in [CELDA_PASO, CELDA_INICIO_ENTRENAMIENTO]:
            llego = yield self.env.process(self.mover_usuario(usuario, destino))
            if not llego:
                yield self.env.process(self.salir_usuario(usuario))
                return

        self.registrar_log(evento="routine_start", usuario=usuario, detalles={"routine": usuario.tipo_rutina, "exercise_sequence": [EJERCICIOS_LOG[e] for e in usuario.rutina], "cardio_planned": bool(usuario.cardio_planificado)})

        yield self.env.process(self.rutina_fuerza(usuario))

        self.registrar_log(evento="strength_end", usuario=usuario, detalles={"completed": [EJERCICIOS_LOG[e] for e in usuario.completados],"pending": [EJERCICIOS_LOG[e] for e in usuario.pendientes], "omitted": [EJERCICIOS_LOG[e] for e in usuario.omitidos]})

        yield self.env.process(self.salir_usuario(usuario))


    def mover_usuario(self, usuario, destino, respetar_limite=True):
        origen = usuario.posicion
        tiempo = tiempo_desplazamiento(origen, destino, usuario.velocidad)
        #salida no se interrumpe por estos limites
        if respetar_limite:
            limite = min(usuario.hora_limite, CIERRE)
            if self.env.now >= limite:
                return False
        self.registrar_log(evento="user_travel_start", usuario=usuario, detalles={"origin": origen, "destination": destino, "distance_m": round(float(distancia(origen, destino)), 4), "duration": round(float(tiempo), 4), "speed_m_per_min": round(float(usuario.velocidad), 4)})
        #cuanto tiempo puede desplazarse
        tiempo_disponible = tiempo
        if respetar_limite:
            tiempo_disponible = min(tiempo, limite - self.env.now)
        yield self.env.timeout(tiempo_disponible)
        #caso fvorable, se completa desplazamiento
        if tiempo_disponible >= tiempo:
            usuario.posicion = destino
            self.registrar_log(evento="user_travel_end", usuario=usuario, detalles={"origin": origen, "destination": destino, "duration": round(float(tiempo), 4)})
            return True

        #caso rn que se interrumpio el desplazamiento
        fraccion = tiempo_disponible / tiempo
        usuario.posicion = interpolar_posicion(origen, destino, fraccion)
        motivo = "permanencia"
        if self.env.now >= CIERRE:
            motivo = "cierre"
        self.registrar_log(evento="user_travel_interrupted", usuario=usuario, detalles={"origin": origen, "destination": destino, "elapsed_time": round(float(tiempo_disponible), 4), "planned_duration": round(float(tiempo), 4), "fraction": round(float(fraccion), 4), "reason": motivo})
        return False

    def salir_usuario(self, usuario):
        for destino in [CELDA_INICIO_ENTRENAMIENTO, CELDA_PASO, CELDA_ACCESO]:
            yield self.env.process(self.mover_usuario(usuario, destino, respetar_limite=False))
        self.registrar_cambio_ocupacion()
        self.usuarios_dentro = self.usuarios_dentro -1
        usuario.hora_salida = self.env.now
        self.registrar_log(evento="exit", usuario=usuario,
            detalles={"occupancy": self.usuarios_dentro, "wait_operational": round(usuario.espera_operacional, 4), "stay": round(self.env.now - usuario.hora_llegada, 4), "planned": len(usuario.rutina),
                "completed": len(usuario.completados), "omitted": len(usuario.omitidos), "total_wait": round(usuario.espera_total, 4),
                "wait_machine": round(usuario.espera_maquinas, 4), "wait_reception": round(usuario.espera_recepcion, 4), "wait_assistance": round(usuario.espera_entrenador, 4),
                "towel_wait": round(usuario.espera_toallas, 4), "water_wait": round(usuario.espera_agua, 4)})

    def registrar_usuario(self,usuario):
        self.contador_tareas_recepcion += 1
        fin = self.env.event()
        tarea = (PRIORIDAD_REGISTRO,self.contador_tareas_recepcion,"registro",usuario,fin,self.env.now)
        yield self.cola_recepcion.put(tarea)
        yield fin


    def proceso_recepcionista(self,recepcionista):
        while True:
            prioridad,orden,tipo,usuario,fin,inicio_espera = yield self.cola_recepcion.get()
            recepcionista.ocupado = True
            recepcionista.tarea_actual = tipo
            if tipo == "registro":
                espera = self.env.now-inicio_espera
                usuario.espera_recepcion += espera
                usuario.espera_total += espera
                self.registrar_log(evento="registration_start", usuario=usuario, recurso=f"R-{recepcionista.id:02d}", detalles={"queue_wait": round(float(espera), 4)})
                duracion = self.tiempo_registro(usuario.perfil)
                yield self.env.timeout(duracion)
                usuario.toallas = TOALLAS_INICIALES
                self.generar_asistencias(usuario)
                self.registrar_log(evento="registration_end", usuario=usuario, recurso=f"R-{recepcionista.id:02d}", detalles={"duration": round(float(duracion), 4), "towels": usuario.toallas})
            recepcionista.ocupado = False
            recepcionista.tarea_actual = None
            fin.succeed()

    def configurar_usuario(self,usuario):
        parametros = PARAMETROS_PERFIL[usuario.perfil]

        usuario.permanencia_maxima = parametros["permanencia"]
        usuario.tolerancia = parametros["tolerancia"]
        usuario.capacidad_botella = parametros["botella"]
        usuario.agua = usuario.capacidad_botella
        usuario.hora_limite = usuario.hora_llegada+usuario.permanencia_maxima

        usuario.cardio_planificado = self.rng.random() < parametros["p_cardio"]
        usuario.cardio_permitido = True

        usuario.tipo_rutina = self.generar_tipo_rutina(usuario.perfil)
        usuario.rutina = self.construir_rutina(usuario,usuario.tipo_rutina)
        usuario.pendientes = usuario.rutina.copy()

        usuario.completados = []
        usuario.omitidos = []

    def elegir_probabilidad(self,opciones):
        valores = list(opciones.keys())
        probabilidades = list(opciones.values())
        return str(self.rng.choice(valores,p=probabilidades))


    def rutina_tren_superior(self):
        empuje_principal = self.elegir_probabilidad(PROB_TREN_SUPERIOR["empuje_principal"])
        jalon_principal = self.elegir_probabilidad(PROB_TREN_SUPERIOR["jalon_principal"])
        if empuje_principal == "press_pecho":
            empuje_secundario = "press_hombros"
        else:
            empuje_secundario = "aperturas_pecho"

        if jalon_principal == "jalon_pecho":
            jalon_secundario = "remo_sentado"
        else:
            jalon_secundario = "curl_biceps"

        return {"empuje_principal": empuje_principal, "jalon_principal": jalon_principal, "empuje_secundario": empuje_secundario, "jalon_secundario": jalon_secundario}

    def rutina_cuerpo_completo(self):
        piernas = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["piernas"])
        empuje = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["empuje"])
        jalon = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["jalon"])
        categoria = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["complemento"])
        elegidos = [piernas,empuje,jalon]
        disponibles = [ejercicio for ejercicio in EJERCICIOS[categoria] if ejercicio not in elegidos]
        complemento = str(self.rng.choice(disponibles))
        return {"piernas": piernas,"empuje": empuje, "jalon": jalon, "complemento": complemento}

    def ordenar_rutina(self,perfil,tipo,componentes=None):
        if tipo == "empuje":
            if perfil == "X":
                return ["press_pecho","aperturas_pecho","press_hombros"]
            return ["press_pecho","press_hombros","aperturas_pecho"]

        if tipo == "jalon":
            if perfil == "X":
                return ["jalon_pecho","curl_biceps","remo_sentado"]
            if perfil == "I":
                return ["remo_sentado","jalon_pecho","curl_biceps"]
            return ["jalon_pecho","remo_sentado","curl_biceps"]

        if tipo == "piernas":
            if perfil == "I":
                return ["prensa_piernas","curl_femoral","extension_piernas"]
            return ["prensa_piernas","extension_piernas","curl_femoral"]

        if tipo == "tren_superior":
            ep = componentes["empuje_principal"]
            jp = componentes["jalon_principal"]
            es = componentes["empuje_secundario"]
            js = componentes["jalon_secundario"]

            if perfil == "E":
                return [ep,jp,es,js]

            if perfil == "X":
                return [ep,jp,js,es]

            if perfil == "I":
                return [ep,es,jp,js]

        if tipo == "cuerpo_completo":
            piernas = componentes["piernas"]
            empuje = componentes["empuje"]
            jalon = componentes["jalon"]
            complemento = componentes["complemento"]

            if perfil == "X":
                return [empuje,jalon,piernas,complemento]

            return [piernas,empuje,jalon,complemento]


    def construir_rutina(self,usuario,tipo):
        if tipo in ["empuje","jalon","piernas"]:
            rutina = self.ordenar_rutina(usuario.perfil,tipo)
        elif tipo == "tren_superior":
            componentes = self.rutina_tren_superior()
            if usuario.perfil == "F":
                rutina = list(componentes.values())
            else:
                rutina = self.ordenar_rutina(usuario.perfil,tipo,componentes)
        elif tipo == "cuerpo_completo":
            componentes = self.rutina_cuerpo_completo()
            if usuario.perfil == "F":
                rutina = list(componentes.values())
            else:
                rutina = self.ordenar_rutina(usuario.perfil,tipo,componentes)
        if self.rng.random() < PROB_POLEA[usuario.perfil][tipo]:
            rutina.append("polea")
        return rutina

    def generar_asistencias(self,usuario):
        usuario.asistencia = {}
        for ejercicio in usuario.rutina:
            probabilidad = PROB_ASISTENCIA[ejercicio][usuario.perfil]
            usuario.asistencia[ejercicio] = self.rng.random() < probabilidad

    def generar_tipo_rutina(self,perfil):
        return self.elegir_probabilidad(PROB_RUTINA[perfil])

    def finalizar_ejercicio(self,usuario,ejercicio):
        usuario.toallas -= TOALLAS_POR_EJERCICIO
        if usuario.toallas < 0:
            usuario.toallas = 0
        self.registrar_log(evento="towel_consumption", usuario=usuario,recurso=EJERCICIOS_LOG[ejercicio], detalles={"amount": TOALLAS_POR_EJERCICIO, "towels_remaining": usuario.toallas})
        yield self.env.process(self.consumo_agua(usuario,ejercicio))


env = simpy.Environment()
gimnasio = Gimnasio(env,seed=0)

gimnasio.iniciar()
env.run(until=120)

gimnasio.registrar_cambio_ocupacion()
gimnasio.guardar_log("log_prueba_120min.csv", generar_log=True)

print("Ocupacion promedio:", gimnasio.area_ocupacion / env.now)
print("Proporcion a capacidad:", gimnasio.tiempo_capacidad / env.now)

print("\nRESUMEN")
print("Llegadas:",gimnasio.total_llegadas)
print("Admitidos:",gimnasio.admitidos)
print("Rechazados:",gimnasio.rechazados)
print("Usuarios dentro:",gimnasio.usuarios_dentro)

interrupciones_usuarios = 0
interrupciones_entrenadores = 0

for evento in gimnasio.eventos_log:

    if evento[4] == "user_travel_interrupted":
        interrupciones_usuarios += 1

    if evento[4] == "worker_travel_interrupted":
        interrupciones_entrenadores += 1

print("Desplazamientos de usuarios interrumpidos:", interrupciones_usuarios)
print("Desplazamientos de entrenadores interrumpidos:", interrupciones_entrenadores)
