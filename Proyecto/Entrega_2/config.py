#def reglas y parametros

PERFILES_LOG = {"E": "standard", "X": "express", "F": "flexible", "I": "intense"}

EJERCICIOS_LOG = {
    "press_pecho": "chest_press", "press_hombros": "shoulder_press", "aperturas_pecho": "chest_fly",
    "jalon_pecho": "lat_pulldown", "remo_sentado": "seated_row",
    "curl_biceps": "biceps_curl", "prensa_piernas": "leg_press", "curl_femoral": "leg_curl",
    "extension_piernas": "leg_extension", "polea": "cable", "trotadora": "treadmill"}


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
MAQUINAS = {"press_pecho": [42,47],
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
    "I": [(0,180,5.00),(180,360,6.62),(360,540,6.62),(540,720,9.98),(720,840,11.60)]}

VELOCIDADES = {"E": (55,70,85),
    "X": (70,85,100),
    "F": (55,70,85),
    "I": (48,62,76)}

PRIORIDAD_URGENTE = 1
PRIORIDAD_REGISTRO = 2
PRIORIDAD_PERIODICA = 3

TOALLAS_INICIALES = 2

VELOCIDADES_TRABAJADORES = {"recepcionista": (55,70,85),
    "entrenador": (65,85,105),
    "tecnico": (45,60,75)}

PARAMETROS_PERFIL = {"E": {"permanencia":72,"tolerancia":8,"botella":1.25,"p_cardio":0.40},
    "X": {"permanencia":50,"tolerancia":5,"botella":1.00,"p_cardio":0.15},
    "F": {"permanencia":52,"tolerancia":7,"botella":1.25,"p_cardio":0.35},
    "I": {"permanencia":70,"tolerancia":float("inf"),"botella":1.50,"p_cardio":0.28}}

EJERCICIOS = {"empuje": ["press_pecho","press_hombros","aperturas_pecho"],
    "jalon": ["jalon_pecho","remo_sentado","curl_biceps"],
    "piernas": ["prensa_piernas","extension_piernas","curl_femoral"]}

PROB_TREN_SUPERIOR = {"empuje_principal": {"press_pecho": 0.65,"press_hombros": 0.35},
    "jalon_principal": {"jalon_pecho": 0.55,"remo_sentado": 0.45}}

PROB_CUERPO_COMPLETO = {
    "piernas": {"prensa_piernas": 0.70,"extension_piernas": 0.20,"curl_femoral": 0.10},
    "empuje": {"press_pecho": 0.60, "press_hombros": 0.30, "aperturas_pecho": 0.10},
    "jalon": {"jalon_pecho": 0.50, "remo_sentado": 0.40, "curl_biceps": 0.10},
    "complemento": {"piernas": 0.40, "empuje": 0.30, "jalon": 0.30}}


PROB_POLEA = {
    "E": {"empuje":0.18,"jalon":0.22, "piernas":0.12, "tren_superior":0.20, "cuerpo_completo":0.15},
    "X": {"empuje":0.18, "jalon":0.22, "piernas":0.12, "tren_superior":0.20, "cuerpo_completo":0.15},
    "F": {"empuje":0.40, "jalon":0.44, "piernas":0.28, "tren_superior":0.38, "cuerpo_completo":0.32},
    "I": {"empuje":0.40, "jalon":0.44, "piernas":0.28, "tren_superior":0.38, "cuerpo_completo":0.32}}

PROB_ASISTENCIA = {
    "press_pecho":       {"E":0.10,"X":0.06,"F":0.12,"I":0.06},
    "press_hombros":     {"E":0.12,"X":0.07,"F":0.14,"I":0.08},
    "aperturas_pecho":   {"E":0.06,"X":0.04,"F":0.08,"I":0.05},
    "jalon_pecho":       {"E":0.10,"X":0.06,"F":0.12,"I":0.06},
    "remo_sentado":      {"E":0.10,"X":0.06,"F":0.12,"I":0.06},
    "curl_biceps":       {"E":0.05,"X":0.03,"F":0.06,"I":0.03},
    "prensa_piernas":    {"E":0.14,"X":0.09,"F":0.18,"I":0.09},
    "curl_femoral":      {"E":0.08,"X":0.05,"F":0.10,"I":0.05},
    "extension_piernas": {"E":0.06,"X":0.04,"F":0.08,"I":0.05},
    "polea":              {"E":0.15,"X":0.09,"F":0.18,"I":0.10}
}

PROB_RUTINA = {
    "E": {"empuje":0.20, "jalon":0.20, "piernas":0.20, "tren_superior":0.25, "cuerpo_completo":0.15},
    "X": {"empuje":0.20, "jalon":0.20, "piernas":0.20, "tren_superior":0.25, "cuerpo_completo":0.15},
    "F": {"empuje":0.15, "jalon":0.15, "piernas":0.15, "tren_superior":0.30, "cuerpo_completo":0.25},
    "I": {"empuje":0.25, "jalon":0.25, "piernas":0.25, "tren_superior":0.15, "cuerpo_completo":0.10}}

GRUPO_FUERZA = {"press_pecho": "G1", "press_hombros": "G1", "jalon_pecho": "G1", "remo_sentado": "G1", "polea": "G1",
    "aperturas_pecho": "G2", "curl_biceps": "G2",
    "prensa_piernas": "G3",
    "curl_femoral": "G4","extension_piernas": "G4"}



PARAMETROS_FUERZA = {
    "G1": {"E": (16, 0.50), "X": (3, 3, 3, 6), "F": (16, 0.50), "I": (16, 0.725)},
    "G2": {"E": (16, 0.375), "X": (3, 3, 2.5, 5), "F": (16, 0.375), "I": (16, 0.54375)},
    "G3": {"E": (16, 0.625), "X": (3, 3, 4, 7), "F": (16, 0.625), "I": (16, 0.90625)},
    "G4": {"E": (16, 0.4375), "X": (3, 3, 3, 5.5), "F": (16, 0.4375), "I": (16, 0.634375)}}

TOALLAS_MINIMAS = 1
TOALLAS_POR_EJERCICIO = 1
MAX_TOALLAS_RETIRO = 2

TIEMPO_RETIRO_AGUA = 0.75
TIEMPO_RETIRO_TOALLAS = 0.75

CATEGORIA_EJERCICIO = {
    "press_pecho":"empuje",
    "press_hombros":"empuje",
    "aperturas_pecho":"empuje",
    "jalon_pecho":"jalon",
    "remo_sentado":"jalon",
    "curl_biceps":"jalon",
    "prensa_piernas":"piernas",
    "curl_femoral":"piernas",
    "extension_piernas":"piernas",
    "polea":"multifuncional"
}

CONSUMO_AGUA = {
    "E": {
        "empuje":(9,0.03),
        "jalon":(9,0.03),
        "piernas":(9,0.04),
        "multifuncional":(9,0.03)
    },
    "X": {
        "empuje":(9,0.03),
        "jalon":(9,0.03),
        "piernas":(9,0.04),
        "multifuncional":(9,0.03)
    },
    "F": {
        "empuje":(9,0.03),
        "jalon":(9,0.03),
        "piernas":(9,0.04),
        "multifuncional":(9,0.03)
    },
    "I": {
        "empuje":(9,0.045),
        "jalon":(9,0.045),
        "piernas":(9,0.06),
        "multifuncional":(9,0.045)
    }
}

PROB_FALLA = {
    "trotadora":0.005,
    "press_pecho":0.004,
    "press_hombros":0.004,
    "aperturas_pecho":0.004,
    "jalon_pecho":0.004,
    "remo_sentado":0.004,
    "curl_biceps":0.004,
    "prensa_piernas":0.005,
    "curl_femoral":0.005,
    "extension_piernas":0.005,
    "polea":0.006
}


PARAMETROS_DURACION_CARDIO = {
    "E":{
        "modelo":"gamma_acotada",
        "shape":9,
        "scale":2.0,
        "maximo":28
    },

    "X":{
        "modelo":"beta_escalada",
        "a":3,
        "b":3,
        "minimo":6,
        "maximo":12
    },

    "F":{
        "modelo":"mezcla",
        "p_gamma":0.75,
        "gamma_shape":12,
        "gamma_scale":1.2,
        "log_mu":3.0,
        "log_sigma":0.18
    },

    "I":{
        "modelo":"mezcla",
        "p_gamma":0.70,
        "gamma_shape":10,
        "gamma_scale":2.3,
        "log_mu":3.55,
        "log_sigma":0.20
    }
}

PARAMETROS_REPOSICION = {
    "water":{
        "p_gamma":0.75,
        "gamma_shape":16,
        "gamma_scale":0.35,
        "log_mu":2.45,
        "log_sigma":0.30
    },

    "towels":{
        "gamma_shape":16,
        "gamma_scale":0.25
    }
}