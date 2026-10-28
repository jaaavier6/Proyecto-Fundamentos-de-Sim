# horarios en minutos desde las 07:00
HORA_APERTURA = 0
FIN_ADMISION = 840
CIERRE = 900

CAPACIDAD_GIMNASIO = 30

N_RECEPCIONISTAS = 2
N_ENTRENADORES = 2
N_TECNICOS = 1

CAPACIDAD_AGUA = 20
UMBRAL_AGUA = 5
INTERVALO_REVISION_AGUA = 35

CAPACIDAD_TOALLAS = 100
UMBRAL_TOALLAS = 30
INTERVALO_REVISION_TOALLAS = 45

# ubicacion de las maquinas
MAQUINAS = {
    "press_pecho": [42,47],
    "press_hombros": [49,45],
    "aperturas_pecho": [46],
    "jalon_pecho": [36,22],
    "remo_sentado": [15,29],
    "curl_biceps": [11,33],
    "prensa_piernas": [26,32],
    "curl_femoral": [31,24],
    "extension_piernas": [12,10],
    "polea": [8,43],
    "trotadora": [14,21,28,35]}

LADO_CELDA = 2.5
PESO_MANHATTAN = 0.7
PESO_EUCLIDIANA = 0.3

CELDA_ACCESO = 1
CELDA_PASO = 6
CELDA_RECEPCION = 7
CELDA_INICIO_ENTRENAMIENTO = 13
CELDA_ENTRENADORES = 25
CELDA_TOALLAS = 44
CELDA_AGUA = 48

TASAS_LLEGADA = {
    "E": [(0,180,5.80),(180,360,7.48),(360,540,6.61),(540,720,9.98),(720,840,11.60)],
    "X": [(0,180,2.50),(180,360,3.31),(360,540,3.31),(540,720,4.99),(720,840,5.80)],
    "F": [(0,180,5.80),(180,360,7.48),(360,540,6.61),(540,720,9.98),(720,840,11.60)],
    "I": [(0,180,5.00),(180,360,6.62),(360,540,6.62),(540,720,9.98),(720,840,11.60)]
}

VELOCIDADES = {
    "E": (55,70,85),
    "X": (70,85,100),
    "F": (55,70,85),
    "I": (48,62,76)
}

PRIORIDAD_URGENTE = 1
PRIORIDAD_REGISTRO = 2
PRIORIDAD_PERIODICA = 3

TOALLAS_INICIALES = 2

VELOCIDADES_TRABAJADORES = {
    "recepcionista": (55,70,85),
    "entrenador": (65,85,105),
    "tecnico": (45,60,75)
}

PARAMETROS_PERFIL = {
    "E": {"permanencia":72,"tolerancia":8,"botella":1.25,"p_cardio":0.40},
    "X": {"permanencia":50,"tolerancia":5,"botella":1.00,"p_cardio":0.15},
    "F": {"permanencia":52,"tolerancia":7,"botella":1.25,"p_cardio":0.35},
    "I": {"permanencia":70,"tolerancia":float("inf"),"botella":1.50,"p_cardio":0.28}
}

# temporal para probar funcionamiento de recepcion
TIEMPO_REGISTRO_PRUEBA = 2