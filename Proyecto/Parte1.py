import pandas as pd
import numpy as np
import simpy
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, gamma, poisson, weibull_min
import matplotlib.pyplot as plt
from tests import chi2_dos_muestras, aplicar_test_kruskal_wallis, ajuste_ks_gamma, ajuste_ks_lognormal, ajuste_ks_weibull

#se leen los archivos y se agrega el separador junto con el decimal para "adaptar" los datos al lenguaje de py, ya que venían con el decimal "," por defecto
log_operacional = pd.read_csv("log_operacional_historico.csv", sep=";", decimal = ",", low_memory=False)
log_reparaciones = pd.read_csv("log_reparaciones_historico.csv", sep=";", decimal = ",", low_memory=False)



##################### PARTE 1a ##########################
#revisar que los datos estén "limpios", hacer revisión general
print("-------------- LOG OPERACIONAL ------------------")

print("------DIMENSIONES-----")
print(log_operacional.shape)

print("------DUPLICADOS-----")
print(log_operacional.duplicated().sum())

print("----- DIAS-----")
print(log_operacional["day_id"].nunique()) #cuantos dias diferentes hay registrados
print(log_operacional["day_id"].unique()) #lista con estos dias

print("------TIEMPOS NEGATIVOS-----")
print((log_operacional["event_time"] < 0 ).sum())

print("----- TIPOS DE EVENTOS ------")
print(log_operacional["event_type"].value_counts())

print("se ve que hay 41 datos que son evento_mal_escrito")
#considerar qué hacer con ellos

print("----- PERFILES ------")
print(log_operacional["profile"].value_counts(dropna=False))

print("----- RUTINAS ------")
print(log_operacional["routine"].value_counts(dropna=False))

print("----- RESULTADOS ------")
print(log_operacional["outcome"].value_counts())

print("----- VALORES FALTANTES ------")
print(log_operacional.isna().sum())

print("------ ID EVENTOS REPETIDOS EN MISMO DIA-------")
print(log_operacional.duplicated(subset=["day_id", "event_id"]).sum())

print("------ HORARIOS VALIDOS -----")
visitas = log_operacional[log_operacional["event_type"] == "visit"]

print("Visitas después de las 21:00:", (visitas["event_time"] > 840).sum())

print("----- REVISION CIERRE 22:00 HRS -------- ")
registros_cierre = log_operacional[(log_operacional["event_type"] == "registration") & (log_operacional["event_time"] >= 900)]

print("Registros iniciados desde las 22:00:",len(registros_cierre))

ejercicios_cierre = log_operacional[(log_operacional["event_type"] == "exercise")
    & (log_operacional["outcome"].isin(["completed", "completed_failed"])) & (log_operacional["event_time"] >= 900)]

print("Ejercicios efectivos iniciados desde las 22:00:",len(ejercicios_cierre))


cardio_cierre = log_operacional[(log_operacional["event_type"] == "cardio")
    & (log_operacional["outcome"].isin(["completed", "completed_failed"])) & (log_operacional["event_time"] >= 900)]

print("Sesiones de cardio iniciadas desde las 22:00:", len(cardio_cierre))

asistencias_cierre = log_operacional[(log_operacional["event_type"] == "assistance") & (log_operacional["event_time"] >= 900)]

print("Asistencias iniciadas desde las 22:00:", len(asistencias_cierre))

reposiciones_cierre = log_operacional[(log_operacional["event_type"] == "replenishment") & (log_operacional["event_time"] >= 900)]

print("Reposiciones iniciadas desde las 22:00:", len(reposiciones_cierre))

print("------ CELDAS FUERA DE RANGO ------")

origen_numerico = pd.to_numeric(log_operacional["origin"],errors="coerce")

destino_numerico = pd.to_numeric(log_operacional["destination"],errors="coerce")

origen_fuera_rango = (origen_numerico.notna() & ((origen_numerico < 1) | (origen_numerico > 49)))

destino_fuera_rango = (destino_numerico.notna() & ((destino_numerico < 1) | (destino_numerico > 49)))

print("Origen fuera de rango:",origen_fuera_rango.sum())

print("Destino fuera de rango:",destino_fuera_rango.sum())


print("------ CELDAS VALORES ENTEROS ------")

origen_no_entero = (origen_numerico.notna() & (origen_numerico % 1 != 0))

destino_no_entero = (destino_numerico.notna() & (destino_numerico % 1 != 0))

print("Origen no entero:", origen_no_entero.sum())

print("Destino no entero:", destino_no_entero.sum())


print("------ REVISAR QUE PERFIL NO CAMBIE EN UNA MISMA VISITA ---------")
usuarios = log_operacional[log_operacional["user_id"].notna()].copy()

perfiles_por_visita = (usuarios.groupby(["day_id", "user_id"])["profile"].nunique())

print("Visitas con más de un perfil:",(perfiles_por_visita > 1).sum())

print("------ REVISAR QUE RUTINA NO CAMBIE EN UNA MISMA VISITA ---------")
rutinas_por_visita = (usuarios.groupby(["day_id", "user_id"])["routine"].nunique())

print("Visitas con más de una rutina:",(rutinas_por_visita > 1).sum())

print("----- DURACIONES IMPOSIBLES -----")
print("Duraciones negativas:",(log_operacional["duration_min"] < 0).sum())

print("Esperas negativas:",(log_operacional["wait_min"] < 0).sum())

print("----- USO DE RECURSOS IMPOSIBLES -----")
print("Agua negativa:", (log_operacional["water_liters"] < 0).sum())

print("Toallas negativas:", (log_operacional["towel_count"] < 0).sum())


#limpiar el log operacional y solucionar problemas

log_operacional_limpio = log_operacional.copy()

#eliminar los eventos erroneos
log_operacional_limpio = log_operacional_limpio[log_operacional_limpio["event_type"] != "evento_mal_escrito"].copy()

print("-------- CORREGIR RESULTADO DESCONOCIDO -------")


filtro = ((log_operacional_limpio["event_type"] == "supply_pickup")
    & (log_operacional_limpio["outcome"] == "resultado_desconocido"))

print("Supply pickup corregidos:", filtro.sum())

log_operacional_limpio.loc[filtro, "outcome"] = "completed"


filtro = ((log_operacional_limpio["event_type"] == "assistance")
    & (log_operacional_limpio["outcome"] == "resultado_desconocido"))

print("Assistance corregidos:", filtro.sum())

log_operacional_limpio.loc[filtro, "outcome"] = "arrived"


filtro = ((log_operacional_limpio["event_type"] == "stockout")
    & (log_operacional_limpio["outcome"] == "resultado_desconocido"))

print("Stockout corregidos:", filtro.sum())

log_operacional_limpio.loc[filtro, "outcome"] = "empty"

log_operacional_limpio = log_operacional_limpio[
    log_operacional_limpio["outcome"] != "resultado_desconocido"].copy()


conteo_perfiles = (log_operacional_limpio[log_operacional_limpio["user_id"].notna()
        & log_operacional_limpio["profile"].notna()]
    .groupby(["day_id", "user_id", "profile"]).size().reset_index(name="cantidad"))

#ordenar para que el mas frecuente ese dia quede primero
conteo_perfiles = conteo_perfiles.sort_values(by=["day_id", "user_id", "cantidad"],ascending=[True, True, False])

perfil_correcto = conteo_perfiles.drop_duplicates(subset=["day_id", "user_id"]).copy()
perfil_correcto = perfil_correcto[["day_id", "user_id", "profile"]]
perfil_correcto = perfil_correcto.rename(columns={"profile": "profile_correcto"})

#agregao la columna con el perfil correcto para luego poder buscar las que no coinciden y modificarla
log_operacional_limpio = log_operacional_limpio.merge(perfil_correcto, on=["day_id", "user_id"], how="left")

filtro_perfiles = (log_operacional_limpio["profile"].notna()
    & log_operacional_limpio["profile_correcto"].notna()
    & (log_operacional_limpio["profile"] != log_operacional_limpio["profile_correcto"]))

#corregir
log_operacional_limpio.loc[filtro_perfiles, "profile"] = log_operacional_limpio.loc[filtro_perfiles, "profile_correcto"]

log_operacional_limpio = log_operacional_limpio.drop(columns=["profile_correcto"])

# limpiar celdas destino fuera de rango

log_operacional_limpio["destination"] = pd.to_numeric(log_operacional_limpio["destination"],errors="coerce")

log_operacional_limpio = log_operacional_limpio[(log_operacional_limpio["destination"].isna()) | 
    ((log_operacional_limpio["destination"] >= 1) & (log_operacional_limpio["destination"] <= 49))].copy()


print("---------------------------------------------------")
print("-------------- LOG REPARACIONES ------------------")

print("------DUPLICADOS-----")
print(log_reparaciones.duplicated().sum())

print("----- TIPOS DE DIAS ------")
print(log_reparaciones["historical_day"].value_counts())

print("----- INSTANTE DE FALLA INVALIDO ------")
print((log_reparaciones["failure_time"] < 0).sum())

print("----- DURACIONES FALTANTES ------")
print(log_reparaciones["repair_duration_min"].isna().sum())

print("----- DURACIONES NEGATIVAS ------")
print((log_reparaciones["repair_duration_min"] < 0 ).sum())

print("----- TIPOS DE MAQUINAS ------")
print(log_reparaciones["machine_type"].value_counts())


print("------ CELDAS FUERA DE RANGO ------")

celda_numerico = pd.to_numeric(log_reparaciones["cell"],errors="coerce")

celda_fuera_rango = (celda_numerico.notna() & ((celda_numerico < 1) | (celda_numerico > 49)))

print("Celda fuera de rango:",celda_fuera_rango.sum())


log_reparaciones_limpio = log_reparaciones.copy()


#eliminar los tiempos de reparacion negativos
log_reparaciones_limpio = log_reparaciones_limpio[log_reparaciones_limpio["repair_duration_min"] >= 0].copy()

print("------ TIPO DE MAQUINA ERRONEO ------")
#primero busco el registro
print(log_reparaciones[log_reparaciones["machine_type"] == "registro_erroneo"])
#como veo que es lat_pulldown-02 puedo reemplazar machine_type por lat_pulldown

filtro = log_reparaciones_limpio["machine_type"] == "registro_erroneo"
log_reparaciones_limpio.loc[filtro, "machine_type"] = "lat_pulldown"

print("------ CELDA FUERA DE RANGO ------")

print(log_reparaciones[(log_reparaciones["cell"] < 1) | (log_reparaciones["cell"] > 49)])

print(log_reparaciones_limpio[
    log_reparaciones_limpio["unit_id"] == "shoulder_press-01"]["cell"].value_counts())

filtro_celda = ((log_reparaciones_limpio["unit_id"] == "shoulder_press-01")
    & (log_reparaciones_limpio["cell"] == 99))
log_reparaciones_limpio.loc[filtro_celda, "cell"] = 49


log_operacional_limpio.to_csv("log_operacional_limpio.csv", sep=";", decimal=",", index=False)


print("------------------- PREGUNTA 1A ----------------------------")


##RUTINAS##
rutinas = log_operacional_limpio[log_operacional_limpio["event_type"] == "visit"].copy()
#print(rutinas["routine"].value_counts())
#reviso que no hayan visitas repetidas, ya que debo considerar solo una observación por visita
print("rutinas repetidas:",rutinas.duplicated(subset=["day_id", "user_id"]).sum())

print("rutinas:", len(rutinas))



#duracion efectiva de fuerza completados
fuerza = log_operacional_limpio[(log_operacional_limpio["event_type"] == "exercise")
    & (log_operacional_limpio["outcome"].isin(["completed", "completed_failed"]))].copy()

print("Ejercicios:", len(fuerza))
print("Duraciones faltantes:",fuerza["duration_min"].isna().sum())

#como hay datos de duraciones faltantes, se excluyen para el análisis
datos_fuerza = fuerza[fuerza["duration_min"].notna()].copy()



#duracion efectiva sesiones de cardio
cardio = log_operacional_limpio[(log_operacional_limpio["event_type"] == "cardio")
    & (log_operacional_limpio["outcome"].isin(["completed", "completed_failed"]))].copy()

print(" datos cardio:", len(cardio))
print("Duraciones faltantes:",cardio["duration_min"].isna().sum())


#tiempo de reparacion
reparacion = log_reparaciones_limpio.copy()

print("datos reparaciones:", len(reparacion))
print("reparaciones faltantes:",reparacion["repair_duration_min"].isna().sum())

"""
print("------------- DATOS RUTINAS -------------")
print(rutinas["routine"].describe())

frec_rutina = rutinas["routine"].value_counts()

plt.bar(frec_rutina.index, frec_rutina.values)
plt.xlabel("Tipo de rutina")
plt.ylabel("Cantidad de visitas")
plt.title("Distribución del tipo de rutina")

plt.show()

print("------------- DATOS DURACIÓN EFECTIVA EJERCICIOS FUERZA -------------")
print(datos_fuerza["duration_min"].describe())

print("Asimetría duracion ejercicios fuerza: ", datos_fuerza["duration_min"].skew())

plt.hist(datos_fuerza["duration_min"], bins=30, edgecolor="black")
plt.xlabel("Duración (minutos)")
plt.ylabel("Frecuencia")
plt.title("Duración efectiva de ejercicios de fuerza")
plt.show()

plt.boxplot(datos_fuerza["duration_min"], vert=False)
plt.xlabel("Duración (min)")
plt.title("Boxplot duración ejercicios de fuerza")
plt.show()


print("------------- DATOS DURACIÓN EFECTIVA RUTINAS CARDIO -------------")
print(cardio["duration_min"].describe())

print("Asimetría duracion ejercicios cardio: ", cardio["duration_min"].skew())

plt.hist(cardio["duration_min"], bins=30, edgecolor="black")
plt.xlabel("Duración (minutos)")
plt.ylabel("Frecuencia")
plt.title("Duración efectiva de rutinas de cardio")
plt.show()

plt.boxplot(cardio["duration_min"], vert=False)
plt.xlabel("Duración (min)")
plt.title("Boxplot duración rutinas de cardio")
plt.show()


print("------------- DATOS TIEMPO DE REPARACIÓN DE MÁQUINAS -------------")
print(reparacion["repair_duration_min"].describe())

print("Asimetría tiempo de reparación: ", reparacion["repair_duration_min"].skew())

plt.hist(reparacion["repair_duration_min"], bins=30, edgecolor="black")
plt.xlabel("Duración (minutos)")
plt.ylabel("Frecuencia")
plt.title("Tiempo de reparación de máquinas")
plt.show()

plt.boxplot(reparacion["repair_duration_min"], vert=False)
plt.xlabel("Duración (min)")
plt.title("Boxplot duración rutinas de cardio")
plt.show()


#graficos juntos
fig, ax = plt.subplots(2, 2, figsize=(12, 8))

# Gráfico de barras de rutinas
frecuencias_rutina = (
    rutinas["routine"]
    .value_counts()
    .reindex()
)

ax[0, 0].bar(
    frecuencias_rutina.index,
    frecuencias_rutina.values
)

ax[0, 0].set_title("Distribución del tipo de rutina")
ax[0, 0].set_xlabel("Rutina")
ax[0, 0].set_ylabel("Frecuencia")


# Histograma fuerza
ax[0, 1].hist(
    datos_fuerza["duration_min"],
    bins=30,
    edgecolor="black"
)

ax[0, 1].set_title("Duración ejercicios de fuerza")
ax[0, 1].set_xlabel("Duración (min)")
ax[0, 1].set_ylabel("Frecuencia")


# Histograma cardio
ax[1, 0].hist(
    cardio["duration_min"],
    bins=30,
    edgecolor="black"
)

ax[1, 0].set_title("Duración sesiones de cardio")
ax[1, 0].set_xlabel("Duración (min)")
ax[1, 0].set_ylabel("Frecuencia")


# Histograma reparaciones
ax[1, 1].hist(
    reparacion["repair_duration_min"],
    bins=30,
    edgecolor="black"
)

ax[1, 1].set_title("Tiempo de reparación")
ax[1, 1].set_xlabel("Duración (min)")
ax[1, 1].set_ylabel("Frecuencia")


plt.tight_layout()
plt.show()



#boxplots
fig, ax = plt.subplots(1, 3, figsize=(13, 4))

# Fuerza
ax[0].boxplot(
    datos_fuerza["duration_min"]
)

ax[0].set_title("Ejercicios de fuerza")
ax[0].set_ylabel("Duración (min)")


# Cardio
ax[1].boxplot(
    cardio["duration_min"]
)

ax[1].set_title("Sesiones de cardio")
ax[1].set_ylabel("Duración (min)")


# Reparaciones
ax[2].boxplot(
    reparacion["repair_duration_min"]
)

ax[2].set_title("Reparaciones")
ax[2].set_ylabel("Duración (min)")


plt.tight_layout()
plt.show()
"""


#separar muestras para comparar RUTINAS
orden = ["push", "pull", "legs", "upper", "full_body"]

standard = rutinas[rutinas["profile"] == "standard"]["routine"].values
express = rutinas[rutinas["profile"] == "express"]["routine"].values
intenso = rutinas[rutinas["profile"] == "intense"]["routine"].values
flexible = rutinas[rutinas["profile"] == "flexible"]["routine"].values

print("------------------------- TEST CHI2 PARA RUTINAS ------------------------------")

chi2_dos_muestras(standard, express, ["standard", "express"], orden)
chi2_dos_muestras(standard, intenso, ["standard", "intenso"], orden)
chi2_dos_muestras(standard, flexible, ["standard", "flexible"], orden)
chi2_dos_muestras(express, flexible, ["express", "flexible"], orden)
chi2_dos_muestras(express, intenso, ["express", "intenso"], orden)
chi2_dos_muestras(flexible, intenso, ["flexible", "intenso"], orden)

#como no es necesario separar entre standard y express, creo la muestra conjunta de ambas

standard_express = rutinas[rutinas["profile"].isin(["standard", "express"])]["routine"].values

#separar muestras para comparar FUERZA

fuerza_standard = datos_fuerza[datos_fuerza["profile"] == "standard"]["duration_min"].values
fuerza_express = datos_fuerza[datos_fuerza["profile"] == "express"]["duration_min"].values
fuerza_intenso = datos_fuerza[datos_fuerza["profile"] == "intense"]["duration_min"].values
fuerza_flexible = datos_fuerza[datos_fuerza["profile"] == "flexible"]["duration_min"].values

print("------------------------- TEST KW PARA FUERZA ------------------------------")
#aplicamos kw
aplicar_test_kruskal_wallis([fuerza_standard, fuerza_express], ["standard", "express"])
aplicar_test_kruskal_wallis([fuerza_standard, fuerza_intenso], ["standard", "intenso"])
aplicar_test_kruskal_wallis([fuerza_standard, fuerza_flexible], ["standard", "flexible"])
aplicar_test_kruskal_wallis([fuerza_express, fuerza_flexible], ["express", "flexible"])
aplicar_test_kruskal_wallis([fuerza_express, fuerza_intenso], ["express", "intenso"])
aplicar_test_kruskal_wallis([fuerza_flexible, fuerza_intenso], ["flexible", "intenso"])


#separar muestras para comparar CARDIO

cardio_standard = cardio[cardio["profile"] == "standard"]["duration_min"].values
cardio_express = cardio[cardio["profile"] == "express"]["duration_min"].values
cardio_intenso = cardio[cardio["profile"] == "intense"]["duration_min"].values
cardio_flexible = cardio[cardio["profile"] == "flexible"]["duration_min"].values

print("------------------------- TEST KW PARA CARDIO ------------------------------")
#aplicamos kw
aplicar_test_kruskal_wallis([cardio_standard, cardio_express], ["standard", "express"])
aplicar_test_kruskal_wallis([cardio_standard, cardio_express], ["standard", "express"])
aplicar_test_kruskal_wallis([cardio_standard, cardio_intenso], ["standard", "intenso"])
aplicar_test_kruskal_wallis([cardio_standard, cardio_flexible], ["standard", "flexible"])
aplicar_test_kruskal_wallis([cardio_express, cardio_flexible], ["express", "flexible"])
aplicar_test_kruskal_wallis([cardio_express, cardio_intenso], ["express", "intenso"])
aplicar_test_kruskal_wallis([cardio_flexible, cardio_intenso], ["flexible", "intenso"])



#separar muestras para comparar CARDIO

reparacion_shoulder_press = reparacion[reparacion["machine_type"] == "shoulder_press"]["repair_duration_min"].values
reparacion_chest_press = reparacion[reparacion["machine_type"] == "chest_press"]["repair_duration_min"].values
reparacion_lat_pulldown = reparacion[reparacion["machine_type"] == "lat_pulldown"]["repair_duration_min"].values
reparacion_seated_row = reparacion[reparacion["machine_type"] == "seated_row"]["repair_duration_min"].values
reparacion_leg_extension = reparacion[reparacion["machine_type"] == "leg_extension"]["repair_duration_min"].values
reparacion_cable = reparacion[reparacion["machine_type"] == "cable"]["repair_duration_min"].values
reparacion_leg_curl = reparacion[reparacion["machine_type"] == "leg_curl"]["repair_duration_min"].values
reparacion_leg_press = reparacion[reparacion["machine_type"] == "leg_press"]["repair_duration_min"].values
reparacion_biceps_curl = reparacion[reparacion["machine_type"] == "biceps_curl"]["repair_duration_min"].values
reparacion_chest_fly = reparacion[reparacion["machine_type"] == "chest_fly"]["repair_duration_min"].values
reparacion_treadmill = reparacion[reparacion["machine_type"] == "treadmill"]["repair_duration_min"].values


print("------------------------- TEST KW PARA REPARACION ------------------------------")
#aplicamos kw
#probar con todas
aplicar_test_kruskal_wallis([reparacion_shoulder_press, reparacion_chest_press, reparacion_lat_pulldown, reparacion_seated_row, 
    reparacion_leg_extension, reparacion_cable, reparacion_leg_curl, reparacion_leg_press, reparacion_biceps_curl, reparacion_chest_fly,
    reparacion_treadmill], ["shoulder_press", "chest_press", "lat_pulldown", "seated_row", "leg_extension", "cable",
        "leg_curl", "leg_press", "biceps_curl", "chest_fly", "treadmill"])

#probar por categorias
print("---------- REPARACION EMPUJE ------------")
aplicar_test_kruskal_wallis([reparacion_shoulder_press, reparacion_chest_press, reparacion_chest_fly], ["shoulder_press", "chest_press", "chest_fly"])

print("---------- REPARACION JALON ------------")
aplicar_test_kruskal_wallis([reparacion_lat_pulldown, reparacion_seated_row, reparacion_biceps_curl], ["lat_pulldown", "seated_row", "biceps_curl"])

print("---------- REPARACION PIERNAS ------------")
aplicar_test_kruskal_wallis([reparacion_leg_press, reparacion_leg_curl, reparacion_leg_extension], ["leg_press", "leg_curl", "leg_extension"])


reparacion_empuje = reparacion[reparacion["machine_type"].isin(["shoulder_press", "chest_press", "chest_fly"])]["repair_duration_min"].values
reparacion_jalon = reparacion[reparacion["machine_type"].isin(["lat_pulldown", "seated_row", "biceps_curl"])]["repair_duration_min"].values
reparacion_piernas = reparacion[reparacion["machine_type"].isin(["leg_press", "leg_curl", "leg_extension"])]["repair_duration_min"].values

aplicar_test_kruskal_wallis([reparacion_piernas, reparacion_treadmill], ["piernas", "correr"])
aplicar_test_kruskal_wallis([reparacion_jalon, reparacion_empuje], ["jalon", "empuje"])
aplicar_test_kruskal_wallis([reparacion_jalon, reparacion_cable], ["jalon", "cable"])


print("----------------- PREGUNTA 1B --------------------")
print("----------------- RUTINAS --------------------")

totales_standard_express = len(standard_express)
prob_push_se = (standard_express == "push").sum() / totales_standard_express
prob_pull_se = (standard_express == "pull").sum() / totales_standard_express
prob_legs_se = (standard_express == "legs").sum() / totales_standard_express
prob_upper_se = (standard_express == "upper").sum() / totales_standard_express
prob_full_body_se = (standard_express == "full_body").sum() / totales_standard_express

totales_intenso = len(intenso)
prob_push_i = (intenso == "push").sum() / totales_intenso
prob_pull_i = (intenso == "pull").sum() / totales_intenso
prob_legs_i = (intenso == "legs").sum() / totales_intenso
prob_upper_i = (intenso == "upper").sum() / totales_intenso
prob_full_body_i = (intenso == "full_body").sum() / totales_intenso



totales_flexible = len(flexible)
prob_push_f = (flexible == "push").sum() / totales_flexible
prob_pull_f = (flexible == "pull").sum() / totales_flexible
prob_legs_f = (flexible == "legs").sum() / totales_flexible
prob_upper_f = (flexible == "upper").sum() / totales_flexible
prob_full_body_f = (flexible == "full_body").sum() / totales_flexible

print("----------------- PROBABILIDADES STANDARD EXPRESS --------------------")
print("push= ", prob_push_se)
print("pull= ", prob_pull_se)
print("legs= ", prob_legs_se)
print("upper= ", prob_upper_se)
print("full body= ", prob_full_body_se)

print("----------------- PROBABILIDADES INTENSO --------------------")
print("push= ", prob_push_i)
print("pull= ", prob_pull_i)
print("legs= ", prob_legs_i)
print("upper= ", prob_upper_i)
print("full body= ", prob_full_body_i)

print("----------------- PROBABILIDADES FLEXIBLE--------------------")
print("push= ", prob_push_f)
print("pull= ", prob_pull_f)
print("legs= ", prob_legs_f)
print("upper= ", prob_upper_f)
print("full body= ", prob_full_body_f)



print("-------------- ESTIMACIONES PARA VARIABLES CONTINUAS ----------")
print("------------------- FUERZA ----------------------")

#gamma 
a_gamma_standard_f, loc_gamma_standard_f, scale_gamma_standard_f = gamma.fit(fuerza_standard, floc=0)
a_gamma_express_f, loc_gamma_express_f, scale_gamma_express_f = gamma.fit(fuerza_express, floc=0)
a_gamma_intenso_f, loc_gamma_intenso_f, scale_gamma_intenso_f = gamma.fit(fuerza_intenso, floc=0)
a_gamma_flexible_f, loc_gamma_flexible_f, scale_gamma_flexible_f = gamma.fit(fuerza_flexible, floc=0)

#lognormal
sigma_lognormal_standard_f, loc_lognormal_standard_f, scale_lognormal_standard_f = lognorm.fit(fuerza_standard, floc=0)
mu_log_standard_f = np.log(scale_lognormal_standard_f)

sigma_lognormal_express_f, loc_lognormal_express_f, scale_lognormal_express_f = lognorm.fit(fuerza_express, floc=0)
mu_log_express_f = np.log(scale_lognormal_express_f)

sigma_lognormal_intenso_f, loc_lognormal_intenso_f, scale_lognormal_intenso_f = lognorm.fit(fuerza_intenso, floc=0)
mu_log_intenso_f = np.log(scale_lognormal_intenso_f)

sigma_lognormal_flexible_f, loc_lognormal_flexible_f, scale_lognormal_flexible_f = lognorm.fit(fuerza_flexible, floc=0)
mu_log_flexible_f = np.log(scale_lognormal_flexible_f)

#weibull
forma_weibull_standard_f, loc_weibull_standard_f, scale_weibull_standard_f = weibull_min.fit(fuerza_standard, floc=0)
forma_weibull_express_f, loc_weibull_express_f, scale_weibull_express_f = weibull_min.fit(fuerza_express, floc=0)
forma_weibull_intenso_f, loc_weibull_intenso_f, scale_weibull_intenso_f = weibull_min.fit(fuerza_intenso, floc=0)
forma_weibull_flexible_f, loc_weibull_flexible_f, scale_weibull_flexible_f = weibull_min.fit(fuerza_flexible, floc=0)


print("----- ESTIMACIONES STANDARD -----")
print("GAMMA")
print("forma= ", a_gamma_standard_f)
print("scale= ", scale_gamma_standard_f)

print("LOGNORMAL")
print("mu= ", mu_log_standard_f)
print("sigma= ", sigma_lognormal_standard_f)

print("WEIBULL")
print("forma= ", forma_weibull_standard_f)
print("scale= ", scale_weibull_standard_f)


print("----- ESTIMACIONES EXPRESS -----")
print("GAMMA")
print("forma= ", a_gamma_express_f)
print("scale= ", scale_gamma_express_f)

print("LOGNORMAL")
print("mu= ", mu_log_express_f)
print("sigma= ", sigma_lognormal_express_f)

print("WEIBULL")
print("forma= ", forma_weibull_express_f)
print("scale= ", scale_weibull_express_f)


print("----- ESTIMACIONES INTENSO -----")
print("GAMMA")
print("forma= ", a_gamma_intenso_f)
print("scale= ", scale_gamma_intenso_f)

print("LOGNORMAL")
print("mu= ", mu_log_intenso_f)
print("sigma= ", sigma_lognormal_intenso_f)

print("WEIBULL")
print("forma= ", forma_weibull_intenso_f)
print("scale= ", scale_weibull_intenso_f)


print("----- ESTIMACIONES FLEXIBLE -----")
print("GAMMA")
print("forma= ", a_gamma_flexible_f)
print("scale= ", scale_gamma_flexible_f)

print("LOGNORMAL")
print("mu= ", mu_log_flexible_f)
print("sigma= ", sigma_lognormal_flexible_f)

print("WEIBULL")
print("forma= ", forma_weibull_flexible_f)
print("scale= ", scale_weibull_flexible_f)



print("--------------------- CARDIO -------------------------")
#gamma 
a_gamma_standard_c, loc_gamma_standard_c, scale_gamma_standard_c = gamma.fit(cardio_standard, floc=0)
a_gamma_express_c, loc_gamma_express_c, scale_gamma_express_c = gamma.fit(cardio_express, floc=0)
a_gamma_intenso_c, loc_gamma_intenso_c, scale_gamma_intenso_c = gamma.fit(cardio_intenso, floc=0)
a_gamma_flexible_c, loc_gamma_flexible_c, scale_gamma_flexible_c = gamma.fit(cardio_flexible, floc=0)

#lognormal
sigma_lognormal_standard_c, loc_lognormal_standard_c, scale_lognormal_standard_c = lognorm.fit(cardio_standard, floc=0)
mu_log_standard_c = np.log(scale_lognormal_standard_c)

sigma_lognormal_express_c, loc_lognormal_express_c, scale_lognormal_express_c = lognorm.fit(cardio_express, floc=0)
mu_log_express_c = np.log(scale_lognormal_express_c)

sigma_lognormal_intenso_c, loc_lognormal_intenso_c, scale_lognormal_intenso_c = lognorm.fit(cardio_intenso, floc=0)
mu_log_intenso_c = np.log(scale_lognormal_intenso_c)

sigma_lognormal_flexible_c, loc_lognormal_flexible_c, scale_lognormal_flexible_c = lognorm.fit(cardio_flexible, floc=0)
mu_log_flexible_c = np.log(scale_lognormal_flexible_c)

#weibull
forma_weibull_standard_c, loc_weibull_standard_c, scale_weibull_standard_c = weibull_min.fit(cardio_standard, floc=0)
forma_weibull_express_c, loc_weibull_express_c, scale_weibull_express_c = weibull_min.fit(cardio_express, floc=0)
forma_weibull_intenso_c, loc_weibull_intenso_c, scale_weibull_intenso_c = weibull_min.fit(cardio_intenso, floc=0)
forma_weibull_flexible_c, loc_weibull_flexible_c, scale_weibull_flexible_c = weibull_min.fit(cardio_flexible, floc=0)


print("----- ESTIMACIONES STANDARD -----")
print("GAMMA")
print("forma= ", a_gamma_standard_c)
print("scale= ", scale_gamma_standard_c)

print("LOGNORMAL")
print("mu= ", mu_log_standard_c)
print("sigma= ", sigma_lognormal_standard_c)

print("WEIBULL")
print("forma= ", forma_weibull_standard_c)
print("scale= ", scale_weibull_standard_c)


print("----- ESTIMACIONES EXPRESS -----")
print("GAMMA")
print("forma= ", a_gamma_express_c)
print("scale= ", scale_gamma_express_c)

print("LOGNORMAL")
print("mu= ", mu_log_express_c)
print("sigma= ", sigma_lognormal_express_c)

print("WEIBULL")
print("forma= ", forma_weibull_express_c)
print("scale= ", scale_weibull_express_c)


print("----- ESTIMACIONES INTENSO -----")
print("GAMMA")
print("forma= ", a_gamma_intenso_c)
print("scale= ", scale_gamma_intenso_c)

print("LOGNORMAL")
print("mu= ", mu_log_intenso_c)
print("sigma= ", sigma_lognormal_intenso_c)

print("WEIBULL")
print("forma= ", forma_weibull_intenso_c)
print("scale= ", scale_weibull_intenso_c)


print("----- ESTIMACIONES FLEXIBLE -----")
print("GAMMA")
print("forma= ", a_gamma_flexible_c)
print("scale= ", scale_gamma_flexible_c)

print("LOGNORMAL")
print("mu= ", mu_log_flexible_c)
print("sigma= ", sigma_lognormal_flexible_c)

print("WEIBULL")
print("forma= ", forma_weibull_flexible_c)
print("scale= ", scale_weibull_flexible_c)


print("----------------------------- REPARACION ------------------------------")

#gamma 
a_gamma_empuje, loc_gamma_empuje, scale_gamma_empuje = gamma.fit(reparacion_empuje, floc=0)
a_gamma_jalon, loc_gamma_jalon, scale_gamma_jalon = gamma.fit(reparacion_jalon, floc=0)
a_gamma_piernas, loc_gamma_piernas, scale_gamma_piernas = gamma.fit(reparacion_piernas, floc=0)
a_gamma_treadmill, loc_gamma_treadmill, scale_gamma_treadmill = gamma.fit(reparacion_treadmill, floc=0)
a_gamma_cable, loc_gamma_cable, scale_gamma_cable = gamma.fit(reparacion_cable, floc=0)


#lognormal
sigma_lognormal_empuje, loc_lognormal_empuje, scale_lognormal_empuje = lognorm.fit(reparacion_empuje, floc=0)
mu_log_empuje = np.log(scale_lognormal_empuje)

sigma_lognormal_jalon, loc_lognormal_jalon, scale_lognormal_jalon = lognorm.fit(reparacion_jalon, floc=0)
mu_log_jalon = np.log(scale_lognormal_jalon)

sigma_lognormal_piernas, loc_lognormal_piernas, scale_lognormal_piernas = lognorm.fit(reparacion_piernas, floc=0)
mu_log_piernas = np.log(scale_lognormal_piernas)

sigma_lognormal_treadmill, loc_lognormal_treadmill, scale_lognormal_treadmill = lognorm.fit(reparacion_treadmill, floc=0)
mu_log_treadmill = np.log(scale_lognormal_treadmill)

sigma_lognormal_cable, loc_lognormal_cable, scale_lognormal_cable = lognorm.fit(reparacion_cable, floc=0)
mu_log_cable = np.log(scale_lognormal_cable)

#weibull
forma_weibull_empuje, loc_weibull_empuje, scale_weibull_empuje = weibull_min.fit(reparacion_empuje, floc=0)
forma_weibull_jalon, loc_weibull_jalon, scale_weibull_jalon = weibull_min.fit(reparacion_jalon, floc=0)
forma_weibull_piernas, loc_weibull_piernas, scale_weibull_piernas = weibull_min.fit(reparacion_piernas, floc=0)
forma_weibull_treadmill, loc_weibull_treadmill, scale_weibull_treadmill = weibull_min.fit(reparacion_treadmill, floc=0)
forma_weibull_cable, loc_weibull_cable, scale_weibull_cable = weibull_min.fit(reparacion_cable, floc=0)


print("----- ESTIMACIONES EMPUJE -----")
print("GAMMA")
print("forma= ", a_gamma_empuje)
print("scale= ", scale_gamma_empuje)

print("LOGNORMAL")
print("mu= ", mu_log_empuje)
print("sigma= ", sigma_lognormal_empuje)

print("WEIBULL")
print("forma= ", forma_weibull_empuje)
print("scale= ", scale_weibull_empuje)



print("----- ESTIMACIONES JALON -----")
print("GAMMA")
print("forma= ", a_gamma_jalon)
print("scale= ", scale_gamma_jalon)

print("LOGNORMAL")
print("mu= ", mu_log_jalon)
print("sigma= ", sigma_lognormal_jalon)

print("WEIBULL")
print("forma= ", forma_weibull_jalon)
print("scale= ", scale_weibull_jalon)



print("----- ESTIMACIONES PIERNAS -----")
print("GAMMA")
print("forma= ", a_gamma_piernas)
print("scale= ", scale_gamma_piernas)

print("LOGNORMAL")
print("mu= ", mu_log_piernas)
print("sigma= ", sigma_lognormal_piernas)

print("WEIBULL")
print("forma= ", forma_weibull_piernas)
print("scale= ", scale_weibull_piernas)


print("----- ESTIMACIONES TROTADORA -----")
print("GAMMA")
print("forma= ", a_gamma_treadmill)
print("scale= ", scale_gamma_treadmill)

print("LOGNORMAL")
print("mu= ", mu_log_treadmill)
print("sigma= ", sigma_lognormal_treadmill)

print("WEIBULL")
print("forma= ", forma_weibull_treadmill)
print("scale= ", scale_weibull_treadmill)



print("----- ESTIMACIONES MULTIFUNCIONAL -----")
print("GAMMA")
print("forma= ", a_gamma_cable)
print("scale= ", scale_gamma_cable)

print("LOGNORMAL")
print("mu= ", mu_log_cable)
print("sigma= ", sigma_lognormal_cable)

print("WEIBULL")
print("forma= ", forma_weibull_cable)
print("scale= ", scale_weibull_cable)


print("----------------- PREGUNTA 1C ---------------------------")
print("-------------------- FUERZA ------------------------------")
ajuste_ks_gamma(fuerza_standard, "Fuerza Standard")
ajuste_ks_lognormal(fuerza_standard, "Fuerza Standard")
ajuste_ks_weibull(fuerza_standard, "Fuerza Standard")

ajuste_ks_gamma(fuerza_express, "Fuerza Express")
ajuste_ks_lognormal(fuerza_express, "Fuerza Express")
ajuste_ks_weibull(fuerza_express, "Fuerza Express")

ajuste_ks_gamma(fuerza_intenso, "Fuerza Intenso")
ajuste_ks_lognormal(fuerza_intenso, "Fuerza Intenso")
ajuste_ks_weibull(fuerza_intenso, "Fuerza Intenso")

ajuste_ks_gamma(fuerza_flexible, "Fuerza Flexible")
ajuste_ks_lognormal(fuerza_flexible, "Fuerza Flexible")
ajuste_ks_weibull(fuerza_flexible, "Fuerza Flexible")

print("-------------------- CARDIO ------------------------------")

ajuste_ks_gamma(cardio_standard, "Cardio Standard")
ajuste_ks_lognormal(cardio_standard, "Cardio Standard")
ajuste_ks_weibull(cardio_standard, "Cardio Standard")

ajuste_ks_gamma(cardio_express, "Cardio Express")
ajuste_ks_lognormal(cardio_express, "Cardio Express")
ajuste_ks_weibull(cardio_express, "Cardio Express")

ajuste_ks_gamma(cardio_intenso, "Cardio Intenso")
ajuste_ks_lognormal(cardio_intenso, "Cardio Intenso")
ajuste_ks_weibull(cardio_intenso, "Cardio Intenso")

ajuste_ks_gamma(cardio_flexible, "Cardio Flexible")
ajuste_ks_lognormal(cardio_flexible, "Cardio Flexible")
ajuste_ks_weibull(cardio_flexible, "Cardio Flexible")


print("-------------------- REPARACION ------------------------------")

ajuste_ks_gamma(reparacion_empuje, "Reparación Empuje")
ajuste_ks_lognormal(reparacion_empuje, "Reparación Empuje")
ajuste_ks_weibull(reparacion_empuje, "Reparación Empuje")

ajuste_ks_gamma(reparacion_jalon, "Reparación Jalón")
ajuste_ks_lognormal(reparacion_jalon, "Reparación Jalón")
ajuste_ks_weibull(reparacion_jalon, "Reparación Jalón")

ajuste_ks_gamma(reparacion_piernas, "Reparación Piernas")
ajuste_ks_lognormal(reparacion_piernas, "Reparación Piernas")
ajuste_ks_weibull(reparacion_piernas, "Reparación Piernas")

ajuste_ks_gamma(reparacion_treadmill, "Reparación Trotadora")
ajuste_ks_lognormal(reparacion_treadmill, "Reparación Trotadora")
ajuste_ks_weibull(reparacion_treadmill, "Reparación Trotadora")

ajuste_ks_gamma(reparacion_cable, "Reparación Multifuncional")
ajuste_ks_lognormal(reparacion_cable, "Reparación Multifuncional")
ajuste_ks_weibull(reparacion_cable, "Reparación Multifuncional")

