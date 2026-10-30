import simpy

#def info de cada elemento

class Usuario:
    def __init__(self,id_usuario,perfil,hora_llegada,velocidad):
        self.id = id_usuario
        self.perfil = perfil
        self.hora_llegada = hora_llegada
        self.velocidad = velocidad
        self.posicion = 1
        self.admitido = False
        self.rutina = []
        self.completados = []
        self.pendientes = []
        self.omitidos = []
        self.espera_total = 0
        self.insatisfecho = False
        self.toallas = 0
        self.espera_recepcion = 0
        self.espera_maquinas = 0
        self.espera_entrenador = 0
        self.permanencia_maxima = None
        self.tolerancia = None
        self.capacidad_botella = None
        self.cardio_planificado = False
        self.tipo_rutina = None
        self.asistencia = {}
        self.agua = 0
        self.hora_limite = None
        self.espera_por_ejercicio = {}
        self.espera_agua = 0
        self.espera_toallas = 0
        self.hora_salida = None
        self.espera_operacional = 0

class Maquina:
    def __init__(self,env,tipo,id_maquina,posicion):
        self.env = env
        self.tipo = tipo
        self.id = id_maquina
        self.posicion = posicion
        self.recurso = simpy.Resource(env,capacity=1)
        self.operativa = True
        self.usuario_actual = None
        self.tiempo_uso = 0
        self.tiempo_falla = 0

class Recepcionista:
    def __init__(self,id_recepcionista,velocidad,posicion):
        self.id = id_recepcionista
        self.velocidad = velocidad
        self.posicion = posicion
        self.ocupado = False
        self.tarea_actual = None

class Entrenador:
    def __init__(self,id_entrenador,velocidad,posicion):
        self.id = id_entrenador
        self.velocidad = velocidad
        self.posicion = posicion
        self.ocupado = False
        self.tarea_actual = None

class Tecnico:
    def __init__(self,id_tecnico,velocidad,posicion):
        self.id = id_tecnico
        self.velocidad = velocidad
        self.posicion = posicion
        self.ocupado = False
        self.tarea_actual = None