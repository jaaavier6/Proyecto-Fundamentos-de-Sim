import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as st
from scipy.stats import mannwhitneyu

alpha = 0.05
replicas = 300

#cargar datos
datos_reales = pd.read_csv("validar_gimnasio.csv", sep=";", decimal=",")
datos_reales.columns = datos_reales.columns.str.strip()

datos_simulados = pd.read_csv("indicadores_300_replicas.csv", sep=";", decimal=",")
datos_simulados.columns = datos_simulados.columns.str.strip()

llegadas_reales = datos_reales["arrivals"].to_numpy()
llegadas_simuladas = datos_simulados["numero_llegadas"].to_numpy()

tasa_rechazo_real = datos_reales["rejection_rate"].to_numpy()
tasa_rechazo_simulada = datos_simulados["tasa_rechazo"].to_numpy()

ocupacion_promedio_real = datos_reales["mean_occupancy"].to_numpy()
ocupacion_promedio_simulada = datos_simulados["ocupacion_promedio"].to_numpy()

prop_cap_maxima_real = datos_reales["proportion_at_capacity"].to_numpy()
prop_cap_maxima_simulada = datos_simulados["proporcion_capacidad_maxima"].to_numpy()

espera_total_promedio_real = datos_reales["mean_total_wait"].to_numpy()
espera_total_promedio_simulada = datos_simulados["espera_total_promedio"].to_numpy()

perc_90_espera_total_real = datos_reales["p90_total_wait"].to_numpy()
perc_90_espera_total_simulada = datos_simulados["percentil_90_espera_total"].to_numpy()

espera_total_promedio_19_21_real = datos_reales["mean_total_wait_block_5"].to_numpy()
espera_total_promedio_19_21_simulada = datos_simulados["espera_total_promedio_19_21"].to_numpy()

tasa_finalizacion_rutinas_real = datos_reales["routine_completion_rate"].to_numpy()
tasa_finalizacion_rutinas_simulada = datos_simulados["tasa_finalizacion_rutinas"].to_numpy()

tasa_finalizacion_rutinas_express_real = datos_reales["routine_completion_rate_express"].to_numpy()
tasa_finalizacion_rutinas_express_simulada = datos_simulados["tasa_finalizacion_rutinas_express"].to_numpy()

insatisfaccion_promedio_real = datos_reales["mean_dissatisfaction"].to_numpy()
insatisfaccion_promedio_simulada = datos_simulados["insatisfaccion_promedio_admitidos"].to_numpy()

utilizacion_operacional_trotadoras_real = datos_reales["operational_utilization_treadmill"].to_numpy()
utilizacion_operacional_trotadoras_simulada = datos_simulados["utilizacion_operacional_trotadoras"].to_numpy()

utilizacion_operacional_aperturas_pecho_real = datos_reales["operational_utilization_chest_fly"].to_numpy()
utilizacion_operacional_aperturas_pecho_simulada = datos_simulados["utilizacion_operacional_aperturas_pecho"].to_numpy()

cola_promedio_aperturas_pecho_real = datos_reales["mean_queue_length_chest_fly"].to_numpy()
cola_promedio_aperturas_pecho_simulada = datos_simulados["cola_promedio_aperturas_pecho"].to_numpy()

cola_promedio_remo_sentado_real = datos_reales["mean_queue_length_seated_row"].to_numpy()
cola_promedio_remo_sentado_simulada = datos_simulados["cola_promedio_remo_sentado"].to_numpy()

utilizacion_entrenadores_real = datos_reales["trainer_utilization"].to_numpy()
utilizacion_entrenadores_simulada = datos_simulados["utilizacion_entrenadores"].to_numpy()

duracion_quiebres_agua_real = datos_reales["water_stockout_duration"].to_numpy()
duracion_quiebres_agua_simulada = datos_simulados["duracion_quiebres_agua"].to_numpy()

duracion_quiebres_toallas_real = datos_reales["towel_stockout_duration"].to_numpy()
duracion_quiebres_toallas_simulada = datos_simulados["duracion_quiebres_toallas"].to_numpy()

numero_fallas_maquinas_real = datos_reales["machine_failures"].to_numpy()
numero_fallas_maquinas_simulada = datos_simulados["numero_fallas_maquinas"].to_numpy()

espera_promedio_reparacion_real = datos_reales["mean_repair_wait"].to_numpy()
espera_promedio_reparacion_simulada = datos_simulados["espera_promedio_reparacion"].to_numpy()

minutos_operacion_post_cierre_real = datos_reales["post_close_operation_minutes"].to_numpy()
minutos_operacion_post_cierre_simulada = datos_simulados["minutos_operacion_postcierre"].to_numpy()

#histogramas 

bins_llegadas = np.histogram_bin_edges(np.concatenate((llegadas_reales, llegadas_simuladas)),bins=15)
bins_tasa_rechazo = np.histogram_bin_edges(np.concatenate((tasa_rechazo_real, tasa_rechazo_simulada)),bins=15)
bins_ocupacion_promedio = np.histogram_bin_edges(np.concatenate((ocupacion_promedio_real, ocupacion_promedio_simulada)),bins=15)
bins_proporcion_cap_max = np.histogram_bin_edges(np.concatenate((prop_cap_maxima_real, prop_cap_maxima_simulada)),bins=15)
bins_espera_total_promedio = np.histogram_bin_edges(np.concatenate((espera_total_promedio_real, espera_total_promedio_simulada)),bins=15)
bins_p90_espera_total_promedio = np.histogram_bin_edges(np.concatenate((perc_90_espera_total_real, perc_90_espera_total_simulada)),bins=15)
bins_espera_total_promedio_19_21 = np.histogram_bin_edges(np.concatenate((espera_total_promedio_19_21_real, espera_total_promedio_19_21_simulada)),bins=15)
bins_tasa_fin_rutinas = np.histogram_bin_edges(np.concatenate((tasa_finalizacion_rutinas_real, tasa_finalizacion_rutinas_simulada)),bins=15)
bins_tasa_fin_rutinas_express = np.histogram_bin_edges(np.concatenate((tasa_finalizacion_rutinas_express_real, tasa_finalizacion_rutinas_express_simulada)),bins=15)
bins_insatisfaccion_promedio = np.histogram_bin_edges(np.concatenate((insatisfaccion_promedio_real, insatisfaccion_promedio_simulada)),bins=15)
bins_utilizacion_operacional_trotadoras = np.histogram_bin_edges(np.concatenate((utilizacion_operacional_trotadoras_real, utilizacion_operacional_trotadoras_simulada)),bins=15)
bins_utilizacion_operacional_ap_pecho = np.histogram_bin_edges(np.concatenate((utilizacion_operacional_aperturas_pecho_real, utilizacion_operacional_aperturas_pecho_simulada)),bins=15)
bins_cola_prom_ap_pecho = np.histogram_bin_edges(np.concatenate((cola_promedio_aperturas_pecho_real, cola_promedio_aperturas_pecho_simulada)),bins=15)
bins_cola_prom_remo_sent = np.histogram_bin_edges(np.concatenate((cola_promedio_remo_sentado_real, cola_promedio_remo_sentado_simulada)),bins=15)
bins_utilizacion_entrenadores = np.histogram_bin_edges(np.concatenate((utilizacion_entrenadores_real, utilizacion_entrenadores_simulada)),bins=15)
bins_duracion_quiebres_agua = np.histogram_bin_edges(np.concatenate((duracion_quiebres_agua_real, duracion_quiebres_agua_simulada)),bins=15)
bins_duracion_quiebres_toallas = np.histogram_bin_edges(np.concatenate((duracion_quiebres_toallas_real, duracion_quiebres_toallas_simulada)),bins=15)
bins_numero_fallas_maquinas = np.histogram_bin_edges(np.concatenate((numero_fallas_maquinas_real, numero_fallas_maquinas_simulada)),bins=15)
bins_espera_promedio_rep = np.histogram_bin_edges(np.concatenate((espera_promedio_reparacion_real, espera_promedio_reparacion_simulada)),bins=15)
bins_minutos_operacion_post_cierre = np.histogram_bin_edges(np.concatenate((minutos_operacion_post_cierre_real, minutos_operacion_post_cierre_simulada)),bins=15)


def graficar_histograma(datos_reales, datos_simulados, bins, titulo, eje_x):
    plt.figure(figsize=(8,5))
    plt.hist(datos_reales, bins=bins, density=True, alpha=0.5, label="Datos reales")
    plt.hist(datos_simulados, bins=bins, density=True, alpha=0.5, label="Datos simulados")
    plt.xlabel(f"{eje_x}")
    plt.ylabel("Densidad")
    plt.title(f"{titulo}")
    plt.legend()
    plt.show()

graficar_histograma(llegadas_reales, llegadas_simuladas, bins_llegadas, "Distribución del número de llegadas", "Número de llegadas")
graficar_histograma(tasa_rechazo_real, tasa_rechazo_simulada, bins_tasa_rechazo, "Distribución de la tasa de rechazo","Tasa de rechazo")
graficar_histograma(ocupacion_promedio_real, ocupacion_promedio_simulada, bins_ocupacion_promedio, "Distribución de la ocupación promedio", "Número promedio de usuarios")
graficar_histograma(prop_cap_maxima_real, prop_cap_maxima_simulada, bins_proporcion_cap_max, "Distribución de la proporción a capacidad máxima", "Proporción del tiempo")
graficar_histograma(espera_total_promedio_real, espera_total_promedio_simulada, bins_espera_total_promedio, "Distribución de la espera total promedio", "Tiempo de espera (minutos)")
graficar_histograma(perc_90_espera_total_real, perc_90_espera_total_simulada, bins_p90_espera_total_promedio, "Distribución del percentil 90 de espera total", "Percentil 90 de espera (minutos)")
graficar_histograma(espera_total_promedio_19_21_real ,espera_total_promedio_19_21_simulada, bins_espera_total_promedio_19_21,"Distribución de la espera promedio entre 19:00 y 21:00","Tiempo de espera (minutos)")
graficar_histograma(tasa_finalizacion_rutinas_real, tasa_finalizacion_rutinas_simulada,bins_tasa_fin_rutinas,"Distribución de la tasa de finalización de rutinas","Tasa de finalización")
graficar_histograma(tasa_finalizacion_rutinas_express_real,tasa_finalizacion_rutinas_express_simulada,bins_tasa_fin_rutinas_express,"Distribución de la finalización de rutinas express","Tasa de finalización")
graficar_histograma(insatisfaccion_promedio_real,insatisfaccion_promedio_simulada,bins_insatisfaccion_promedio,"Distribución de la insatisfacción promedio","Índice de insatisfacción")
graficar_histograma(utilizacion_operacional_trotadoras_real,utilizacion_operacional_trotadoras_simulada,bins_utilizacion_operacional_trotadoras,"Distribución de la utilización de trotadoras", "Utilización operacional")
graficar_histograma(utilizacion_operacional_aperturas_pecho_real, utilizacion_operacional_aperturas_pecho_simulada, bins_utilizacion_operacional_ap_pecho,"Distribución de la utilización de aperturas de pecho","Utilización operacional")
graficar_histograma(cola_promedio_aperturas_pecho_real,cola_promedio_aperturas_pecho_simulada,bins_cola_prom_ap_pecho,"Distribución de la cola promedio de aperturas de pecho","Número promedio de usuarios en cola")
graficar_histograma(cola_promedio_remo_sentado_real, cola_promedio_remo_sentado_simulada, bins_cola_prom_remo_sent, "Distribución de la cola promedio de remo sentado", "Número promedio de usuarios en cola")
graficar_histograma(utilizacion_entrenadores_real, utilizacion_entrenadores_simulada, bins_utilizacion_entrenadores, "Distribución de la utilización de entrenadores", "Utilización")
graficar_histograma(duracion_quiebres_agua_real, duracion_quiebres_agua_simulada, bins_duracion_quiebres_agua, "Distribución de la duración de quiebres de agua", "Duración (minutos)")
graficar_histograma(duracion_quiebres_toallas_real, duracion_quiebres_toallas_simulada,bins_duracion_quiebres_toallas,"Distribución de la duración de quiebres de toallas","Duración (minutos)")
graficar_histograma(numero_fallas_maquinas_real,numero_fallas_maquinas_simulada,bins_numero_fallas_maquinas,"Distribución del número de fallas de máquinas", "Número de fallas")
graficar_histograma(espera_promedio_reparacion_real, espera_promedio_reparacion_simulada, bins_espera_promedio_rep, "Distribución de la espera promedio por reparación", "Tiempo de espera (minutos)")
graficar_histograma(minutos_operacion_post_cierre_real, minutos_operacion_post_cierre_simulada, bins_minutos_operacion_post_cierre, "Distribución de la operación posterior al cierre", "Duración (minutos)")


def test_mann_whitney(datos_reales, datos_simulados, medida_desempeno):
    U, p_value = mannwhitneyu(datos_reales, datos_simulados, method = "asymptotic")
    print(f"\nMedida de desempeño: {medida_desempeno}")
    print("U=", U)
    print("p_value", p_value)
    if p_value < alpha:
        print("Hay evidencia para RECHAZAR H0")
    else:
        print("NO hay evidencia para rechazar H0")
    return U, p_value

test_mann_whitney(llegadas_reales,llegadas_simuladas, "Número de llegadas")
test_mann_whitney(tasa_rechazo_real, tasa_rechazo_simulada, "Tasa de rechazo")
test_mann_whitney(ocupacion_promedio_real, ocupacion_promedio_simulada, "Ocupación promedio")
test_mann_whitney(prop_cap_maxima_real,prop_cap_maxima_simulada, "Proporción a capacidad máxima")
test_mann_whitney(espera_total_promedio_real,espera_total_promedio_simulada,"Espera total promedio")
test_mann_whitney(perc_90_espera_total_real,perc_90_espera_total_simulada,"Percentil 90 de espera total")
test_mann_whitney(espera_total_promedio_19_21_real,espera_total_promedio_19_21_simulada,"Espera promedio entre 19:00 y 21:00")
test_mann_whitney(tasa_finalizacion_rutinas_real,tasa_finalizacion_rutinas_simulada,"Tasa de finalización de rutinas")
test_mann_whitney(tasa_finalizacion_rutinas_express_real,tasa_finalizacion_rutinas_express_simulada,"Tasa de finalización de rutinas express")
test_mann_whitney(insatisfaccion_promedio_real,insatisfaccion_promedio_simulada,"Insatisfacción promedio")
test_mann_whitney(utilizacion_operacional_trotadoras_real,utilizacion_operacional_trotadoras_simulada,"Utilización operacional de trotadoras")
test_mann_whitney(utilizacion_operacional_aperturas_pecho_real,utilizacion_operacional_aperturas_pecho_simulada,"Utilización operacional de aperturas de pecho")
test_mann_whitney(cola_promedio_aperturas_pecho_real,cola_promedio_aperturas_pecho_simulada,"Cola promedio de aperturas de pecho")
test_mann_whitney(cola_promedio_remo_sentado_real,cola_promedio_remo_sentado_simulada,"Cola promedio de remo sentado")
test_mann_whitney(utilizacion_entrenadores_real,utilizacion_entrenadores_simulada,"Utilización de entrenadores")
test_mann_whitney(duracion_quiebres_agua_real,duracion_quiebres_agua_simulada,"Duración de quiebres de agua")
test_mann_whitney(duracion_quiebres_toallas_real,duracion_quiebres_toallas_simulada,"Duración de quiebres de toallas")
test_mann_whitney(numero_fallas_maquinas_real,numero_fallas_maquinas_simulada, "Número de fallas de máquinas")
test_mann_whitney(espera_promedio_reparacion_real, espera_promedio_reparacion_simulada,"Espera promedio por reparación")
test_mann_whitney(minutos_operacion_post_cierre_real, minutos_operacion_post_cierre_simulada, "Operación posterior al cierre")
