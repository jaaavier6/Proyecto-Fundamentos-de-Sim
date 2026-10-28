
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
        print(f"[{self.env.now:.2f}] Usuario {usuario.id} ({usuario.perfil}) entra | ocupacion={self.usuarios_dentro}")

        yield self.env.process(self.mover_usuario(usuario,CELDA_PASO))
        yield self.env.process(self.mover_usuario(usuario,CELDA_RECEPCION))
        print(f"[{self.env.now:.2f}] Usuario {usuario.id} llega a recepcion")

        yield self.env.process(self.registrar_usuario(usuario))
        self.configurar_usuario(usuario)

        yield self.env.process(self.mover_usuario(usuario,CELDA_PASO))
        yield self.env.process(self.mover_usuario(usuario,CELDA_INICIO_ENTRENAMIENTO))

        print(f"[{self.env.now:.2f}] Usuario {usuario.id} llega al inicio del entrenamiento | perfil={usuario.perfil} | permanencia={usuario.permanencia_maxima} | tolerancia={usuario.tolerancia} | cardio={usuario.cardio_planificado}")




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
                yield self.env.timeout(TIEMPO_REGISTRO_PRUEBA)

                usuario.toallas = TOALLAS_INICIALES
                print(f"[{self.env.now:.2f}] Usuario {usuario.id} termina registro con R{recepcionista.id}")

            recepcionista.ocupado = False
            recepcionista.tarea_actual = None
            fin.succeed()


    def configurar_usuario(self,usuario):
        parametros = PARAMETROS_PERFIL[usuario.perfil]

        usuario.permanencia_maxima = parametros["permanencia"]
        usuario.tolerancia = parametros["tolerancia"]
        usuario.capacidad_botella = parametros["botella"]
        usuario.cardio_planificado = self.rng.random() < parametros["p_cardio"]


env = simpy.Environment()
gimnasio = Gimnasio(env,seed=0)

gimnasio.iniciar()
env.run(until=FIN_ADMISION)

print("\nRESUMEN")
print("Llegadas:",gimnasio.total_llegadas)
print("Admitidos:",gimnasio.admitidos)
print("Rechazados:",gimnasio.rechazados)
print("Usuarios dentro:",gimnasio.usuarios_dentro)