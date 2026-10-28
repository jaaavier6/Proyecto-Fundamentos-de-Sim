
import simpy
import numpy as np
from config import *
from clases import Usuario,Maquina,Recepcionista,Entrenador,Tecnico
from layout import tiempo_desplazamiento

class Gimnasio:
    def __init__(self,env,seed=0):
        self.env = env
        self.rng = np.random.default_rng(seed)

        self.usuarios_dentro = 0
        self.total_llegadas = 0
        self.admitidos = 0
        self.rechazados = 0

        self.maquinas = []
        self.crear_maquinas()

        self.recepcionistas = []
        self.cola_recepcion = simpy.PriorityStore(env)
        self.contador_tareas_recepcion = 0
        self.crear_recepcionistas()

        self.agua = simpy.Container(env,capacity=CAPACIDAD_AGUA,init=CAPACIDAD_AGUA)
        self.toallas = simpy.Container(env,capacity=CAPACIDAD_TOALLAS,init=CAPACIDAD_TOALLAS)

    def crear_maquinas(self):
        for tipo,posiciones in MAQUINAS.items():
            for i,posicion in enumerate(posiciones):
                maquina = Maquina(self.env,tipo,i+1,posicion)
                self.maquinas.append(maquina)

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
        if self.usuarios_dentro >= CAPACIDAD_GIMNASIO:
            self.rechazados += 1
            print(f"[{self.env.now:.2f}] Usuario {usuario.id} ({usuario.perfil}) rechazado")
            return

        usuario.admitido = True
        self.admitidos += 1
        self.usuarios_dentro += 1

        self.configurar_usuario(usuario)

        print(f"[{self.env.now:.2f}] Usuario {usuario.id} ({usuario.perfil}) entra | ocupacion={self.usuarios_dentro}")

        yield self.env.process(self.mover_usuario(usuario,CELDA_PASO))
        yield self.env.process(self.mover_usuario(usuario,CELDA_RECEPCION))

        print(f"[{self.env.now:.2f}] Usuario {usuario.id} llega a recepcion")

        yield self.env.process(self.registrar_usuario(usuario))

        yield self.env.process(self.mover_usuario(usuario,CELDA_PASO))
        yield self.env.process(self.mover_usuario(usuario,CELDA_INICIO_ENTRENAMIENTO))

        print(f"[{self.env.now:.2f}] Usuario {usuario.id} inicia entrenamiento | perfil={usuario.perfil} | rutina={usuario.tipo_rutina} | ejercicios={usuario.rutina} | cardio={usuario.cardio_planificado}")



    def mover_usuario(self,usuario,destino):
        tiempo = tiempo_desplazamiento(usuario.posicion,destino,usuario.velocidad)
        yield self.env.timeout(tiempo)
        usuario.posicion = destino


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

                print(f"[{self.env.now:.2f}] Usuario {usuario.id} inicia registro con R{recepcionista.id} | espera={espera:.2f}")

                duracion = self.tiempo_registro(usuario.perfil)
                yield self.env.timeout(duracion)

                usuario.toallas = TOALLAS_INICIALES
                self.generar_asistencias(usuario)

                print(f"[{self.env.now:.2f}] Usuario {usuario.id} termina registro con R{recepcionista.id} | duracion={duracion:.2f}")

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

        usuario.tipo_rutina = self.generar_tipo_rutina(usuario.perfil)
        usuario.rutina = self.construir_rutina(usuario,usuario.tipo_rutina)
        usuario.pendientes = usuario.rutina.copy()


    def elegir_probabilidad(self,opciones):
        valores = list(opciones.keys())
        probabilidades = list(opciones.values())
        return str(self.rng.choice(valores,p=probabilidades))

    
    def rutina_tren_superior(self):
        empuje_principal = self.elegir_probabilidad(
            PROB_TREN_SUPERIOR["empuje_principal"]
        )

        jalon_principal = self.elegir_probabilidad(
            PROB_TREN_SUPERIOR["jalon_principal"]
        )

        if empuje_principal == "press_pecho":
            empuje_secundario = "press_hombros"
        else:
            empuje_secundario = "aperturas_pecho"

        if jalon_principal == "jalon_pecho":
            jalon_secundario = "remo_sentado"
        else:
            jalon_secundario = "curl_biceps"

        return {
            "empuje_principal": empuje_principal,
            "jalon_principal": jalon_principal,
            "empuje_secundario": empuje_secundario,
            "jalon_secundario": jalon_secundario
        }

    def rutina_cuerpo_completo(self):
        piernas = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["piernas"])
        empuje = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["empuje"])
        jalon = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["jalon"])

        categoria = self.elegir_probabilidad(PROB_CUERPO_COMPLETO["complemento"])

        elegidos = [piernas,empuje,jalon]

        disponibles = [ejercicio for ejercicio in EJERCICIOS[categoria] if ejercicio not in elegidos]

        complemento = str(self.rng.choice(disponibles))

        return {
            "piernas": piernas,
            "empuje": empuje,
            "jalon": jalon,
            "complemento": complemento
        }

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
                rutina = self.ordenar_rutina(
                    usuario.perfil,tipo,componentes
                )

        elif tipo == "cuerpo_completo":
            componentes = self.rutina_cuerpo_completo()

            if usuario.perfil == "F":
                rutina = list(componentes.values())
            else:
                rutina = self.ordenar_rutina(
                    usuario.perfil,tipo,componentes
                )

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

env = simpy.Environment()
gimnasio = Gimnasio(env,seed=0)

gimnasio.iniciar()
env.run(until=60)

print("\nRESUMEN")
print("Llegadas:",gimnasio.total_llegadas)
print("Admitidos:",gimnasio.admitidos)
print("Rechazados:",gimnasio.rechazados)
print("Usuarios dentro:",gimnasio.usuarios_dentro)