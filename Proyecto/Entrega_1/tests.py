import pandas as pd
import numpy as np
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, poisson, gamma, weibull_min, fisk
import matplotlib.pyplot as plt
from scipy.optimize import minimize

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


def ajuste_ks_loglogistica(datos, nombre):
    c, loc, scale = fisk.fit(datos, floc=0)
    parametros = (c, loc, scale)
    resultado = kstest(datos, "fisk", args=parametros)
    print(f"\n === Test K-S: {nombre} vs Log-logística ===")
    print("forma =", round(c, 4))
    print("scale =", round(scale, 4))
    print("D       =", round(resultado.statistic, 4))
    print("p-value =", resultado.pvalue)
    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis del ajuste Log-logística")
    else:
        print("  => NO se puede rechazar la hipótesis del ajuste Log-logística")


def parametros_gamma_lognormal(datos):
    datos = np.asarray(datos)
    datos = datos[~np.isnan(datos)]
    # Valores iniciales
    mediana = np.median(datos)
    grupo_1 = datos[datos <= mediana]
    grupo_2 = datos[datos > mediana]
    # Gamma inicial
    a_0, loc_gamma_0, scale_gamma_0 = gamma.fit(grupo_1,floc=0)
    # Lognormal inicial
    sigma_0, loc_log_0, scale_log_0 = lognorm.fit(grupo_2,floc=0)
    mu_0 = np.log(scale_log_0)
    w_0 = len(grupo_1) / len(datos)
    parametros_iniciales = [w_0,a_0,scale_gamma_0,mu_0,sigma_0]
    # Log-verosimilitud negativa
    def log_verosimilitud_negativa(parametros):
        w, a, scale_gamma, mu, sigma = parametros
        densidad_gamma = gamma.pdf(datos,a=a,loc=0,scale=scale_gamma)
        densidad_lognormal = lognorm.pdf(datos,s=sigma,loc=0,scale=np.exp(mu))
        densidad_mezcla = (w * densidad_gamma + (1 - w) * densidad_lognormal)
        densidad_mezcla = np.maximum(densidad_mezcla, 1e-300)
        return -np.sum(np.log(densidad_mezcla))
    # Restricciones
    limites = [
        (0.0001, 0.9999),  # w
        (0.0001, None),    # forma Gamma
        (0.0001, None),    # escala Gamma
        (None, None),      # mu Lognormal
        (0.0001, None)]     # sigma Lognormal

    resultado = minimize(log_verosimilitud_negativa,parametros_iniciales,method="L-BFGS-B",bounds=limites)

    w, a, scale_gamma, mu, sigma = resultado.x

    return w, a, scale_gamma, mu, sigma


def parametros_gamma_gamma(datos):
    datos = np.asarray(datos)
    datos = datos[~np.isnan(datos)]
    mediana = np.median(datos)
    grupo_1 = datos[datos <= mediana]
    grupo_2 = datos[datos > mediana]
    a1_0, loc1_0, scale1_0 = gamma.fit(grupo_1,floc=0)
    a2_0, loc2_0, scale2_0 = gamma.fit(grupo_2, floc=0)
    w_0 = len(grupo_1) / len(datos)
    parametros_iniciales = [w_0, a1_0, scale1_0, a2_0, scale2_0]
    # Log-verosimilitud negativa
    def log_verosimilitud_negativa(parametros):
        w, a1, scale1, a2, scale2 = parametros
        densidad_1 = gamma.pdf(datos, a=a1, loc=0, scale=scale1)
        densidad_2 = gamma.pdf(datos, a=a2, loc=0, scale=scale2)
        densidad_mezcla = (w * densidad_1 + (1 - w) * densidad_2)
        # Evita log(0)
        densidad_mezcla = np.maximum(densidad_mezcla, 1e-300)
        return -np.sum(np.log(densidad_mezcla))
    # Restricciones
    limites = [
        (0.0001, 0.9999),  # w
        (0.0001, None),    # a1
        (0.0001, None),    # scale1
        (0.0001, None),    # a2
        (0.0001, None)]     # scale2
    resultado = minimize(log_verosimilitud_negativa,parametros_iniciales,method="L-BFGS-B",bounds=limites)
    w, a1, scale1, a2, scale2 = resultado.x
    # Ordenamos las componentes por su media
    media_1 = a1 * scale1
    media_2 = a2 * scale2
    if media_1 > media_2:
        w = 1 - w
        a1, a2 = a2, a1
        scale1, scale2 = scale2, scale1
    return w, a1, scale1, a2, scale2


def ajuste_ks_gamma_gamma(datos, w, a1, scale1, a2, scale2, nombre):
    def cdf_mezcla(x):
        return (w * gamma.cdf(x, a=a1, loc=0, scale=scale1) +
            (1 - w) * gamma.cdf( x, a=a2, loc=0, scale=scale2))
    resultado = kstest(datos, cdf_mezcla)
    print(
        f"\n === Test K-S: {nombre} vs mezcla Gamma-Gamma ===")

    print("w =", round(w, 4))

    print("Gamma 1:")
    print("forma =", round(a1, 4))
    print("escala =", round(scale1, 4))

    print("Gamma 2:")
    print("forma =", round(a2, 4))
    print("escala =", round(scale2, 4))

    print("D       =", round(resultado.statistic, 4))
    print("p-value =", resultado.pvalue)

    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis del ajuste " "Gamma-Gamma")
    else:
        print("  => NO se puede rechazar la hipótesis del ajuste " "Gamma-Gamma")



def ajuste_ks_gamma_lognormal(datos, w, a, scale_gamma, mu, sigma, nombre):
    def cdf_mezcla(x):
        return (w * gamma.cdf(x, a=a, loc=0, scale=scale_gamma) +
            (1 - w) * lognorm.cdf(x, s=sigma, loc=0, scale=np.exp(mu)))
    resultado = kstest(datos, cdf_mezcla)
    print(f"\n === Test K-S: {nombre} vs mezcla Gamma-Lognormal ===")

    print("w =", round(w, 4))

    print("Gamma:")
    print("forma =", round(a, 4))
    print("escala =", round(scale_gamma, 4))

    print("Lognormal:")
    print("mu =", round(mu, 4))
    print("sigma =", round(sigma, 4))

    print("D       =", round(resultado.statistic, 4))
    print("p-value =", resultado.pvalue)

    if resultado.pvalue < 0.05:
        print("  => Se RECHAZA la hipótesis del ajuste " "Gamma-Lognormal")
    else:
        print("  => NO se puede rechazar la hipótesis del ajuste " "Gamma-Lognormal")