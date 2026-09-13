import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2, kruskal, kstest, poisson


log = pd.read_csv(
    "log_operacional_historico.csv",
    sep=";",
    decimal=","
)

llegadas = log[log["event_type"] == "visit"].copy()


print("Cantidad de intentos de llegada:", len(llegadas))

print("\nPerfiles:")
print(llegadas["profile"].value_counts())


llegadas["intervalo_30m"] = (
    np.floor(llegadas["event_time"] / 30) * 30
).astype(int)

#discriminaremos por perfil

n_dias = llegadas["day_id"].nunique()

perfiles = ["standard", "express", "flexible", "intense"]


#para graficar nos ayudamos de la IA 
fig, axes = plt.subplots(2, 2, figsize=(14, 8))

axes = axes.flatten()

for i, perfil in enumerate(perfiles):

    datos = llegadas[llegadas["profile"] == perfil]

    conteo = (
        datos
        .groupby("intervalo_30m")
        .size()
        / n_dias
    )

    conteo.plot(
        kind="bar",
        ax=axes[i],
        edgecolor="black",
        alpha=0.8
    )

    axes[i].set_title(perfil.capitalize())
    axes[i].set_xlabel("Minutos desde las 07:00")
    axes[i].set_ylabel("Llegadas promedio")
    axes[i].tick_params(axis="x", rotation=45)
    axes[i].grid(axis="y", linestyle="--", alpha=0.5)

plt.suptitle(
    "Perfil de llegadas promedio cada 30 minutos por perfil",
    fontsize=14,
    fontweight="bold"
)

plt.tight_layout()


#ahora veremos como se comporta el numero de llegadas por perfil

conteos_dia_perfil = (
    llegadas
    .groupby(["day_id", "profile"])
    .size()
    .unstack(fill_value=0)
)

print(conteos_dia_perfil.head(40))

print("\nTEST CHI-CUADRADO PARA POISSON")
# comprobaremos con chi-cuadrado si el conteo diario es Poisson

def estimar_alpha(datos):
    alpha = np.mean(datos)
    return alpha


def crear_intervalos(alpha):
    cortes = poisson.ppf(
        [1/6, 2/6, 3/6, 4/6, 5/6],
        alpha
    )

    intervalos = [
        [0, cortes[0] + 1],
        [cortes[0] + 1, cortes[1] + 1],
        [cortes[1] + 1, cortes[2] + 1],
        [cortes[2] + 1, cortes[3] + 1],
        [cortes[3] + 1, cortes[4] + 1],
        [cortes[4] + 1, np.inf]
    ]

    return intervalos


def contar_datos(datos, intervalos):
    N = np.zeros(len(intervalos))

    for i in range(len(datos)):
        for j in range(len(intervalos)):
            if datos[i] >= intervalos[j][0] and datos[i] < intervalos[j][1]:
                N[j] += 1
                break

    return N


def calcular_T(N, intervalos, alpha):
    T = 0
    n = np.sum(N)

    for i in range(len(intervalos)):
        inferior = intervalos[i][0]
        superior = intervalos[i][1]

        if superior == np.inf:
            p_i = 1 - poisson.cdf(inferior - 1, alpha)
        else:
            p_i = (
                poisson.cdf(superior - 1, alpha)
                - poisson.cdf(inferior - 1, alpha)
            )

        esperado = n * p_i

        T += ((N[i] - esperado)**2) / esperado

    return T


def calcular_pvalue(T, k, m):
    gl = k - m - 1
    pvalue = 1 - chi2.cdf(T, gl)

    return pvalue



for perfil in perfiles:

    print(f"\n---------- {perfil} ----------")

    datos = conteos_dia_perfil[perfil].values

    alpha = estimar_alpha(datos)
    intervalos = crear_intervalos(alpha)

    N = contar_datos(datos, intervalos)

    T = calcular_T(N, intervalos, alpha)

    pvalue = calcular_pvalue(
        T,
        len(intervalos),
        1
    )

    print("Lambda:", alpha)
    print("Intervalos:", intervalos)
    print("Conteos observados:", N)
    print("T:", T)
    print("p-value:", pvalue)

    if pvalue < 0.05:
        print("Se RECHAZA la hipótesis de ajuste Poisson")
    else:
        print("No se puede rechazar la hipótesis de ajuste Poisson")


#como no se rechazó ninguna hipotesis podemos seguir con el siguiente paso, 
#ver si podemos agrupar las muestras 

def aplicar_test_kruskal_wallis(muestras, nombres, alpha=0.05):
    resultado_test = kruskal(*muestras)

    print(f"\n === Test Kruskal-Wallis: {' vs '.join(nombres)} ===")
    for nombre, muestra in zip(nombres, muestras):
        print(f"   {nombre:20s} n = {len(muestra):4d}   "
            f"mediana = {np.median(muestra):5.2f}")
    print("  H       =", round(resultado_test.statistic, 4))
    print("  p-value =", resultado_test.pvalue)

    if resultado_test.pvalue < alpha:
        print("  => Se RECHAZA la hipótesis de que las muestras vengan de la",
            "misma distribución")
        print("     => tiene sentido separar la muestra y analizar cada perfil por separado")
    else:
        print("  => NO se puede rechazar la hipótesis de que las muestras vengan de la",
            "misma distribución")
        print("     => no hay evidencia para separar la muestra por perfil")


standard = conteos_dia_perfil["standard"].values
express = conteos_dia_perfil["express"].values
flexible = conteos_dia_perfil["flexible"].values
intense = conteos_dia_perfil["intense"].values

muestras = [standard, express, flexible, intense]
nombres = ["Standard", "Express", "Flexible", "Intense"]

comparados = []

for nombre1, muestra1 in zip(nombres, muestras):
    for nombre2, muestra2 in zip(nombres, muestras):
        if nombre1 != nombre2 and {nombre1, nombre2} not in comparados:
            aplicar_test_kruskal_wallis(
                [muestra1, muestra2],
                [nombre1, nombre2],
                alpha=0.05
            )
            comparados.append({nombre1, nombre2})

#ahora comprobaremos homogeniedad bajo los grupos que podemos y no agrupar

standard_flexible_llegadas = llegadas[llegadas["profile"].isin(["standard", "flexible"])]["event_time"].values

express_llegadas = llegadas[llegadas["profile"] == "express"]["event_time"].values

intense_llegadas = llegadas[llegadas["profile"] == "intense"]["event_time"].values


print("\nAhora comprobare homogeneidad")

T = 840

def test_homogeneidad_ks(datos_t, T, nombre):
    res = kstest(datos_t, 'uniform', args=(0, T))

    print(f"\n     Test K-S Homogeneidad: {nombre}  ")
    print(f"  D       = {res.statistic}")
    print(f"  p-value = {res.pvalue}")

    if res.pvalue < 0.05:
        print("  => Se RECHAZA que vengan de una Uniforme.")
    else:
        print("  => NO se rechaza. Es una Uniforme.")


test_homogeneidad_ks(
    standard_flexible_llegadas,
    T,
    "Standard + Flexible"
)

test_homogeneidad_ks(
    express_llegadas,
    T,
    "Express"
)

test_homogeneidad_ks(
    intense_llegadas,
    T,
    "Intense"
)

#ahora como todos los grupos nos dieron PPNH hay que estimar lambda(t)


#usaremos intervalos de 30 minutos, igual que en el analisis exploratorio

tramos = []

for inicio in range(0, 840, 30):
    tramos.append([inicio, inicio + 30])


def estimar_lambdas(datos, tramos, n_dias):

    lambdas = []

    for tramo in tramos:

        inferior = tramo[0]
        superior = tramo[1]

        cantidad = np.sum(
            (datos >= inferior) &
            (datos < superior)
        )
        largo_tramo = superior - inferior
        # tasa de llegadas por minuto
        lambda_j = cantidad / (n_dias * largo_tramo)
        lambdas.append(lambda_j)

    return np.array(lambdas)


lambda_standard_flexible = estimar_lambdas(
    standard_flexible_llegadas,
    tramos,
    n_dias
)

lambda_express = estimar_lambdas(
    express_llegadas,
    tramos,
    n_dias
)

lambda_intense = estimar_lambdas(
    intense_llegadas,
    tramos,
    n_dias
)

print("\n TASAS ESTIMADAS")

print("\nStandard + Flexible")
for i in range(len(tramos)):
    print(
        tramos[i],
        "lambda =",
        lambda_standard_flexible[i]
    )

print("\nExpress")
for i in range(len(tramos)):
    print(
        tramos[i],
        "lambda =",
        lambda_express[i]
    )

print("\nIntense")
for i in range(len(tramos)):
    print(
        tramos[i],
        "lambda =",
        lambda_intense[i]
    )

#Ahora calculamos  la acumulada m(t)/m(T) para aplicar un test K_S y verificar que lambda(t) se ajusta a la muestra 
def calcular_m(t, lambdas, tramos):
    m = 0

    for i in range(len(tramos)):
        inferior = tramos[i][0]
        superior = tramos[i][1]
        if t >= superior:
            #sumamos el tramo completo
            m += lambdas[i] * (superior - inferior)
        elif t > inferior:
            #sumamos solo la parte del tramo hasta t
            m += lambdas[i] * (t - inferior)
            break
        else:
            break
    return m

#calculamos el nnumero esperado de llegadas
print("\n m(T) ")

print("Standard + Flexible:",calcular_m(840, lambda_standard_flexible, tramos))

print("Express:",calcular_m(840, lambda_express, tramos))

print("Intense:",calcular_m(840, lambda_intense, tramos))



def F_modelo(t, lambdas, tramos):
    m_total = calcular_m(840, lambdas, tramos)

    resultados = []
    for valor in t:
        resultados.append(calcular_m(valor, lambdas, tramos) / m_total)

    return np.array(resultados)


def ajuste_ks_ppnh(datos, lambdas, tramos, nombre):

    resultado = kstest(
        datos,
        lambda t: F_modelo(t, lambdas, tramos))

    print(f"\n Test K-S PPNH: {nombre} ")
    print("  D       =", resultado.statistic)
    print("  p-value =", resultado.pvalue)

    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA el ajuste al PPNH propuesto.")
    else:
        print("  => NO se puede rechazar el ajuste al PPNH propuesto.")

print("\n VALIDACION DE LOS PPNH ")


ajuste_ks_ppnh(
    standard_flexible_llegadas,
    lambda_standard_flexible,
    tramos,
    "Standard + Flexible"
)

ajuste_ks_ppnh(
    express_llegadas,
    lambda_express,
    tramos,
    "Express"
)

ajuste_ks_ppnh(
    intense_llegadas,
    lambda_intense,
    tramos,
    "Intense"
)


plt.show()




