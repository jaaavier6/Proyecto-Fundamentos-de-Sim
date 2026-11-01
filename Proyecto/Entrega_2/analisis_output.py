import pandas as pd
import numpy as np
from scipy.stats import t
import matplotlib.pyplot as plt

datos = pd.read_csv("metricas_300_replicas.csv",sep=";").head(200)

medidas = ["numero_llegadas","tasa_rechazo","ocupacion_promedio","proporcion_capacidad_maxima","espera_total_promedio","percentil_90_espera_total","espera_total_promedio_19_21","tasa_finalizacion_rutinas","tasa_finalizacion_rutinas_express","insatisfaccion_promedio_admitidos","utilizacion_operacional_trotadoras","utilizacion_operacional_aperturas_pecho","cola_promedio_aperturas_pecho","cola_promedio_remo_sentado","utilizacion_entrenadores","duracion_quiebres_agua","duracion_quiebres_toallas","numero_fallas_maquinas","espera_promedio_reparacion","minutos_operacion_postcierre"]

for columna in datos.columns:
    datos[columna] = pd.to_numeric(datos[columna].astype(str).str.replace(",","."),errors="raise")


n = len(datos)
t_critico = t.ppf(0.975,n-1)

def calcular_resumen(columnas):
    resultados = []
    for medida in columnas:
        media = datos[medida].mean()
        desviacion = datos[medida].std(ddof=1)
        error = t_critico*desviacion/np.sqrt(n)
        resultados.append([medida,media,desviacion,media-error,media+error])
    return pd.DataFrame(resultados,columns=["medida","promedio","desviacion","ic95_inferior","ic95_superior"])

tabla = calcular_resumen(medidas)
tabla.to_csv("analisis_output_200.csv",sep=";",decimal=",",index=False)

franjas = ["espera_total_promedio_07_10","espera_total_promedio_10_13","espera_total_promedio_13_16","espera_total_promedio_16_19","espera_total_promedio_19_21"]
perfiles = ["tasa_finalizacion_rutinas_estandar","tasa_finalizacion_rutinas_express","tasa_finalizacion_rutinas_flexible","tasa_finalizacion_rutinas_intenso","insatisfacciones_promedio_estandar","insatisfacciones_promedio_express","insatisfacciones_promedio_flexible","insatisfacciones_promedio_intenso"]
recursos = ["utilizacion_operacional_trotadoras","utilizacion_operacional_aperturas_pecho","utilizacion_operacional_remo_sentado","utilizacion_operacional_prensa_piernas","utilizacion_operacional_poleas","cola_promedio_aperturas_pecho","cola_promedio_remo_sentado","utilizacion_recepcionistas","utilizacion_entrenadores","utilizacion_tecnicos","espera_promedio_entrenador"]
cierre = ["usuarios_al_cierre","minutos_operacion_postcierre"]
adicionales = ["permanencia_promedio","percentil_90_permanencia","tasa_cumplimiento_ejercicios","tasa_finalizacion_cardio","numero_ejercicios_omitidos","numero_ejercicios_pendientes","utilizacion_efectiva_aperturas_pecho","numero_quiebres_agua","numero_quiebres_toallas","tiempo_indisponibilidad_maquinas","costo_operacional_total","costo_por_admitido"]

tabla_franjas = calcular_resumen(franjas)
tabla_perfiles = calcular_resumen(perfiles)
tabla_recursos = calcular_resumen(recursos)
tabla_cierre = calcular_resumen(cierre)
tabla_adicionales = calcular_resumen(adicionales)

tabla_franjas.to_csv("analisis_franjas.csv",sep=";",decimal=",",index=False)
tabla_perfiles.to_csv("analisis_perfiles.csv",sep=";",decimal=",",index=False)
tabla_recursos.to_csv("analisis_recursos.csv",sep=";",decimal=",",index=False)
tabla_cierre.to_csv("analisis_cierre.csv",sep=";",decimal=",",index=False)
tabla_adicionales.to_csv("analisis_adicionales.csv",sep=";",decimal=",",index=False)

print("\nFRANJAS HORARIAS")
print(tabla_franjas.round(4).to_string(index=False))
print("\nPERFILES")
print(tabla_perfiles.round(4).to_string(index=False))
print("\nRECURSOS")
print(tabla_recursos.round(4).to_string(index=False))
print("\nCIERRE")
print(tabla_cierre.round(4).to_string(index=False))
print("\nMEDIDAS ADICIONALES")
print(tabla_adicionales.round(4).to_string(index=False))

nombres_franjas = ["07-10","10-13","13-16","16-19","19-21"]
plt.figure()
plt.plot(nombres_franjas,tabla_franjas["promedio"],marker="o")
plt.xlabel("Franja horaria")
plt.ylabel("Espera promedio [min]")
plt.title("Espera promedio por franja horaria")
plt.tight_layout()
plt.show()

nombres_perfiles = ["Estándar","Express","Flexible","Intenso"]
plt.figure()
plt.bar(nombres_perfiles,tabla_perfiles["promedio"].iloc[:4])
plt.xlabel("Perfil")
plt.ylabel("Tasa de finalización")
plt.title("Finalización de rutinas por perfil")
plt.tight_layout()
plt.show()

nombres_recursos = ["Trotadoras","Aperturas","Remo","Prensa piernas","Poleas"]
plt.figure()
plt.bar(nombres_recursos,tabla_recursos["promedio"].iloc[:5])
plt.xlabel("Recurso")
plt.ylabel("Utilización operacional")
plt.title("Utilización operacional de máquinas")
plt.xticks(rotation=20)
plt.tight_layout()
plt.show()