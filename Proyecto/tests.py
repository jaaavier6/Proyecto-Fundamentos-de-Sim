import pandas as pd
import numpy as np
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, poisson, gamma, weibull_min
import matplotlib.pyplot as plt

def chi2_dos_muestras(muestra1, muestra2, nombres, categorias):
    obs1 = np.zeros(len(categorias))
    obs2 = np.zeros(len(categorias))
    for i in range(len(categorias)):
        obs1[i]= np.sum(muestra1 == categorias[i])
        obs2[i]= np.sum(muestra2 == categorias[i])
    n1 = len(muestra1)
    n2 = len(muestra2)
    n = n1 + n2
    total_por_categoria = obs1 + obs2
    #frec esperada
    esperados1 = n1 * total_por_categoria / n
    esperados2 = n2 * total_por_categoria / n
    T= 0
    for i in range(len(categorias)):
        T += ((obs1[i] - esperados1[i])**2) / esperados1[i]
        T += ((obs2[i] - esperados2[i])**2) / esperados2[i]
    gl = len(categorias) - 1
    pvalue = 1 - chi2.cdf(T, gl)
    print("---- TEST CHI2 ----")
    print(f"{nombres[0]} vs {nombres[1]}")
    print("T=", round(T,4))
    print("p-value= ", pvalue)

    if pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis de que las muestras vengan de la misma distribución")
        print("     => tiene sentido separar la muestra y ajustar una distribución a cada grupo")
    else:
        print("  => NO se puede rechazar la hipótesis de que las muestras vengan de la misma distribución")
        print("     => no hay evidencia para separar la muestra")
    return T, pvalue



def aplicar_test_kruskal_wallis(muestras, nombres, alpha=0.05):
    resultado_test = kruskal(*muestras)

    print(f"\n === Test Kruskal-Wallis: {' vs '.join(nombres)} ===")
    for nombre, muestra in zip(nombres, muestras):
        print(f"{nombre:15s}"
              f"n = {len(muestra):4d}"
              f"mediana = {np.median(muestra):5.2f}")
    print("  H       =", round(resultado_test.statistic, 4))
    print("  p-value =", resultado_test.pvalue)

    if resultado_test.pvalue < alpha:
        print("  => Se RECHAZA la hipótesis de que las muestras vengan de la",
              "misma distribución")
        print("     => tiene sentido separar la muestra y ajustar una distribución a cada grupo")
    else:
        print("  => NO se puede rechazar la hipótesis de que las muestras vengan de la",
              "misma distribución")
        print("     => no hay evidencia para separar la muestra")
    return resultado_test.statistic, resultado_test.pvalue


def ajuste_ks_gamma(datos, nombre):
    a, loc, scale = gamma.fit(datos, floc=0)
    parametros = (a, loc, scale)
    resultado = kstest(datos, "gamma", args=parametros)
    print(f"\n === Test K-S: {nombre} vs Gamma ===")
    print("a= ", round(a, 4))
    print("scale= ", round(scale, 4))
    print("  D       =", round(resultado.statistic, 4))
    print("  p-value =", resultado.pvalue)

    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis del ajuste", "gamma")
    else:
        print("  => NO se puede rechazar la hipótesis del ajuste", "gamma")


def ajuste_ks_lognormal(datos, nombre):
    s, loc, scale = lognorm.fit(datos, floc=0)
    parametros = (s, loc, scale)
    resultado = kstest(datos, "lognorm", args=parametros)
    print(f"\n === Test K-S: {nombre} vs lognormal ===")
    print("mu= ", round(np.log(scale), 4))
    print("sigma= ", round(s, 4))
    print("  D       =", round(resultado.statistic, 4))
    print("  p-value =", resultado.pvalue)

    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis del ajuste", "lognormal")
    else:
        print("  => NO se puede rechazar la hipótesis del ajuste", "lognormal")



def ajuste_ks_weibull(datos, nombre):
    c, loc, scale = weibull_min.fit(datos, floc=0)
    parametros = (c, loc, scale)
    resultado = kstest(datos, "weibull_min", args=parametros)
    print(f"\n === Test K-S: {nombre} vs Weibull ===")
    print("forma= ", round(c,4))
    print("scale = ", round(scale, 4))
    print("  D       =", round(resultado.statistic, 4))
    print("  p-value =", resultado.pvalue)

    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis del ajuste Weibull")
    else:
        print("  => NO se puede rechazar la hipótesis del ajuste Weibull")




#hacer el test chi cuadrado BONDAD DE AJUSTE

def estimar_alpha(datos):
    alpha = np.mean(datos)
    return alpha

def contar_datos(datos, intervalos):
    N =np.zeros(len(intervalos))
    for i in range(len(datos)):
        for j in range(len(intervalos)):
            if datos.iloc[i] >= intervalos[j][0] and datos.iloc[i] < intervalos[j][1]:
                N[j] += 1
                break
    return N

def calcular_T(N, intervalos, alpha):
    T = 0
    n = np.sum(N)
    for i in range(len(intervalos)):
        inferior = intervalos[i][0]
        superior = intervalos[i][1]
        p_i = (poisson.cdf(superior - 1, alpha) - poisson.cdf(inferior - 1, alpha))
        esperado = n * p_i
        T += ((N[i] - esperado)**2) / esperado
    return T

def calcular_pvalue(T, k, m):
    gl = k - m - 1
    pvalue = 1 - chi2.cdf(T, gl)
    return pvalue
