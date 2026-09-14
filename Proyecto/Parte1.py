import pandas as pd
import numpy as np
import simpy
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, gamma, poisson
import matplotlib.pyplot as plt


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


##RUTINAS##
#rutinas = log_operacional[log_operacional["event_type"] == "visit"].copy()
#print(rutinas["routine"].value_counts())




