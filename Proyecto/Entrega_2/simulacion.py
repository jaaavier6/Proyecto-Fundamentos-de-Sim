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

        self.cierre_iniciado = False
        self.fin_replica = self.env.event()
        self.aviso_estado_cierre = self.env.event()

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

        self.tecnicos = []
        self.cola_reparaciones = simpy.Store(env)
        self.total_fallas = 0
        self.crear_tecnicos()

        self.agua = simpy.Container(env,capacity=CAPACIDAD_AGUA,init=CAPACIDAD_AGUA)
        self.toallas = simpy.Container(env,capacity=CAPACIDAD_TOALLAS,init=CAPACIDAD_TOALLAS)

        self.punto_agua = simpy.Resource(env,capacity=1)
        self.punto_toallas = simpy.Resource(env,capacity=1)


        #reposiciones de insumos
        self.solicitudes_reposicion = {
            "water":None,
            "towels":None}

        self.tareas_reposicion = {
            "water":None,
            "towels":None}

        self.aviso_stock = {
            "water":self.env.event(),
            "towels":self.env.event()}

        self.quiebre_activo = {
            "water":False,
            "towels":False}

        self.inicio_quiebre = {
            "water":None,
            "towels":None}

        self.episodios_quiebre = {
            "water":0,
            "towels":0}

        self.duracion_quiebre = {
            "water":0,
            "towels":0}

        self.cantidad_repuesta = {
            "water":0,
            "towels":0}
        


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

    def crear_tecnicos(self):
        for i in range(N_TECNICOS):
            tecnico = Tecnico(
                i+1,
                self.velocidad_trabajador("tecnico"),
                CELDA_RECEPCION
            )

            self.tecnicos.append(tecnico)

            self.env.process(
                self.proceso_tecnico(tecnico)
            )

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
        if usuario.reasignacion_pendiente is not None:
            maquina_reasignada = usuario.reasignacion_pendiente["maquina"]

            if (
                maquina_reasignada is not None
                and maquina_reasignada.tipo == ejercicio
                and maquina_reasignada.operativa
            ):
                return maquina_reasignada
            
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

    def seleccionar_maquina_reasignacion(self,maquina_averiada):
        opciones = []

        for maquina in self.maquinas:
            if (
                maquina.tipo == maquina_averiada.tipo
                and maquina is not maquina_averiada
                and maquina.operativa
            ):
                opciones.append((
                    len(maquina.recurso.queue),
                    distancia(maquina_averiada.posicion,maquina.posicion),
                    maquina.posicion,
                    maquina
                ))

        if len(opciones) == 0:
            return None

        mejor = min(opciones,key=lambda x:(x[0],x[1],x[2]))

        return mejor[3]

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

    def duracion_cardio(self,perfil):
        p = PARAMETROS_DURACION_CARDIO[perfil]

        if perfil == "E":
            duracion = self.rng.gamma(
                p["shape"],
                p["scale"]
            )

            return min(
                p["maximo"],
                duracion
            )

        if perfil == "X":
            beta = self.rng.beta(
                p["a"],
                p["b"]
            )

            return (
                p["minimo"]
                + beta*(p["maximo"]-p["minimo"])
            )

        if perfil in ["F","I"]:
            if self.rng.random() < p["p_gamma"]:
                return self.rng.gamma(
                    p["gamma_shape"],
                    p["gamma_scale"]
                )

            return self.rng.lognormal(
                p["log_mu"],
                p["log_sigma"]
            )

    def seleccionar_trotadora(self,usuario):
        operativas = []

        for maquina in self.maquinas:
            if maquina.tipo == "trotadora" and maquina.operativa:
                operativas.append(maquina)

        if len(operativas) == 0:
            return None

        libres = []

        for maquina in operativas:
            if (
                maquina.recurso.count == 0
                and len(maquina.recurso.queue) == 0
            ):
                libres.append(maquina)

        #si existe alguna libre se elige la libre mas cercana
        if len(libres) > 0:
            candidatas = libres
        else:
            #si todas estan ocupadas se elige la mas cercana
            candidatas = operativas

        return min(
            candidatas,
            key=lambda maquina:(
                distancia(usuario.posicion,maquina.posicion),
                maquina.posicion
            )
        )

    def esperar_trotadora_operativa( self, usuario, tolerancia_restante):
        restante = tolerancia_restante

        while self.seleccionar_trotadora(usuario) is None:

            if self.env.now >= CIERRE:
                return "cierre"

            if self.env.now >= usuario.hora_limite:
                return "permanencia máxima"

            if restante <= 1e-9:
                return "tolerancia"

            tiempo_limite = min(
                usuario.hora_limite,
                CIERRE
            ) - self.env.now

            tiempo_espera = min(
                tiempo_limite,
                restante
            )

            aviso = self.aviso_reparacion

            inicio = self.env.now

            yield (
                aviso
                | self.env.timeout(tiempo_espera)
            )

            espera = self.env.now-inicio

            usuario.espera_cardio += espera
            usuario.espera_total += espera

            if restante != float("inf"):
                restante = max(
                    0,
                    restante-espera
                )

        return "disponible"
    def intentar_cardio(self,usuario):

        espera_inicial = usuario.espera_cardio

        while True:

            if self.env.now >= CIERRE:
                return "cierre"

            if self.env.now >= usuario.hora_limite:
                return "permanencia máxima"

            espera_usada = (
                usuario.espera_cardio
                - espera_inicial
            )

            if usuario.perfil == "I":
                tolerancia_restante = float("inf")
            else:
                tolerancia_restante = max(
                    0,
                    usuario.tolerancia-espera_usada
                )

            #si viene reasignado por una falla de trotadora
            info_reasignacion = None

            if (
                usuario.reasignacion_pendiente is not None
                and usuario.reasignacion_pendiente["maquina"] is not None
                and usuario.reasignacion_pendiente["maquina"].tipo == "trotadora"
            ):
                info_reasignacion = (
                    usuario.reasignacion_pendiente
                )

                maquina = info_reasignacion["maquina"]

            else:
                #si la falla no tenia otra trotadora disponible
                if usuario.reasignacion_pendiente is not None:

                    siguiente = usuario.reasignacion_pendiente.get(
                        "siguiente_turno"
                    )

                    if (
                        siguiente is not None
                        and not siguiente.triggered
                    ):
                        siguiente.succeed()

                    usuario.reasignacion_pendiente = None

                maquina = self.seleccionar_trotadora(
                    usuario
                )

            #no queda ninguna operativa
            if maquina is None:

                resultado = yield self.env.process(
                    self.esperar_trotadora_operativa(
                        usuario,
                        tolerancia_restante
                    )
                )

                if resultado == "disponible":
                    continue

                return resultado

            #viajar a la trotadora
            llego = yield self.env.process(
                self.mover_usuario(
                    usuario,
                    maquina.posicion
                )
            )

            if not llego:

                if info_reasignacion is not None:
                    siguiente = info_reasignacion[
                        "siguiente_turno"
                    ]

                    if (
                        siguiente is not None
                        and not siguiente.triggered
                    ):
                        siguiente.succeed()

                    usuario.reasignacion_pendiente = None

                if self.env.now >= CIERRE:
                    return "cierre"

                return "permanencia máxima"

            if self.env.now >= CIERRE:
                return "cierre"

            if self.env.now >= usuario.hora_limite:
                return "permanencia máxima"

            #puede haber fallado mientras caminaba
            if not maquina.operativa:

                if info_reasignacion is not None:
                    siguiente = info_reasignacion[
                        "siguiente_turno"
                    ]

                    if (
                        siguiente is not None
                        and not siguiente.triggered
                    ):
                        siguiente.succeed()

                    usuario.reasignacion_pendiente = None

                continue

            #si fue una reasignacion por falla,
            #respetar el orden anterior
            if info_reasignacion is not None:

                turno = info_reasignacion[
                    "turno_reasignacion"
                ]

                if not turno.triggered:

                    espera_usada = (
                        usuario.espera_cardio
                        - espera_inicial
                    )

                    if usuario.perfil == "I":
                        tolerancia_turno = float("inf")
                    else:
                        tolerancia_turno = max(
                            0,
                            usuario.tolerancia-espera_usada
                        )

                    tiempo_permanencia = (
                        usuario.hora_limite
                        - self.env.now
                    )

                    tiempo_cierre = (
                        CIERRE-self.env.now
                    )

                    tiempo_turno = min(
                        tolerancia_turno,
                        tiempo_permanencia,
                        tiempo_cierre
                    )

                    if tiempo_turno <= 1e-9:

                        siguiente = info_reasignacion[
                            "siguiente_turno"
                        ]

                        if (
                            siguiente is not None
                            and not siguiente.triggered
                        ):
                            siguiente.succeed()

                        if tiempo_permanencia <= 0:
                            return "permanencia máxima"

                        if tiempo_cierre <= 0:
                            return "cierre"

                        return "tolerancia"

                    inicio_turno = self.env.now

                    resultado_turno = yield (
                        turno
                        | self.env.timeout(tiempo_turno)
                    )

                    espera_turno = (
                        self.env.now-inicio_turno
                    )

                    usuario.espera_cardio += espera_turno
                    usuario.espera_total += espera_turno

                    if turno not in resultado_turno:

                        siguiente = info_reasignacion[
                            "siguiente_turno"
                        ]

                        if (
                            siguiente is not None
                            and not siguiente.triggered
                        ):
                            siguiente.succeed()

                        if self.env.now >= CIERRE:
                            return "cierre"

                        if self.env.now >= usuario.hora_limite:
                            return "permanencia máxima"

                        return "tolerancia"

            #recalcular tolerancia despues de cualquier espera
            espera_usada = (
                usuario.espera_cardio
                - espera_inicial
            )

            if usuario.perfil == "I":
                tiempo_tolerancia = float("inf")
            else:
                tiempo_tolerancia = max(
                    0,
                    usuario.tolerancia-espera_usada
                )

            maquina_libre = (
                maquina.recurso.count == 0
                and len(maquina.recurso.queue) == 0
            )

            if (
                not maquina_libre
                and tiempo_tolerancia <= 1e-9
            ):
                return "tolerancia"

            tiempo_permanencia = (
                usuario.hora_limite-self.env.now
            )

            tiempo_cierre = (
                CIERRE-self.env.now
            )

            if maquina_libre:
                tiempo_dispo = min(
                    tiempo_permanencia,
                    tiempo_cierre
                )
            else:
                tiempo_dispo = min(
                    tiempo_tolerancia,
                    tiempo_permanencia,
                    tiempo_cierre
                )

            if tiempo_dispo <= 1e-9:
                if tiempo_permanencia <= 0:
                    return "permanencia máxima"

                return "cierre"

            inicio_espera = self.env.now

            with maquina.recurso.request() as solicitud:

                solicitud.usuario = usuario
                solicitud.ejercicio = "trotadora"
                solicitud.aviso_reasignacion = self.env.event()

                #ya entro a la nueva cola:
                #liberar al siguiente reasignado
                if info_reasignacion is not None:

                    siguiente = info_reasignacion[
                        "siguiente_turno"
                    ]

                    if (
                        siguiente is not None
                        and not siguiente.triggered
                    ):
                        siguiente.succeed()

                    usuario.reasignacion_pendiente = None

                if not solicitud.triggered:
                    self.registrar_log(
                        evento="machine_queue_enter",
                        usuario=usuario,
                        recurso=self.identificador_maquina(maquina),
                        detalles={
                            "machine_type":"treadmill",
                            "queue_length":len(
                                maquina.recurso.queue
                            )
                        }
                    )

                resultado = yield (
                    solicitud
                    | self.env.timeout(tiempo_dispo)
                    | solicitud.aviso_reasignacion
                )

                espera = (
                    self.env.now-inicio_espera
                )

                usuario.espera_cardio += espera
                usuario.espera_total += espera

                #la trotadora fallo mientras esperaba
                if solicitud.aviso_reasignacion in resultado:

                    usuario.reasignacion_pendiente = (
                        resultado[
                            solicitud.aviso_reasignacion
                        ]
                    )

                    continue

                if self.env.now >= CIERRE:
                    return "cierre"

                if self.env.now >= usuario.hora_limite:
                    return "permanencia máxima"

                if solicitud not in resultado:

                    if (
                        tiempo_dispo
                        == tiempo_tolerancia
                    ):
                        return "tolerancia"

                    if (
                        tiempo_dispo
                        == tiempo_permanencia
                    ):
                        return "permanencia máxima"

                    return "cierre"

                if not maquina.operativa:
                    continue

                self.registrar_log(
                    evento="machine_acquired",
                    usuario=usuario,
                    recurso=self.identificador_maquina(maquina),
                    detalles={
                        "machine_type":"treadmill",
                        "queue_wait":round(
                            float(espera),
                            4
                        )
                    }
                )

                maquina.usuario_actual = usuario.id

                duracion = self.duracion_cardio(
                    usuario.perfil
                )

                self.registrar_log(
                    evento="cardio_start",
                    usuario=usuario,
                    recurso=self.identificador_maquina(maquina),
                    detalles={
                        "machine_type":"treadmill",
                        "duration":round(
                            float(duracion),
                            4
                        )
                    }
                )

                #una vez iniciado no se interrumpe
                yield self.env.timeout(duracion)

                maquina.tiempo_uso += duracion
                maquina.usuario_actual = None

                fallo = yield self.env.process(
                    self.evaluar_falla(
                        maquina,
                        usuario
                    )
                )

                usuario.cardio_completado = True

                self.registrar_log(
                    evento="cardio_end",
                    usuario=usuario,
                    recurso=self.identificador_maquina(maquina),
                    detalles={
                        "machine_type":"treadmill",
                        "duration":round(
                            float(duracion),
                            4
                        ),
                        "failed_after_use":bool(fallo)
                    }
                )

                return "completado"
            
    def evaluar_falla(self,maquina,usuario):

        probabilidad = PROB_FALLA[maquina.tipo]

        if self.rng.random() >= probabilidad:
            return False

        maquina.operativa = False
        maquina.inicio_falla = self.env.now
        maquina.numero_fallas += 1

        self.total_fallas += 1

        cola_antes_falla = list(maquina.recurso.queue)

        maquina_reasignada = self.seleccionar_maquina_reasignacion(
            maquina
        )

        turnos_reasignacion = [
            self.env.event()
            for _ in cola_antes_falla
        ]

        if len(turnos_reasignacion) > 0:
            turnos_reasignacion[0].succeed()

        duracion = self.duracion_reparacion(maquina.tipo)

        solicitud = {
            "maquina":maquina,
            "hora_falla":self.env.now,
            "duracion":duracion
        }

        for rango,solicitud_cola in enumerate(cola_antes_falla,start=1):

            usuario_cola = solicitud_cola.usuario

            if maquina_reasignada is not None:
                self.registrar_log(
                    evento="queue_reassigned_failure",
                    usuario=usuario_cola,
                    recurso=self.identificador_maquina(maquina_reasignada),
                    detalles={
                        "from_unit":self.identificador_maquina(maquina),
                        "queue_size":len(cola_antes_falla),
                        "rank":rango
                    }
                )
            info = {
                "maquina":maquina_reasignada,
                "maquina_anterior":maquina,
                "rango":rango,
                "turno_reasignacion":turnos_reasignacion[rango-1],
                "siguiente_turno":(
                    turnos_reasignacion[rango]
                    if rango < len(turnos_reasignacion)
                    else None
                )
            }
            if not solicitud_cola.aviso_reasignacion.triggered:
                solicitud_cola.aviso_reasignacion.succeed(info)

        self.registrar_log(
            evento="machine_failure",
            usuario=usuario,
            tipo_entidad="machine",
            identificador=self.identificador_maquina(maquina),
            ubicacion=maquina.posicion,
            recurso=EJERCICIOS_LOG[maquina.tipo],
            detalles={
                "queued_users":len(cola_antes_falla),
                "reassignment_unit":(
                    self.identificador_maquina(maquina_reasignada)
                    if maquina_reasignada is not None
                    else None
                )
            }
        )

        yield self.cola_reparaciones.put(solicitud)

        return True

    def proceso_tecnico(self,tecnico):

        while True:

            solicitud = yield self.cola_reparaciones.get()

            maquina = solicitud["maquina"]
            hora_falla = solicitud["hora_falla"]
            duracion = solicitud["duracion"]

            tecnico.ocupado = True
            tecnico.tarea_actual = "reparacion"

            espera_despacho = self.env.now-hora_falla

            origen = tecnico.posicion
            destino = maquina.posicion

            tiempo_viaje = tiempo_desplazamiento(
                origen,
                destino,
                tecnico.velocidad
            )

            self.registrar_log(
                evento="worker_travel_start",
                tipo_entidad="worker",
                identificador=f"M-{tecnico.id:02d}",
                ubicacion=origen,
                recurso="technicians",
                detalles={
                    "origin":origen,
                    "destination":destino,
                    "duration":round(float(tiempo_viaje),4)
                }
            )

            yield self.env.timeout(tiempo_viaje)

            tecnico.posicion = destino

            self.registrar_log(
                evento="worker_travel_end",
                tipo_entidad="worker",
                identificador=f"M-{tecnico.id:02d}",
                ubicacion=destino,
                recurso="technicians",
                detalles={
                    "origin":origen,
                    "destination":destino,
                    "duration":round(float(tiempo_viaje),4)
                }
            )

            espera_reparacion = self.env.now-hora_falla

            self.registrar_log(
                evento="repair_start",
                tipo_entidad="machine",
                identificador=self.identificador_maquina(maquina),
                ubicacion=maquina.posicion,
                recurso=f"M-{tecnico.id:02d}",
                detalles={
                    "machine_type":EJERCICIOS_LOG[maquina.tipo],
                    "dispatch_wait":round(float(espera_despacho),4),
                    "travel_time":round(float(tiempo_viaje),4),
                    "repair_wait":round(float(espera_reparacion),4),
                    "duration":round(float(duracion),4)
                }
            )

            yield self.env.timeout(duracion)

            maquina.operativa = True

            maquina.tiempo_falla += max(0,min(self.env.now,CIERRE)-maquina.inicio_falla)

            maquina.inicio_falla = None

            self.registrar_log(
                evento="repair_end",
                tipo_entidad="machine",
                identificador=self.identificador_maquina(maquina),
                ubicacion=maquina.posicion,
                recurso=f"M-{tecnico.id:02d}",
                detalles={
                    "machine_type":EJERCICIOS_LOG[maquina.tipo],
                    "repair_wait":round(float(espera_reparacion),4),
                    "duration":round(float(duracion),4),
                    "returned_same_day":bool(self.env.now < CIERRE)
                }
            )

            self.notificar_reparacion()

            #si no quedan fallas pendientes vuelve a recepcion
            if len(self.cola_reparaciones.items) == 0:
                tecnico.tarea_actual = "retorno"

                origen = tecnico.posicion
                destino = CELDA_RECEPCION

                if origen != destino:

                    tiempo_viaje = tiempo_desplazamiento(
                        origen,
                        destino,
                        tecnico.velocidad
                    )

                    self.registrar_log(
                        evento="worker_travel_start",
                        tipo_entidad="worker",
                        identificador=f"M-{tecnico.id:02d}",
                        ubicacion=origen,
                        recurso="technicians",
                        detalles={
                            "origin":origen,
                            "destination":destino,
                            "duration":round(float(tiempo_viaje),4)
                        }
                    )

                    yield self.env.timeout(tiempo_viaje)

                    tecnico.posicion = destino

                    self.registrar_log(
                        evento="worker_travel_end",
                        tipo_entidad="worker",
                        identificador=f"M-{tecnico.id:02d}",
                        ubicacion=destino,
                        recurso="technicians",
                        detalles={
                            "origin":origen,
                            "destination":destino,
                            "duration":round(float(tiempo_viaje),4)
                        }
                    )

                tecnico.ocupado = False
                tecnico.tarea_actual = None
                self.notificar_estado_cierre()
                    
    def duracion_reparacion(self,tipo):

        if tipo == "trotadora":
            return min(50,self.rng.gamma(7,5))

        if tipo in [
            "press_pecho",
            "press_hombros",
            "aperturas_pecho"
        ]:
            if self.rng.random() < 0.75:
                return self.rng.gamma(12,1.35)
            return self.rng.lognormal(3.55,0.18)

        if tipo in [
            "jalon_pecho",
            "remo_sentado",
            "curl_biceps"
        ]:
            u = self.rng.random()
            duracion = 20.5 * (u/(1-u))**(1/4.2)

            return min(48,duracion)

        if tipo in [
            "prensa_piernas",
            "curl_femoral",
            "extension_piernas"
        ]:
            if self.rng.random() < 0.65:
                return self.rng.gamma(12,2.1)
            return self.rng.lognormal(3.7,0.16)

        if tipo == "polea":
            if self.rng.random() < 0.70:
                duracion = 21*self.rng.weibull(4)
            else:
                duracion = self.rng.lognormal(3.55,0.20)

            return min(55,duracion)

    def intentar_ejercicio(self, usuario, ejercicio, maquina, tolerancia=None):
        #primero se revisa si el usuario tiene el tiempo suficiente 
        if self.env.now >= CIERRE:
            return "cierre"
        if self.env.now >= usuario.hora_limite:
            return "permanencia máxima"
        if maquina is None:
            return "sin_maquina_operativa"

        info_reasignacion = None
        if (
            usuario.reasignacion_pendiente is not None
            and usuario.reasignacion_pendiente["maquina"] is maquina
            ):
            info_reasignacion = usuario.reasignacion_pendiente
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

        #si viene de una reasignacion por falla,
#respeta el orden que tenia en la cola anterior
        if info_reasignacion is not None:

            turno = info_reasignacion["turno_reasignacion"]

            if not turno.triggered:

                tiempo_permanencia = usuario.hora_limite-self.env.now
                tiempo_cierre = CIERRE-self.env.now

                tiempo_disponible_turno = min(
                    tiempo_tolerancia,
                    tiempo_permanencia,
                    tiempo_cierre
                )

                if tiempo_disponible_turno <= 1e-9:
                    siguiente = info_reasignacion["siguiente_turno"]

                    if (
                        siguiente is not None
                        and not siguiente.triggered
                    ):
                        siguiente.succeed()

                    if tiempo_permanencia <= 0:
                        return "permanencia máxima"

                    if tiempo_cierre <= 0:
                        return "cierre"

                    return "tolerancia"

                inicio_espera_turno = self.env.now

                resultado_turno = yield (
                    turno
                    | self.env.timeout(tiempo_disponible_turno)
                )

                espera_turno = (
                    self.env.now-inicio_espera_turno
                )

                usuario.espera_maquinas += espera_turno
                usuario.espera_total += espera_turno

                if turno not in resultado_turno:

                    siguiente = info_reasignacion["siguiente_turno"]

                    if (
                        siguiente is not None
                        and not siguiente.triggered
                    ):
                        siguiente.succeed()

                    if (
                        tiempo_permanencia
                        <= tiempo_tolerancia
                        and tiempo_permanencia <= tiempo_cierre
                    ):
                        return "permanencia máxima"

                    if tiempo_cierre <= tiempo_tolerancia:
                        return "cierre"

                    return "tolerancia"

                if tiempo_tolerancia != float("inf"):
                    tiempo_tolerancia = max(
                        0,
                        tiempo_tolerancia-espera_turno
                    )

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
            solicitud_maquina.usuario = usuario
            solicitud_maquina.ejercicio = ejercicio
            solicitud_maquina.aviso_reasignacion = self.env.event()
            if info_reasignacion is not None:

                siguiente = info_reasignacion["siguiente_turno"]

                if (
                    siguiente is not None
                    and not siguiente.triggered
                ):
                    siguiente.succeed()

                usuario.reasignacion_pendiente = None
                
            if not solicitud_maquina.triggered:
                self.registrar_log(evento="machine_queue_enter", usuario=usuario, recurso=self.identificador_maquina(maquina), detalles={"machine_type": EJERCICIOS_LOG[maquina.tipo], "queue_length": len(maquina.recurso.queue)})
            resultado = yield (
                solicitud_maquina
                | self.env.timeout(tiempo_dispo)
                | solicitud_maquina.aviso_reasignacion
            )
            espera = self.env.now - inicio_espera
            usuario.espera_maquinas = usuario.espera_maquinas + espera
            usuario.espera_total = usuario.espera_total + espera
            if solicitud_maquina.aviso_reasignacion in resultado:
                info = resultado[solicitud_maquina.aviso_reasignacion]

                usuario.reasignacion_pendiente = info

                return "maquina_averiada"
            
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

            fallo = yield self.env.process(
                self.evaluar_falla(maquina,usuario)
            )

            self.registrar_log(
                evento="exercise_end",
                usuario=usuario,
                recurso=self.identificador_maquina(maquina),
                detalles={
                    "machine_type":EJERCICIOS_LOG[maquina.tipo],
                    "duration":round(float(duracion),4),
                    "failed_after_use":bool(fallo)
                }
            )
            #liberar al entrenador en caso de que se haya neesitado
            if pedido is not None:
                pedido["fin"].succeed()
            return "completado"

    def crear_entrenadores(self):
        for i in range(N_ENTRENADORES):
            entrenador = Entrenador(i+1, self.velocidad_trabajador("entrenador"), CELDA_ENTRENADORES)
            self.entrenadores.append(entrenador)
            self.env.process(self.proceso_entrenador(entrenador))

    def tiempo_reposicion(self,insumo):
        if insumo == "water":
            p = PARAMETROS_REPOSICION["water"]

            if self.rng.random() < p["p_gamma"]:
                return self.rng.gamma(
                    p["gamma_shape"],
                    p["gamma_scale"]
                )

            return self.rng.lognormal(
                p["log_mu"],
                p["log_sigma"]
            )

        p = PARAMETROS_REPOSICION["towels"]

        return self.rng.gamma(
            p["gamma_shape"],
            p["gamma_scale"]
        )
    
    def notificar_stock(self,insumo):

        aviso = self.aviso_stock[insumo]

        self.aviso_stock[insumo] = self.env.event()

        if not aviso.triggered:
            aviso.succeed()


    def activar_quiebre(self,insumo,usuario=None):
        if not self.quiebre_activo[insumo]:

            self.quiebre_activo[insumo] = True
            self.inicio_quiebre[insumo] = self.env.now
            self.episodios_quiebre[insumo] += 1

            celda = (
                CELDA_AGUA
                if insumo == "water"
                else CELDA_TOALLAS
            )

            evento = (
                "water_stockout"
                if insumo == "water"
                else "towels_stockout"
            )

            identificador = insumo

            if usuario is not None:
                identificador = f"U-{usuario.id:04d}"

            self.registrar_log(
                evento=evento,
                usuario=usuario,
                tipo_entidad="supply",
                identificador=identificador,
                ubicacion=celda,
                recurso=insumo,
                detalles={
                    "stock":0,
                    "episode":self.episodios_quiebre[insumo]
                }
            )

        #al quedar en cero la reposicion pasa a urgente
        if self.env.now < CIERRE:
            self.solicitar_reposicion(
                insumo,
                PRIORIDAD_URGENTE,
                "urgent"
            )

    def finalizar_quiebre(self,insumo):

        if not self.quiebre_activo[insumo]:
            return

        duracion = (
            self.env.now
            - self.inicio_quiebre[insumo]
        )

        self.duracion_quiebre[insumo] += duracion

        evento = (
            "water_stockout_end"
            if insumo == "water"
            else "towels_stockout_end"
        )

        nivel = (
            self.agua.level
            if insumo == "water"
            else self.toallas.level
        )

        self.registrar_log(
            evento=evento,
            tipo_entidad="supply",
            identificador=insumo,
            recurso=insumo,
            detalles={
                "episode":self.episodios_quiebre[insumo],
                "episode_duration":round(
                    float(duracion),
                    4
                ),
                "new_stock":round(
                    float(nivel),
                    4
                )
            }
        )

        self.quiebre_activo[insumo] = False
        self.inicio_quiebre[insumo] = None


    def solicitar_reposicion(self,insumo,prioridad,motivo):

        existente = self.solicitudes_reposicion[insumo]

        #no existe ninguna solicitud
        if existente is None:

            self.contador_tareas_recepcion += 1

            orden = self.contador_tareas_recepcion
            fin = self.env.event()

            solicitud = {
                "insumo":insumo,
                "prioridad":prioridad,
                "motivo":motivo,
                "estado":"pendiente",
                "orden":orden,
                "fin":fin
            }

            self.solicitudes_reposicion[insumo] = solicitud

            tarea = (
                prioridad,
                orden,
                "reposicion",
                solicitud,
                fin,
                self.env.now
            )

            self.cola_recepcion.put(tarea)

            return

        #si ya existe una solicitud periodica pendiente
        #y el stock llega a cero, la misma solicitud
        #pasa a urgente
        if (
            prioridad == PRIORIDAD_URGENTE
            and existente["prioridad"] != PRIORIDAD_URGENTE
            and existente["estado"] == "pendiente"
        ):

            existente["prioridad"] = PRIORIDAD_URGENTE
            existente["motivo"] = "urgent"

            tarea_urgente = (
                PRIORIDAD_URGENTE,
                existente["orden"],
                "reposicion",
                existente,
                existente["fin"],
                self.env.now
            )

            self.cola_recepcion.put(tarea_urgente)

    def esperar_stock(self,usuario,insumo,limite):

        if self.env.now >= limite:
            return False

        #asegura que exista/promueva la reposicion urgente
        self.activar_quiebre(insumo)

        aviso = self.aviso_stock[insumo]

        inicio_espera = self.env.now

        resultado = yield (
            aviso
            | self.env.timeout(
                limite-self.env.now
            )
        )

        espera = self.env.now-inicio_espera

        if insumo == "water":
            usuario.espera_agua += espera
        else:
            usuario.espera_toallas += espera

        usuario.espera_total += espera

        if aviso not in resultado:
            return False

        #puede haber vuelto el stock justo al alcanzar
        #permanencia/cierre: no puede iniciar otro retiro
        if self.env.now >= limite:
            return False

        return True
            
    def retirar_toallas(self,usuario):

        limite = min(
            usuario.hora_limite,
            CIERRE
        )

        if self.env.now >= limite:
            return False

        llego = yield self.env.process(
            self.mover_usuario(
                usuario,
                CELDA_TOALLAS
            )
        )

        if not llego:
            return False

        while True:

            if self.env.now >= limite:
                return False

            inicio_espera = self.env.now

            with self.punto_toallas.request() as req:

                tiempo_disponible = (
                    limite-self.env.now
                )

                resultado = yield (
                    req
                    | self.env.timeout(
                        tiempo_disponible
                    )
                )

                espera = (
                    self.env.now-inicio_espera
                )

                usuario.espera_toallas += espera
                usuario.espera_total += espera

                if req not in resultado:
                    return False

                #si esta vacio NO esperamos
                #manteniendo bloqueado el punto
                if self.toallas.level > 0:

                    cantidad = min(
                        MAX_TOALLAS_RETIRO,
                        int(self.toallas.level)
                    )

                    stock_anterior = (
                        self.toallas.level
                    )

                    #el retiro ya iniciado es
                    #no interrumpible
                    yield self.env.timeout(
                        TIEMPO_RETIRO_TOALLAS
                    )

                    #el stock se descuenta
                    #al TERMINAR los 0.75 min
                    yield self.toallas.get(
                        cantidad
                    )

                    usuario.toallas += cantidad

                    self.registrar_log(
                        evento="towels_pickup_end",
                        usuario=usuario,
                        recurso="towels",
                        detalles={
                            "amount":cantidad,
                            "pickup_duration":
                                TIEMPO_RETIRO_TOALLAS,
                            "stock_before":
                                stock_anterior,
                            "remaining_stock":
                                self.toallas.level,
                            "towels_personal":
                                usuario.toallas
                        }
                    )

                    #el quiebre comienza JUSTO
                    #cuando este retiro deja stock 0
                    if self.toallas.level <= 0:
                        self.activar_quiebre(
                            "towels"
                        )

                    return True

            #salimos del with antes de esperar:
            #asi el punto queda libre para reposicion
            pudo_continuar = yield self.env.process(
                self.esperar_stock(
                    usuario,
                    "towels",
                    limite
                )
            )

            if not pudo_continuar:
                return False

            #volvio stock:
            #vuelve al comienzo y pide el punto nuevamente
    
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

        limite = min(
            usuario.hora_limite,
            CIERRE
        )

        if self.env.now >= limite:
            return False

        llego = yield self.env.process(
            self.mover_usuario(
                usuario,
                CELDA_AGUA
            )
        )

        if not llego:
            return False

        while True:

            if self.env.now >= limite:
                return False

            inicio_espera = self.env.now

            with self.punto_agua.request() as req:

                tiempo_disponible = (
                    limite-self.env.now
                )

                resultado = yield (
                    req
                    | self.env.timeout(
                        tiempo_disponible
                    )
                )

                espera = (
                    self.env.now-inicio_espera
                )

                usuario.espera_agua += espera
                usuario.espera_total += espera

                if req not in resultado:
                    return False

                if self.agua.level > 0:

                    cantidad = min(
                        usuario.capacidad_botella
                        - usuario.agua,
                        self.agua.level
                    )

                    stock_anterior = (
                        self.agua.level
                    )

                    #retiro no interrumpible
                    yield self.env.timeout(
                        TIEMPO_RETIRO_AGUA
                    )

                    #el descuento ocurre
                    #al finalizar los 0.75 min
                    yield self.agua.get(
                        cantidad
                    )

                    usuario.agua += cantidad

                    self.registrar_log(
                        evento="water_pickup_end",
                        usuario=usuario,
                        recurso="water",
                        detalles={
                            "amount":round(
                                float(cantidad),
                                4
                            ),
                            "pickup_duration":
                                TIEMPO_RETIRO_AGUA,
                            "stock_before":round(
                                float(stock_anterior),
                                4
                            ),
                            "remaining_stock":round(
                                float(self.agua.level),
                                4
                            ),
                            "bottle_level_liters":
                                round(
                                    float(usuario.agua),
                                    4
                                )
                        }
                    )

                    #si este retiro vacio el bidon,
                    #el quiebre comienza AHORA
                    if self.agua.level <= 1e-9:

                        self.activar_quiebre(
                            "water"
                        )

                    return True

            pudo_continuar = yield self.env.process(
                self.esperar_stock(
                    usuario,
                    "water",
                    limite
                )
            )

            if not pudo_continuar:
                return False

    def inspecciones_periodicas(self):

        proxima_agua = INTERVALO_REVISION_AGUA
        proxima_toallas = INTERVALO_REVISION_TOALLAS

        while True:

            siguiente = min(
                proxima_agua,
                proxima_toallas
            )

            if siguiente >= CIERRE:
                return

            yield self.env.timeout(
                siguiente-self.env.now
            )

            revisar_agua = (
                abs(
                    self.env.now-proxima_agua
                ) < 1e-9
            )

            revisar_toallas = (
                abs(
                    self.env.now-proxima_toallas
                ) < 1e-9
            )

            #la revision es como una camara:
            #solo requiere que exista al menos
            #un recepcionista libre
            hay_recepcionista_libre = any(
                not r.ocupado
                for r in self.recepcionistas
            )

            if hay_recepcionista_libre:

                #IMPORTANTE:
                #si coinciden ambas revisiones,
                #toallas primero
                if (
                    revisar_toallas
                    and self.toallas.level
                        < UMBRAL_TOALLAS
                ):
                    self.solicitar_reposicion(
                        "towels",
                        PRIORIDAD_PERIODICA,
                        "periodic"
                    )

                if (
                    revisar_agua
                    and self.agua.level
                        < UMBRAL_AGUA
                ):
                    self.solicitar_reposicion(
                        "water",
                        PRIORIDAD_PERIODICA,
                        "periodic"
                    )

            if revisar_agua:
                proxima_agua += (
                    INTERVALO_REVISION_AGUA
                )

            if revisar_toallas:
                proxima_toallas += (
                    INTERVALO_REVISION_TOALLAS
                )

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

    def intentar_express(self,usuario,ejercicio):
        espera_inicial = usuario.espera_maquinas

        while True:
            espera_usada = usuario.espera_maquinas-espera_inicial

            tolerancia_restante = max(
                0,
                usuario.tolerancia-espera_usada
            )

            maquina = self.seleccionar_maquina(
                usuario,
                ejercicio
            )

            #express no espera reparacion
            if maquina is None:
                return "sin_maquina_operativa"

            resultado = yield self.env.process(
                self.intentar_ejercicio(
                    usuario,
                    ejercicio,
                    maquina,
                    tolerancia_restante
                )
            )

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
                resultado = yield self.env.process(
                        self.intentar_express(
                            usuario,
                            ejercicio
                        )
                    )
                if resultado == "sin_maquina_operativa":
                    usuario.pendientes.remove(ejercicio)
                    usuario.omitidos.append(ejercicio)

                    self.registrar_log(
                        evento="exercise_omitted",
                        usuario=usuario,
                        recurso=EJERCICIOS_LOG[ejercicio],
                        detalles={
                            "reason":"no_operational_machine"
                        }
                    )

                    continue

                elif resultado == "completado":
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
                        usuario.cardio_permitido = False
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
                    resultado = yield self.env.process(
                        self.esperar_operatividad(usuario,[ejercicio])
                    )

                    if resultado == "disponible":
                        continue

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
                self.notificar_estado_cierre()
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
            self.notificar_estado_cierre()

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
            self.notificar_estado_cierre()
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
        self.env.process(self.inspecciones_periodicas())
        self.env.process(self.proceso_cierre())

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
            
        registro_completado = yield self.env.process(
            self.registrar_usuario(usuario))

        if not registro_completado:
            yield self.env.process(
                self.salir_usuario(usuario)
            )
            return
        
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

        if (usuario.cardio_planificado and usuario.cardio_permitido and self.env.now < CIERRE and self.env.now < usuario.hora_limite):
            
            yield self.env.process(self.intentar_cardio(usuario) )

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
    
    def mover_trabajador(self,trabajador,destino,grupo):
        if trabajador.posicion == destino:
            return
        if grupo == "trainers":
            identificador = f"PT-{trabajador.id:02d}"
        elif grupo == "technicians":
            identificador = f"M-{trabajador.id:02d}"
        else:
            identificador = f"R-{trabajador.id:02d}"

        origen = trabajador.posicion
        tiempo = tiempo_desplazamiento(origen,destino,trabajador.velocidad)
        self.registrar_log(evento="worker_travel_start",tipo_entidad="worker",identificador=identificador,ubicacion=origen,recurso=grupo,detalles={"origin":origen,"destination":destino,"duration":round(float(tiempo),4)})
        yield self.env.timeout(tiempo)
        trabajador.posicion = destino
        self.registrar_log(evento="worker_travel_end",tipo_entidad="worker",identificador=identificador,ubicacion=destino,recurso=grupo,detalles={"origin":origen,"destination":destino,"duration":round(float(tiempo),4)})

    def salir_trabajador(self,trabajador,grupo):
        if grupo == "trainers":
            identificador = f"PT-{trabajador.id:02d}"
        elif grupo == "technicians":
            identificador = f"M-{trabajador.id:02d}"
        else:
            identificador = f"R-{trabajador.id:02d}"

        ruta = [CELDA_ACCESO] if trabajador.posicion == CELDA_RECEPCION else [CELDA_INICIO_ENTRENAMIENTO,CELDA_PASO,CELDA_ACCESO]
        self.registrar_log(evento="staff_exit_start",tipo_entidad="worker",identificador=identificador,ubicacion=trabajador.posicion,recurso=grupo,detalles={"route":ruta})
        inicio = self.env.now

        for destino in ruta:
            yield self.env.process(self.mover_trabajador(trabajador,destino,grupo))

        trabajador.dentro = False
        trabajador.hora_salida = self.env.now
        self.registrar_log(evento="staff_exit",tipo_entidad="worker",identificador=identificador,ubicacion=CELDA_ACCESO,recurso=grupo,detalles={"overtime_minutes":round(max(0,self.env.now-CIERRE),4),"exit_travel_time":round(self.env.now-inicio,4)})

    def mover_recepcionista(self, recepcionista, destino):

        origen = recepcionista.posicion

        tiempo = tiempo_desplazamiento(
            origen,
            destino,
            recepcionista.velocidad
        )

        self.registrar_log(
            evento="worker_travel_start",
            tipo_entidad="worker",
            identificador=f"R-{recepcionista.id:02d}",
            ubicacion=origen,
            recurso="receptionists",
            detalles={
                "origin":origen,
                "destination":destino,
                "distance_m":round(
                    float(distancia(origen,destino)),
                    4
                ),
                "duration":round(
                    float(tiempo),
                    4
                ),
                "speed_m_per_min":round(
                    float(recepcionista.velocidad),
                    4
                )
            }
        )

        yield self.env.timeout(tiempo)

        recepcionista.posicion = destino

        self.registrar_log(
            evento="worker_travel_end",
            tipo_entidad="worker",
            identificador=f"R-{recepcionista.id:02d}",
            ubicacion=destino,
            recurso="receptionists",
            detalles={
                "origin":origen,
                "destination":destino,
                "duration":round(
                    float(tiempo),
                    4
                ),
                "speed_m_per_min":round(
                    float(recepcionista.velocidad),
                    4
                )
            }
        )
    def ejecutar_reposicion(self,recepcionista, solicitud):

        insumo = solicitud["insumo"]

        solicitud["estado"] = "ejecucion"

        if insumo == "water":
            destino = CELDA_AGUA
            punto = self.punto_agua
            contenedor = self.agua
            capacidad = CAPACIDAD_AGUA
            evento_inicio = "water_replenishment_start"
            evento_fin = "water_replenishment_end"

        else:
            destino = CELDA_TOALLAS
            punto = self.punto_toallas
            contenedor = self.toallas
            capacidad = CAPACIDAD_TOALLAS
            evento_inicio = "towels_replenishment_start"
            evento_fin = "towels_replenishment_end"

        #viaje desde recepcion
        yield self.env.process(
            self.mover_recepcionista(
                recepcionista,
                destino
            )
        )

        #el punto SOLO se bloquea durante
        #el servicio efectivo de reposicion
        with punto.request() as req:

            yield req

            duracion = self.tiempo_reposicion(
                insumo
            )

            nivel_anterior = contenedor.level

            self.registrar_log(
                evento=evento_inicio,
                tipo_entidad="worker",
                identificador=f"R-{recepcionista.id:02d}",
                ubicacion=destino,
                recurso=insumo,
                detalles={
                    "duration":round(
                        float(duracion),
                        4
                    ),
                    "reason":solicitud["motivo"]
                }
            )

            yield self.env.timeout(duracion)

            cantidad = (
                capacidad-contenedor.level
            )

            if cantidad > 0:
                yield contenedor.put(cantidad)

            self.cantidad_repuesta[
                insumo
            ] += cantidad

            #si habia quiebre termina justo
            #cuando vuelve el stock
            self.finalizar_quiebre(insumo)

            #despertar usuarios esperando
            self.notificar_stock(insumo)

        #el punto ya quedo libre,
        #pero el recepcionista sigue ocupado
        #hasta volver a recepcion
        yield self.env.process(
            self.mover_recepcionista(
                recepcionista,
                CELDA_RECEPCION
            )
        )

        self.registrar_log(
            evento=evento_fin,
            tipo_entidad="worker",
            identificador=f"R-{recepcionista.id:02d}",
            ubicacion=CELDA_RECEPCION,
            recurso=insumo,
            detalles={
                "duration":round(
                    float(duracion),
                    4
                ),
                "old_level":round(
                    float(nivel_anterior),
                    4
                ),
                "new_level":round(
                    float(contenedor.level),
                    4
                ),
                "reason":solicitud["motivo"]
            }
        )

        self.solicitudes_reposicion[
            insumo
        ] = None

        self.tareas_reposicion[
            insumo
        ] = None

        #caso extremo: durante el regreso
        #se volvio a agotar
        if (
            contenedor.level <= 0
            and self.env.now < CIERRE
        ):
            self.activar_quiebre(insumo)

    def salir_usuario(self, usuario):
        for destino in [CELDA_INICIO_ENTRENAMIENTO, CELDA_PASO, CELDA_ACCESO]:
            yield self.env.process(self.mover_usuario(usuario, destino, respetar_limite=False))
        self.registrar_cambio_ocupacion()
        self.usuarios_dentro -= 1
        self.notificar_estado_cierre()
        usuario.hora_salida = self.env.now
        self.registrar_log(evento="exit", usuario=usuario,
            detalles={"occupancy": self.usuarios_dentro, "wait_operational": round(usuario.espera_operacional, 4), "stay": round(self.env.now - usuario.hora_llegada, 4), "planned": len(usuario.rutina),
                "completed": len(usuario.completados), "omitted": len(usuario.omitidos), "cardio_completed":bool(usuario.cardio_completado),"total_wait": round(usuario.espera_total, 4),
                "wait_machine": round(usuario.espera_maquinas, 4),"wait_cardio":round(usuario.espera_cardio,4), "wait_reception": round(usuario.espera_recepcion, 4), "wait_assistance": round(usuario.espera_entrenador, 4),
                "towel_wait": round(usuario.espera_toallas, 4), "water_wait": round(usuario.espera_agua, 4)},)

    def registrar_usuario(self,usuario):

        self.contador_tareas_recepcion += 1

        fin = self.env.event()

        usuario.registro_iniciado = False
        usuario.registro_cancelado = False

        tarea = (
            PRIORIDAD_REGISTRO,
            self.contador_tareas_recepcion,
            "registro",
            usuario,
            fin,
            self.env.now
        )

        yield self.cola_recepcion.put(tarea)

        limite = min(
            usuario.hora_limite,
            CIERRE
        )

        if self.env.now >= limite:
            usuario.registro_cancelado = True
            return False

        resultado = yield (
            fin
            | self.env.timeout(
                limite-self.env.now
            )
        )

        #registro termino normalmente
        if fin in resultado:
            return bool(resultado[fin])

        #si ya habia empezado antes del limite,
        #el registro es no interrumpible
        if usuario.registro_iniciado:

            yield fin

            return True

        #seguia esperando: cancela
        usuario.registro_cancelado = True

        self.notificar_estado_cierre()

        return False

    def proceso_recepcionista(self,recepcionista):

        while True:

            (prioridad,
                orden,
                tipo,
                entidad,
                fin,
                inicio_espera) = yield self.cola_recepcion.get()

            if (
                tipo == "reposicion"
                and prioridad != entidad["prioridad"]
            ):
                continue

            if tipo == "registro":

                usuario = entidad

                limite_usuario = min(
                    usuario.hora_limite,
                    CIERRE
                )


                if (
                    usuario.registro_cancelado
                    or self.env.now >= limite_usuario
                ):

                    usuario.registro_cancelado = True

                    if not fin.triggered:
                        fin.succeed(False)

                    self.notificar_estado_cierre()

                    continue

            elif tipo == "reposicion":

                solicitud = entidad

                if (
                    solicitud["estado"] == "cancelada"
                    or self.env.now >= CIERRE
                ):

                    if not fin.triggered:
                        fin.succeed(False)

                    self.notificar_estado_cierre()

                    continue


            recepcionista.ocupado = True
            recepcionista.tarea_actual = tipo


            if tipo == "registro":

                usuario = entidad

                usuario.registro_iniciado = True

                espera = (
                    self.env.now-inicio_espera
                )

                usuario.espera_recepcion += espera
                usuario.espera_total += espera

                self.registrar_log(
                    evento="registration_start",
                    usuario=usuario,
                    recurso=f"R-{recepcionista.id:02d}",
                    detalles={
                        "queue_wait":round(
                            float(espera),
                            4
                        )
                    }
                )

                duracion = self.tiempo_registro(
                    usuario.perfil
                )

                yield self.env.timeout(duracion)

                usuario.toallas = TOALLAS_INICIALES

                self.generar_asistencias(usuario)

                self.registrar_log(
                    evento="registration_end",
                    usuario=usuario,
                    recurso=f"R-{recepcionista.id:02d}",
                    detalles={
                        "duration":round(
                            float(duracion),
                            4
                        ),
                        "towels":usuario.toallas
                    }
                )
            elif tipo == "reposicion":

                solicitud = entidad

                yield self.env.process(
                    self.ejecutar_reposicion(
                        recepcionista,
                        solicitud
                    )
                )
            recepcionista.ocupado = False
            recepcionista.tarea_actual = None

            self.notificar_estado_cierre()

            if not fin.triggered:
                fin.succeed(True)

    def cancelar_tareas_recepcion_cierre(self):
        for tarea in list(self.cola_recepcion.items):

            (prioridad,
                orden,
                tipo,
                entidad,
                fin,
                inicio) = tarea

            if tipo == "registro":

                entidad.registro_cancelado = True

                if not fin.triggered:
                    fin.succeed(False)

            elif tipo == "reposicion":

                solicitud = entidad

                if solicitud["estado"] == "pendiente":

                    solicitud["estado"] = "cancelada"

                    insumo = solicitud["insumo"]

                    if (self.solicitudes_reposicion[insumo] is solicitud):
                        self.solicitudes_reposicion[insumo] = None

                        self.tareas_reposicion[insumo] = None

                    if not fin.triggered:
                        fin.succeed(False)

        self.notificar_estado_cierre()


    def notificar_estado_cierre(self):

        aviso = self.aviso_estado_cierre
        self.aviso_estado_cierre = self.env.event()

        if not aviso.triggered:
            aviso.succeed()

    def esperar_condicion_cierre(self,condicion):

        while True:

            aviso = self.aviso_estado_cierre

            if condicion():
                return

            yield aviso

    def proceso_cierre(self):
        yield self.env.timeout(CIERRE-self.env.now)
        self.cierre_iniciado = True
        self.registrar_cambio_ocupacion()
        self.cancelar_tareas_recepcion_cierre()

        self.registrar_log(evento="close_started",tipo_entidad="system",identificador="system",detalles={"people_present":self.usuarios_dentro,"maintenance_pending":len(self.cola_reparaciones.items)+sum(t.ocupado for t in self.tecnicos),"water_stock":round(float(self.agua.level),4),"towel_stock":round(float(self.toallas.level),4)})
        self.notificar_estado_cierre()

        #entrenadores: esperan que no quede ninguna asistencia valida ni en ejecucion
        def entrenadores_listos():
            pendientes = any(not p["cancelado"] for p in self.cola_entrenadores.items)
            return not pendientes and all(not e.ocupado for e in self.entrenadores)

        yield self.env.process(self.esperar_condicion_cierre(entrenadores_listos))
        salidas = [self.env.process(self.salir_trabajador(e,"trainers")) for e in self.entrenadores]
        if salidas:
            yield self.env.all_of(salidas)

        #tecnico: espera que salga el ultimo usuario y que terminen reparaciones
        yield self.env.process(self.esperar_condicion_cierre(lambda: self.usuarios_dentro == 0))
        yield self.env.process(self.esperar_condicion_cierre(lambda: len(self.cola_reparaciones.items) == 0 and all(not t.ocupado for t in self.tecnicos)))

        salidas = [self.env.process(self.salir_trabajador(t,"technicians")) for t in self.tecnicos]
        if salidas:
            yield self.env.all_of(salidas)

        #recepcionistas: salen al final
        yield self.env.process(self.esperar_condicion_cierre(lambda: all(not r.ocupado for r in self.recepcionistas)))
        salidas = [self.env.process(self.salir_trabajador(r,"receptionists")) for r in self.recepcionistas]
        if salidas:
            yield self.env.all_of(salidas)

        if not self.fin_replica.triggered:
            self.fin_replica.succeed(self.env.now)

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
gimnasio = Gimnasio(env,seed=2)

gimnasio.iniciar()
env.run(until=gimnasio.fin_replica)

gimnasio.registrar_cambio_ocupacion()
#gimnasio.guardar_log("log_prueba_reasignacion.csv",generar_log=True)
#gimnasio.guardar_log("log_prueba_reasignacion_seeds.csv",generar_log=True)
#gimnasio.guardar_log("log_prueba_fallas.csv", generar_log=True)
#gimnasio.guardar_log("log_prueba_120min.csv", generar_log=True)
#gimnasio.guardar_log("log_prueba_cardio.csv",generar_log=True)
#gimnasio.guardar_log( "log_prueba_reposicion_urgente.csv", generar_log=True)
gimnasio.guardar_log("log_prueba_cierre.csv",generar_log=True)

print("Ocupacion promedio:",gimnasio.area_ocupacion/CIERRE)
print("Proporcion a capacidad:",gimnasio.tiempo_capacidad/CIERRE)

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
print("Fallas de maquinas:",gimnasio.total_fallas)
print("Fin efectivo:",env.now)
print("Operacion post-cierre:",max(0,env.now-CIERRE))
