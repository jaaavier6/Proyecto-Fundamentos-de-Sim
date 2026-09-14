import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import ks_2samp


#tasas estimadas en la parte 2, en llegadas por minuto (me ayude con la IA para pasar todos los datos)

lambda_standard_flexible = np.array([
    0.17583333333333334,
    0.20166666666666666,
    0.17916666666666667,
    0.18666666666666668,
    0.19666666666666666,
    0.17416666666666666,
    0.2425,
    0.2608333333333333,
    0.22916666666666666,
    0.27166666666666667,
    0.24833333333333332,
    0.25916666666666666,
    0.21166666666666667,
    0.2175,
    0.20916666666666667,
    0.21583333333333332,
    0.22,
    0.22,
    0.31833333333333336,
    0.33166666666666667,
    0.33666666666666667,
    0.3225,
    0.35333333333333333,
    0.3416666666666667,
    0.38916666666666666,
    0.38333333333333336,
    0.365,
    0.4025
])


lambda_express = np.array([
    0.045,
    0.03916666666666667,
    0.0525,
    0.050833333333333335,
    0.04833333333333333,
    0.03916666666666667,
    0.055,
    0.058333333333333334,
    0.050833333333333335,
    0.059166666666666666,
    0.07083333333333333,
    0.059166666666666666,
    0.06,
    0.060833333333333336,
    0.06166666666666667,
    0.049166666666666664,
    0.056666666666666664,
    0.051666666666666666,
    0.07333333333333333,
    0.09166666666666666,
    0.08333333333333333,
    0.07833333333333334,
    0.0875,
    0.07666666666666666,
    0.095,
    0.1,
    0.1025,
    0.0975
])


lambda_intense = np.array([
    0.08833333333333333,
    0.09083333333333334,
    0.08,
    0.07416666666666667,
    0.09083333333333334,
    0.07833333333333334,
    0.10583333333333333,
    0.11,
    0.105,
    0.12916666666666668,
    0.10166666666666667,
    0.10416666666666667,
    0.1025,
    0.09333333333333334,
    0.10916666666666666,
    0.12166666666666667,
    0.09916666666666667,
    0.09416666666666666,
    0.17416666666666666,
    0.17583333333333334,
    0.16,
    0.1675,
    0.16166666666666665,
    0.15333333333333332,
    0.18916666666666668,
    0.19583333333333333,
    0.20333333333333334,
    0.18166666666666667
])


#probabilidades para separar Standard y Flexible
p_standard = 4485 / (4485 + 4472)
p_flexible = 1 - p_standard

#calcula los valores acumulados M

def calcular_M(lambdas):
    M = [0]
    for tasa in lambdas:
        nuevo_M = M[-1] + tasa * 30
        M.append(nuevo_M)
    return np.array(M)

M_standard_flexible = calcular_M(lambda_standard_flexible)
M_express = calcular_M(lambda_express)
M_intense = calcular_M(lambda_intense)


def inversa_m(y, lambdas, M):

    for j in range(len(lambdas)):
        if M[j] <= y < M[j + 1]:

            t = 30*j + (y - M[j]) / lambdas[j]
            return t

def simular_ppnh(lambdas):

    M = calcular_M(lambdas)
    S = 0
    llegadas = []

    while True:
        #generamos el siguiente salto Exp(1)
        E = np.random.exponential(1)
        S = S + E
        #si supera m(T), terminamos la jornada
        if S >= M[-1]:
            break
        #transformamos desde la escala acumulada al tiempo real
        t = inversa_m(S, lambdas, M)
        llegadas.append(t)

    return np.array(llegadas)

#simularemos 200 jornadas

np.random.seed(123)

n_simulaciones = 200

#guardaremos todos los tiempos simulados por perfil
sim_standard = []
sim_flexible = []
sim_express = []
sim_intense = []


for dia in range(n_simulaciones):

    #simulamos los tres procesos
    llegadas_sf = simular_ppnh(lambda_standard_flexible)
    llegadas_express = simular_ppnh(lambda_express)
    llegadas_intense = simular_ppnh(lambda_intense)


    #separamos Standard y Flexible
    for llegada in llegadas_sf:

        U = np.random.uniform()

        if U < p_standard:
            sim_standard.append(llegada)
        else:
            sim_flexible.append(llegada)

    sim_express.extend(llegadas_express)
    sim_intense.extend(llegadas_intense)


#pasamos las listas a arreglos
sim_standard = np.array(sim_standard)
sim_flexible = np.array(sim_flexible)
sim_express = np.array(sim_express)
sim_intense = np.array(sim_intense)


print("\n-------- SIMULACION DE 200 JORNADAS --------")

print("Standard:", len(sim_standard))
print("Flexible:", len(sim_flexible))
print("Express:", len(sim_express))
print("Intense:", len(sim_intense))

#vuelvo a leer el log 

#datos observados

log = pd.read_csv(
    "log_operacional_limpio.csv",
    sep=";",
    decimal=","
)

llegadas_reales = log[
    log["event_type"] == "visit"
].copy()

n_dias_reales = llegadas_reales["day_id"].nunique()


real_standard = llegadas_reales[
    llegadas_reales["profile"] == "standard"
]["event_time"].values

real_flexible = llegadas_reales[
    llegadas_reales["profile"] == "flexible"
]["event_time"].values

real_express = llegadas_reales[
    llegadas_reales["profile"] == "express"
]["event_time"].values

real_intense = llegadas_reales[
    llegadas_reales["profile"] == "intense"
]["event_time"].values

#comparacion grafica observado vs simulado (me ayude de la IA)

intervalos = np.arange(0, 841, 30)

perfiles = [
    "Standard",
    "Flexible",
    "Express",
    "Intense"
]

reales = [
    real_standard,
    real_flexible,
    real_express,
    real_intense
]

simulados = [
    sim_standard,
    sim_flexible,
    sim_express,
    sim_intense
]


fig, axes = plt.subplots(2, 2, figsize=(14, 8))

axes = axes.flatten()


for i in range(len(perfiles)):

    #conteos observados por intervalo
    conteo_real, _ = np.histogram(
        reales[i],
        bins=intervalos
    )

    #conteos simulados por intervalo
    conteo_simulado, _ = np.histogram(
        simulados[i],
        bins=intervalos
    )


    #promedio por jornada
    promedio_real = conteo_real / n_dias_reales

    promedio_simulado = conteo_simulado / n_simulaciones


    axes[i].plot(
        intervalos[:-1],
        promedio_real,
        marker="o",
        label="Observado"
    )

    axes[i].plot(
        intervalos[:-1],
        promedio_simulado,
        marker="o",
        label="Simulado"
    )

    axes[i].set_title(perfiles[i])

    axes[i].set_xlabel(
        "Minutos desde las 07:00"
    )

    axes[i].set_ylabel(
        "Llegadas promedio"
    )

    axes[i].grid(
        linestyle="--",
        alpha=0.5
    )

    axes[i].legend()


plt.suptitle(
    "Comparación de llegadas observadas y simuladas"
)

plt.tight_layout()

def test_ks_dos_muestras(observados, simulados, nombre):

    resultado = ks_2samp(observados,simulados)

    print(f"\n Test K-S Observado vs Simulado: {nombre} ")
    print("  D       =", resultado.statistic)
    print("  p-value =", resultado.pvalue)


    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA que ambas muestras "
            "tengan la misma distribución.")

    else:
        print("  => NO se puede rechazar que ambas "
            "muestras tengan la misma distribución.")


print("\nTEST K-S OBSERVADO VS SIMULADO")

test_ks_dos_muestras(real_standard, sim_standard, "Standard")

test_ks_dos_muestras(real_flexible,sim_flexible,"Flexible")

test_ks_dos_muestras(real_express,sim_express,"Express")

test_ks_dos_muestras(real_intense,sim_intense,"Intense")

plt.show()





