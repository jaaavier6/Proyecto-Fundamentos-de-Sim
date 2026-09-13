import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2


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
plt.show()

#ahora veremos como se comporta el numero de llegadas por perfil

conteos_dia_perfil = (
    llegadas
    .groupby(["day_id", "profile"])
    .size()
    .unstack(fill_value=0)
)

print(conteos_dia_perfil.head(40))

#comprobaremos con chi- cuadrado si el conteo por periodo es poisson 

from scipy.stats import chi2

print("\nTEST DE DISPERSIÓN PARA POISSON")

for perfil in perfiles:
    datos = conteos_dia_perfil[perfil]

    n = len(datos)
    media = datos.mean()
    varianza = datos.var(ddof=1)

    estadistico = (n - 1) * varianza / media

    p_inferior = chi2.cdf(estadistico, df=n-1)
    p_superior = 1 - chi2.cdf(estadistico, df=n-1)
    p_value = 2 * min(p_inferior, p_superior)

    print(f"\n{perfil}")
    print(f"Media = {media:.3f}")
    print(f"Varianza = {varianza:.3f}")
    print(f"Var/Media = {varianza/media:.3f}")
    print(f"Estadístico = {estadistico:.3f}")
    print(f"p-value = {p_value:.4f}")

    if p_value < 0.05:
        print("=> Se RECHAZA la hipótesis de dispersión Poisson.")
    else:
        print("=> NO se rechaza la hipótesis de dispersión Poisson.")



