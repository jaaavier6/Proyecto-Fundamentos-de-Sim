import pandas as pd
import numpy as np
import simpy
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, gamma, poisson, weibull_min, fisk
import matplotlib.pyplot as plt
from tests import chi2_dos_muestras, aplicar_test_kruskal_wallis, ajuste_ks_gamma, ajuste_ks_lognormal, ajuste_ks_weibull, ajuste_ks_loglogistica
from tests import parametros_gamma_lognormal, parametros_gamma_gamma, ajuste_ks_gamma_gamma, ajuste_ks_gamma_lognormal


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
print(log_reparaciones_limpio[log_reparaciones_limpio["unit_id"] == "shoulder_press-01"]["cell"].value_counts())

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
frecuencias_rutina = (rutinas["routine"].value_counts().reindex())
ax[0, 0].bar(frecuencias_rutina.index,frecuencias_rutina.values)
ax[0, 0].set_title("Distribución del tipo de rutina")
ax[0, 0].set_xlabel("Rutina")
ax[0, 0].set_ylabel("Frecuencia")

# Histograma fuerza
ax[0, 1].hist(datos_fuerza["duration_min"],bins=30,edgecolor="black")
ax[0, 1].set_title("Duración ejercicios de fuerza")
ax[0, 1].set_xlabel("Duración (min)")
ax[0, 1].set_ylabel("Frecuencia")

# Histograma cardio
ax[1, 0].hist(cardio["duration_min"],bins=30,edgecolor="black")
ax[1, 0].set_title("Duración sesiones de cardio")
ax[1, 0].set_xlabel("Duración (min)")
ax[1, 0].set_ylabel("Frecuencia")

# Histograma reparaciones
ax[1, 1].hist(reparacion["repair_duration_min"],bins=30,edgecolor="black")
ax[1, 1].set_title("Tiempo de reparación")
ax[1, 1].set_xlabel("Duración (min)")
ax[1, 1].set_ylabel("Frecuencia")

plt.tight_layout()
plt.show()

#boxplots
fig, ax = plt.subplots(1, 3, figsize=(13, 4))
# Fuerza
ax[0].boxplot(datos_fuerza["duration_min"])
ax[0].set_title("Ejercicios de fuerza")
ax[0].set_ylabel("Duración (min)")

# Cardio
ax[1].boxplot(cardio["duration_min"])
ax[1].set_title("Sesiones de cardio")
ax[1].set_ylabel("Duración (min)")

# Reparaciones
ax[2].boxplot(reparacion["repair_duration_min"])
ax[2].set_title("Reparaciones")
ax[2].set_ylabel("Duración (min)")

plt.tight_layout()
plt.show()

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


print("--------------- SOLUCIONAR PROBLEMAS CON FUERZA Y CARDIO STANDARD Y REPARACION EMPUJE ------")

print("--- FUERZA STANDARD ----")

fuerza_standard_df = datos_fuerza[datos_fuerza["profile"] == "standard"].copy()

standard_shoulder_press = fuerza_standard_df[fuerza_standard_df["resource"] == "shoulder_press"]["duration_min"].values
standard_chest_press = fuerza_standard_df[fuerza_standard_df["resource"] == "chest_press"]["duration_min"].values
standard_chest_fly = fuerza_standard_df[fuerza_standard_df["resource"] == "chest_fly"]["duration_min"].values
standard_lat_pulldown = fuerza_standard_df[fuerza_standard_df["resource"] == "lat_pulldown"]["duration_min"].values
standard_seated_row = fuerza_standard_df[fuerza_standard_df["resource"] == "seated_row"]["duration_min"].values
standard_biceps_curl = fuerza_standard_df[fuerza_standard_df["resource"] == "biceps_curl"]["duration_min"].values
standard_leg_press = fuerza_standard_df[fuerza_standard_df["resource"] == "leg_press"]["duration_min"].values
standard_leg_curl = fuerza_standard_df[fuerza_standard_df["resource"] == "leg_curl"]["duration_min"].values
standard_leg_extension = fuerza_standard_df[fuerza_standard_df["resource"] == "leg_extension"]["duration_min"].values
standard_cable = fuerza_standard_df[fuerza_standard_df["resource"] == "cable"]["duration_min"].values

print("------ESTIMACIÓN FUERZA STANDARD POR RESOURCE ------")

# Gamma
a_gamma_shoulder_press_f, loc_gamma_shoulder_press_f, scale_gamma_shoulder_press_f = gamma.fit(standard_shoulder_press, floc=0)
a_gamma_chest_press_f, loc_gamma_chest_press_f, scale_gamma_chest_press_f = gamma.fit(standard_chest_press, floc=0)
a_gamma_chest_fly_f, loc_gamma_chest_fly_f, scale_gamma_chest_fly_f = gamma.fit(standard_chest_fly, floc=0)
a_gamma_lat_pulldown_f, loc_gamma_lat_pulldown_f, scale_gamma_lat_pulldown_f = gamma.fit(standard_lat_pulldown, floc=0)
a_gamma_seated_row_f, loc_gamma_seated_row_f, scale_gamma_seated_row_f = gamma.fit(standard_seated_row, floc=0)
a_gamma_biceps_curl_f, loc_gamma_biceps_curl_f, scale_gamma_biceps_curl_f = gamma.fit(standard_biceps_curl, floc=0)
a_gamma_leg_press_f, loc_gamma_leg_press_f, scale_gamma_leg_press_f = gamma.fit(standard_leg_press, floc=0)
a_gamma_leg_curl_f, loc_gamma_leg_curl_f, scale_gamma_leg_curl_f = gamma.fit(standard_leg_curl, floc=0)
a_gamma_leg_extension_f, loc_gamma_leg_extension_f, scale_gamma_leg_extension_f = gamma.fit(standard_leg_extension, floc=0)
a_gamma_cable_f, loc_gamma_cable_f, scale_gamma_cable_f = gamma.fit(standard_cable, floc=0)

# Lognormal
sigma_lognormal_shoulder_press_f, loc_lognormal_shoulder_press_f, scale_lognormal_shoulder_press_f = lognorm.fit(standard_shoulder_press, floc=0)
mu_log_shoulder_press_f = np.log(scale_lognormal_shoulder_press_f)

sigma_lognormal_chest_press_f, loc_lognormal_chest_press_f, scale_lognormal_chest_press_f = lognorm.fit(standard_chest_press, floc=0)
mu_log_chest_press_f = np.log(scale_lognormal_chest_press_f)

sigma_lognormal_chest_fly_f, loc_lognormal_chest_fly_f, scale_lognormal_chest_fly_f = lognorm.fit(standard_chest_fly, floc=0)
mu_log_chest_fly_f = np.log(scale_lognormal_chest_fly_f)

sigma_lognormal_lat_pulldown_f, loc_lognormal_lat_pulldown_f, scale_lognormal_lat_pulldown_f = lognorm.fit(standard_lat_pulldown, floc=0)
mu_log_lat_pulldown_f = np.log(scale_lognormal_lat_pulldown_f)

sigma_lognormal_seated_row_f, loc_lognormal_seated_row_f, scale_lognormal_seated_row_f = lognorm.fit(standard_seated_row, floc=0)
mu_log_seated_row_f = np.log(scale_lognormal_seated_row_f)

sigma_lognormal_biceps_curl_f, loc_lognormal_biceps_curl_f, scale_lognormal_biceps_curl_f = lognorm.fit(standard_biceps_curl, floc=0)
mu_log_biceps_curl_f = np.log(scale_lognormal_biceps_curl_f)

sigma_lognormal_leg_press_f, loc_lognormal_leg_press_f, scale_lognormal_leg_press_f = lognorm.fit(standard_leg_press, floc=0)
mu_log_leg_press_f = np.log(scale_lognormal_leg_press_f)

sigma_lognormal_leg_curl_f, loc_lognormal_leg_curl_f, scale_lognormal_leg_curl_f = lognorm.fit(standard_leg_curl, floc=0)
mu_log_leg_curl_f = np.log(scale_lognormal_leg_curl_f)

sigma_lognormal_leg_extension_f, loc_lognormal_leg_extension_f, scale_lognormal_leg_extension_f = lognorm.fit(standard_leg_extension, floc=0)
mu_log_leg_extension_f = np.log(scale_lognormal_leg_extension_f)

sigma_lognormal_cable_f, loc_lognormal_cable_f, scale_lognormal_cable_f = lognorm.fit(standard_cable, floc=0)
mu_log_cable_f = np.log(scale_lognormal_cable_f)

# Weibull
forma_weibull_shoulder_press_f, loc_weibull_shoulder_press_f, scale_weibull_shoulder_press_f = weibull_min.fit(standard_shoulder_press, floc=0)
forma_weibull_chest_press_f, loc_weibull_chest_press_f, scale_weibull_chest_press_f = weibull_min.fit(standard_chest_press, floc=0)
forma_weibull_chest_fly_f, loc_weibull_chest_fly_f, scale_weibull_chest_fly_f = weibull_min.fit(standard_chest_fly, floc=0)
forma_weibull_lat_pulldown_f, loc_weibull_lat_pulldown_f, scale_weibull_lat_pulldown_f = weibull_min.fit(standard_lat_pulldown, floc=0)
forma_weibull_seated_row_f, loc_weibull_seated_row_f, scale_weibull_seated_row_f = weibull_min.fit(standard_seated_row, floc=0)
forma_weibull_biceps_curl_f, loc_weibull_biceps_curl_f, scale_weibull_biceps_curl_f = weibull_min.fit(standard_biceps_curl, floc=0)
forma_weibull_leg_press_f, loc_weibull_leg_press_f, scale_weibull_leg_press_f = weibull_min.fit(standard_leg_press, floc=0)
forma_weibull_leg_curl_f, loc_weibull_leg_curl_f, scale_weibull_leg_curl_f = weibull_min.fit(standard_leg_curl, floc=0)
forma_weibull_leg_extension_f, loc_weibull_leg_extension_f, scale_weibull_leg_extension_f = weibull_min.fit(standard_leg_extension, floc=0)
forma_weibull_cable_f, loc_weibull_cable_f, scale_weibull_cable_f = weibull_min.fit(standard_cable, floc=0)

print("----- ESTIMACIONES SHOULDER PRESS -----")
print("GAMMA")
print("forma= ", a_gamma_shoulder_press_f)
print("scale= ", scale_gamma_shoulder_press_f)
print("LOGNORMAL")
print("mu= ", mu_log_shoulder_press_f)
print("sigma= ", sigma_lognormal_shoulder_press_f)
print("WEIBULL")
print("forma= ", forma_weibull_shoulder_press_f)
print("scale= ", scale_weibull_shoulder_press_f)

print("----- ESTIMACIONES CHEST PRESS -----")
print("GAMMA")
print("forma= ", a_gamma_chest_press_f)
print("scale= ", scale_gamma_chest_press_f)
print("LOGNORMAL")
print("mu= ", mu_log_chest_press_f)
print("sigma= ", sigma_lognormal_chest_press_f)
print("WEIBULL")
print("forma= ", forma_weibull_chest_press_f)
print("scale= ", scale_weibull_chest_press_f)

print("----- ESTIMACIONES CHEST FLY -----")
print("GAMMA")
print("forma= ", a_gamma_chest_fly_f)
print("scale= ", scale_gamma_chest_fly_f)
print("LOGNORMAL")
print("mu= ", mu_log_chest_fly_f)
print("sigma= ", sigma_lognormal_chest_fly_f)
print("WEIBULL")
print("forma= ", forma_weibull_chest_fly_f)
print("scale= ", scale_weibull_chest_fly_f)

print("----- ESTIMACIONES LAT PULLDOWN -----")
print("GAMMA")
print("forma= ", a_gamma_lat_pulldown_f)
print("scale= ", scale_gamma_lat_pulldown_f)
print("LOGNORMAL")
print("mu= ", mu_log_lat_pulldown_f)
print("sigma= ", sigma_lognormal_lat_pulldown_f)
print("WEIBULL")
print("forma= ", forma_weibull_lat_pulldown_f)
print("scale= ", scale_weibull_lat_pulldown_f)

print("----- ESTIMACIONES SEATED ROW -----")
print("GAMMA")
print("forma= ", a_gamma_seated_row_f)
print("scale= ", scale_gamma_seated_row_f)
print("LOGNORMAL")
print("mu= ", mu_log_seated_row_f)
print("sigma= ", sigma_lognormal_seated_row_f)
print("WEIBULL")
print("forma= ", forma_weibull_seated_row_f)
print("scale= ", scale_weibull_seated_row_f)

print("----- ESTIMACIONES BICEPS CURL -----")
print("GAMMA")
print("forma= ", a_gamma_biceps_curl_f)
print("scale= ", scale_gamma_biceps_curl_f)
print("LOGNORMAL")
print("mu= ", mu_log_biceps_curl_f)
print("sigma= ", sigma_lognormal_biceps_curl_f)
print("WEIBULL")
print("forma= ", forma_weibull_biceps_curl_f)
print("scale= ", scale_weibull_biceps_curl_f)

print("----- ESTIMACIONES LEG PRESS -----")
print("GAMMA")
print("forma= ", a_gamma_leg_press_f)
print("scale= ", scale_gamma_leg_press_f)
print("LOGNORMAL")
print("mu= ", mu_log_leg_press_f)
print("sigma= ", sigma_lognormal_leg_press_f)
print("WEIBULL")
print("forma= ", forma_weibull_leg_press_f)
print("scale= ", scale_weibull_leg_press_f)

print("----- ESTIMACIONES LEG CURL -----")
print("GAMMA")
print("forma= ", a_gamma_leg_curl_f)
print("scale= ", scale_gamma_leg_curl_f)
print("LOGNORMAL")
print("mu= ", mu_log_leg_curl_f)
print("sigma= ", sigma_lognormal_leg_curl_f)
print("WEIBULL")
print("forma= ", forma_weibull_leg_curl_f)
print("scale= ", scale_weibull_leg_curl_f)

print("----- ESTIMACIONES LEG EXTENSION -----")
print("GAMMA")
print("forma= ", a_gamma_leg_extension_f)
print("scale= ", scale_gamma_leg_extension_f)
print("LOGNORMAL")
print("mu= ", mu_log_leg_extension_f)
print("sigma= ", sigma_lognormal_leg_extension_f)
print("WEIBULL")
print("forma= ", forma_weibull_leg_extension_f)
print("scale= ", scale_weibull_leg_extension_f)

print("----- ESTIMACIONES CABLE -----")
print("GAMMA")
print("forma= ", a_gamma_cable_f)
print("scale= ", scale_gamma_cable_f)
print("LOGNORMAL")
print("mu= ", mu_log_cable_f)
print("sigma= ", sigma_lognormal_cable_f)
print("WEIBULL")
print("forma= ", forma_weibull_cable_f)
print("scale= ", scale_weibull_cable_f)

print("\n------ AJUSTES FUERZA STANDARD POR RESOURCE ------")

print("\n----- SHOULDER PRESS -----")
ajuste_ks_gamma(standard_shoulder_press,"Fuerza Standard Shoulder Press")
ajuste_ks_lognormal(standard_shoulder_press,"Fuerza Standard Shoulder Press")
ajuste_ks_weibull(standard_shoulder_press,"Fuerza Standard Shoulder Press")

print("\n----- CHEST PRESS -----")
ajuste_ks_gamma(standard_chest_press,"Fuerza Standard Chest Press")
ajuste_ks_lognormal(standard_chest_press,"Fuerza Standard Chest Press")
ajuste_ks_weibull(standard_chest_press,"Fuerza Standard Chest Press")

print("\n----- CHEST FLY -----")
ajuste_ks_gamma(standard_chest_fly,"Fuerza Standard Chest Fly")
ajuste_ks_lognormal(standard_chest_fly,"Fuerza Standard Chest Fly")
ajuste_ks_weibull(standard_chest_fly,"Fuerza Standard Chest Fly")

print("\n----- LAT PULLDOWN -----")
ajuste_ks_gamma(standard_lat_pulldown,"Fuerza Standard Lat Pulldown")
ajuste_ks_lognormal(standard_lat_pulldown,"Fuerza Standard Lat Pulldown")
ajuste_ks_weibull(standard_lat_pulldown,"Fuerza Standard Lat Pulldown")

print("\n----- SEATED ROW -----")
ajuste_ks_gamma(standard_seated_row,"Fuerza Standard Seated Row")
ajuste_ks_lognormal(standard_seated_row,"Fuerza Standard Seated Row")
ajuste_ks_weibull(standard_seated_row,"Fuerza Standard Seated Row")

print("\n----- BICEPS CURL -----")
ajuste_ks_gamma(standard_biceps_curl,"Fuerza Standard Biceps Curl")
ajuste_ks_lognormal(standard_biceps_curl,"Fuerza Standard Biceps Curl")
ajuste_ks_weibull(standard_biceps_curl,"Fuerza Standard Biceps Curl")

print("\n----- LEG PRESS -----")
ajuste_ks_gamma(standard_leg_press,"Fuerza Standard Leg Press")
ajuste_ks_lognormal(standard_leg_press,"Fuerza Standard Leg Press")
ajuste_ks_weibull(standard_leg_press,"Fuerza Standard Leg Press")

print("\n----- LEG CURL -----")
ajuste_ks_gamma(standard_leg_curl,"Fuerza Standard Leg Curl")
ajuste_ks_lognormal(standard_leg_curl,"Fuerza Standard Leg Curl")
ajuste_ks_weibull(standard_leg_curl,"Fuerza Standard Leg Curl")

print("\n----- LEG EXTENSION -----")
ajuste_ks_gamma(standard_leg_extension,"Fuerza Standard Leg Extension")
ajuste_ks_lognormal(standard_leg_extension,"Fuerza Standard Leg Extension")
ajuste_ks_weibull(standard_leg_extension,"Fuerza Standard Leg Extension")

print("\n----- CABLE -----")
ajuste_ks_gamma(standard_cable,"Fuerza Standard Cable")
ajuste_ks_lognormal(standard_cable,"Fuerza Standard Cable")
ajuste_ks_weibull(standard_cable,"Fuerza Standard Cable")

print("--- CARDIO STANDARD ----")
plt.hist(cardio_standard, bins=40, edgecolor="black")
plt.xlabel("Duración (minutos)")
plt.ylabel("Frecuencia")
plt.title("Duración sesiones de cardio - Standard")
plt.show()

c_loglog_cardio_standard, loc_loglog_cardio_standard, scale_loglog_cardio_standard = fisk.fit(cardio_standard,floc=0)

print("----- LOG-LOGISTICA CARDIO STANDARD -----")
print("forma= ", c_loglog_cardio_standard)
print("scale= ", scale_loglog_cardio_standard)

w_gl, a_gl, scale_gamma_gl, mu_gl, sigma_gl = parametros_gamma_lognormal(cardio_standard)

print("\n----- CARDIO STANDARD: GAMMA-LOGNORMAL -----")
print("w =", round(w_gl, 4))

print("Gamma:")
print("forma =", round(a_gl, 4))
print("escala =", round(scale_gamma_gl, 4))

print("Lognormal:")
print("mu =", round(mu_gl, 4))
print("sigma =", round(sigma_gl, 4))

w_gg, a1_gg, scale1_gg, a2_gg, scale2_gg = parametros_gamma_gamma(cardio_standard)
print("\n----- CARDIO STANDARD: GAMMA-GAMMA -----")
print("w =", round(w_gg, 4))

print("Gamma 1:")
print("forma =", round(a1_gg, 4))
print("escala =", round(scale1_gg, 4))

print("Gamma 2:")
print("forma =", round(a2_gg, 4))
print("escala =", round(scale2_gg, 4))

ajuste_ks_loglogistica(cardio_standard,"Cardio Standard")
ajuste_ks_gamma_lognormal(cardio_standard, w_gl, a_gl, scale_gamma_gl, mu_gl, sigma_gl, "Cardio Standard")
ajuste_ks_gamma_gamma(cardio_standard, w_gg, a1_gg, scale1_gg, a2_gg, scale2_gg, "Cardio Standard")

print("------- REPARACION EMPUJE ------")

print("\n----- LOG-LOGISTICA REPARACION EMPUJE -----")
forma_loglog_reparacion_empuje, loc_loglog_reparacion_empuje, scale_loglog_reparacion_empuje = fisk.fit(reparacion_empuje, floc=0)
print("forma =", round(forma_loglog_reparacion_empuje, 4))
print("scale =", round(scale_loglog_reparacion_empuje, 4))

print("\n----- REPARACION EMPUJE: GAMMA-LOGNORMAL -----")
w_gl_rep, a_gl_rep, scale_gamma_gl_rep, mu_gl_rep, sigma_gl_rep = parametros_gamma_lognormal(reparacion_empuje)
print("w =", round(w_gl_rep, 4))
print("Gamma:")
print("forma =", round(a_gl_rep, 4))
print("escala =", round(scale_gamma_gl_rep, 4))

print("Lognormal:")
print("mu =", round(mu_gl_rep, 4))
print("sigma =", round(sigma_gl_rep, 4))

print("\n----- REPARACION EMPUJE: GAMMA-GAMMA -----")
w_gg_rep, a1_gg_rep, scale1_gg_rep, a2_gg_rep, scale2_gg_rep = parametros_gamma_gamma(reparacion_empuje)

print("w =", round(w_gg_rep, 4))

print("Gamma 1:")
print("forma =", round(a1_gg_rep, 4))
print("escala =", round(scale1_gg_rep, 4))

print("Gamma 2:")
print("forma =", round(a2_gg_rep, 4))
print("escala =", round(scale2_gg_rep, 4))

print("\n------ AJUSTES REPARACION EMPUJE ------")

ajuste_ks_loglogistica(reparacion_empuje, "Reparacion Empuje")
ajuste_ks_gamma_lognormal(reparacion_empuje, w_gl_rep, a_gl_rep, scale_gamma_gl_rep, mu_gl_rep, sigma_gl_rep, "Reparacion Empuje")
ajuste_ks_gamma_gamma(reparacion_empuje, w_gg_rep, a1_gg_rep, scale1_gg_rep, a2_gg_rep, scale2_gg_rep, "Reparacion Empuje")

def graficar_histogramas(submuestras, titulo_general, bins=30, ncols=3):
    nombres = list(submuestras.keys())
    cantidad = len(nombres)
    nrows = int(np.ceil(cantidad / ncols))
    fig, axes = plt.subplots(nrows,ncols,figsize=(15, 4 * nrows))
    axes = np.array(axes).reshape(-1)
    for i, nombre in enumerate(nombres):
        datos = submuestras[nombre]
        axes[i].hist(datos,bins=bins,edgecolor="black")
        axes[i].set_title(nombre,fontsize=11,pad=10)
        axes[i].set_xlabel("Duración (min)",fontsize=9)
        axes[i].set_ylabel("Frecuencia",fontsize=9)
    # Apagar gráficos sobrantes
    for j in range(i + 1, len(axes)):
        axes[j].axis("off")
    fig.suptitle(titulo_general,fontsize=16,y=0.995)
    plt.subplots_adjust(top=0.95,bottom=0.06,hspace=0.65,wspace=0.20)
    plt.show()

submuestras_fuerza_perfiles = {"Fuerza Express": fuerza_express,
    "Fuerza Intense": fuerza_intenso,
    "Fuerza Flexible": fuerza_flexible}

fig, axes = plt.subplots(1,3,figsize=(15, 4),constrained_layout=True)

for ax, (nombre, datos) in zip(axes,submuestras_fuerza_perfiles.items()):
    ax.hist(datos,bins=30,edgecolor="black")
    ax.set_title(nombre)
    ax.set_xlabel("Duración (min)")
    ax.set_ylabel("Frecuencia")

fig.suptitle("Histogramas de Fuerza por perfil",fontsize=16)
plt.show()

submuestras_fuerza_standard = {
    "Shoulder press": standard_shoulder_press,
    "Chest press": standard_chest_press,
    "Chest fly": standard_chest_fly,
    "Lat pulldown": standard_lat_pulldown,
    "Seated row": standard_seated_row,
    "Biceps curl": standard_biceps_curl,
    "Leg press": standard_leg_press,
    "Leg curl": standard_leg_curl,
    "Leg extension": standard_leg_extension,
    "Cable": standard_cable
}
fig, axes = plt.subplots(5,2,figsize=(12, 18),constrained_layout=True)

axes = axes.flatten()

for ax, (nombre, datos) in zip(axes,
    submuestras_fuerza_standard.items()):
    ax.hist(datos,bins=30,edgecolor="black")
    ax.set_title(nombre, fontsize=11)
    ax.set_xlabel("Duración (min)")
    ax.set_ylabel("Frecuencia")

fig.suptitle("Histogramas de Fuerza Standard por tipo de máquina",fontsize=16)
plt.show()


submuestras_cardio = {"Cardio Standard": cardio_standard,
    "Cardio Express": cardio_express,
    "Cardio Intense": cardio_intenso,
    "Cardio Flexible": cardio_flexible}

submuestras_reparacion = {"Reparacion Empuje": reparacion_empuje,
    "Reparacion Jalon": reparacion_jalon,
    "Reparacion Piernas": reparacion_piernas,
    "Reparacion Trotadora": reparacion_treadmill,
    "Reparacion Multifuncional": reparacion_cable}

graficar_histogramas(submuestras_cardio, "Histogramas submuestras de Cardio", bins=30, ncols=2)
graficar_histogramas(submuestras_reparacion, "Histogramas submuestras de Reparacion", bins=30, ncols=3)


def densidad_modelo(x, modelo, parametros):
    if modelo == "gamma":
        a = parametros["forma"]
        escala = parametros["escala"]
        return gamma.pdf(x, a=a, loc=0, scale=escala)
    elif modelo == "lognormal":
        mu = parametros["mu"]
        sigma = parametros["sigma"]
        return lognorm.pdf(x, s=sigma, loc=0, scale=np.exp(mu))
    elif modelo == "weibull":
        forma = parametros["forma"]
        escala = parametros["escala"]
        return weibull_min.pdf(x, c=forma, loc=0, scale=escala)
    elif modelo == "gamma_gamma":
        w = parametros["w"]
        a1 = parametros["forma1"]
        escala1 = parametros["escala1"]
        a2 = parametros["forma2"]
        escala2 = parametros["escala2"]
        return (
            w * gamma.pdf(x, a=a1, loc=0, scale=escala1)
            + (1 - w) * gamma.pdf(x, a=a2, loc=0, scale=escala2))
    else:
        raise ValueError("Modelo no reconocido")

def graficar_histograma_con_ajuste(datos, nombre, modelo, parametros, bins=30):
    plt.figure(figsize=(7, 5))
    plt.hist(datos, bins=bins, density=True, edgecolor="black", alpha=0.7)
    x = np.linspace(min(datos), max(datos), 500)
    y = densidad_modelo(x, modelo, parametros)
    plt.plot(x, y, linewidth=2)
    plt.title(nombre)
    plt.xlabel("Duración (min)")
    plt.ylabel("Densidad")
    plt.tight_layout()
    plt.show()


modelos_finales = {"Fuerza Express": {"datos": fuerza_express,"modelo": "gamma","parametros": {"forma": 40.4363, "escala": 0.1085}},
    "Fuerza Intense": {"datos": fuerza_intenso,"modelo": "gamma","parametros": {"forma": 12.1920, "escala": 0.9141}},
    "Fuerza Flexible": {"datos": fuerza_flexible,"modelo": "gamma","parametros": {"forma": 12.1337, "escala": 0.6358}},
    
    "Standard Shoulder press": {"datos": standard_shoulder_press,"modelo": "gamma","parametros": {"forma": 16.8451, "escala": 0.4732}},
    "Standard Chest press": {"datos": standard_chest_press,"modelo": "gamma","parametros": {"forma": 16.1063, "escala": 0.4942}},
    "Standard Chest fly": {"datos": standard_chest_fly,"modelo": "gamma","parametros": {"forma": 17.3148, "escala": 0.3430}},
    "Standard Lat pulldown": {"datos": standard_lat_pulldown,"modelo": "gamma","parametros": {"forma": 15.6070, "escala": 0.5102}},
    "Standard Seated row": {"datos": standard_seated_row,"modelo": "gamma","parametros": {"forma": 16.3765, "escala": 0.4882}},
    "Standard Biceps curl": {"datos": standard_biceps_curl,"modelo": "gamma","parametros": {"forma": 16.3935, "escala": 0.3684}},
    "Standard Leg press": {"datos": standard_leg_press,"modelo": "gamma","parametros": {"forma": 14.9705, "escala": 0.6690}},
    "Standard Leg curl": {"datos": standard_leg_curl,"modelo": "lognormal","parametros": {"mu": 1.9151, "sigma": 0.2450}},
    "Standard Leg extension": {"datos": standard_leg_extension,"modelo": "gamma","parametros": {"forma": 16.6796, "escala": 0.4247}},
    "Standard Cable": {"datos": standard_cable,"modelo": "gamma","parametros": {"forma": 16.1428, "escala": 0.4918}},
    
    "Cardio Standard": {"datos": cardio_standard,"modelo": "gamma_gamma","parametros": {"w": 0.7272,"forma1": 11.7240,"escala1": 1.3271,"forma2": 42.4354,"escala2": 0.5509}},
    "Cardio Express": {"datos": cardio_express,"modelo": "weibull","parametros": {"forma": 8.8668, "escala": 9.4151}},
    "Cardio Intense": {"datos": cardio_intenso,"modelo": "gamma","parametros": {"forma": 7.7515, "escala": 3.4589}},
    "Cardio Flexible": {"datos": cardio_flexible,"modelo": "gamma","parametros": {"forma": 10.6295, "escala": 1.5095}},

    "Reparacion Empuje": {"datos": reparacion_empuje,"modelo": "gamma_gamma","parametros": {"w": 0.6998,"forma1": 12.1780,"escala1": 1.2545,"forma2": 22.6476,"escala2": 1.5179}},
    "Reparacion Jalon": {"datos": reparacion_jalon,"modelo": "gamma","parametros": {"forma": 6.5050, "escala": 3.3583}},
    "Reparacion Piernas": {"datos": reparacion_piernas,"modelo": "gamma","parametros": {"forma": 7.7546, "escala": 3.9459}},
    "Reparacion Trotadora": {"datos": reparacion_treadmill,"modelo": "weibull","parametros": {"forma": 3.6772, "escala": 38.7781}},
    "Reparacion Multifuncional": {"datos": reparacion_cable,"modelo": "lognormal","parametros": {"mu": 3.1127, "sigma": 0.3832}}
    }


for nombre, info in modelos_finales.items():
    graficar_histograma_con_ajuste(datos=info["datos"],nombre=nombre,modelo=info["modelo"],parametros=info["parametros"],bins=30)