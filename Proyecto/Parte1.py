import pandas as pd
import numpy as np
import simpy
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, gamma, poisson
import matplotlib.pyplot as plt


#se leen los archivos y se agrega el separador junto con el decimal para "adaptar" los datos al lenguaje de py, ya que venían con el decimal "," por defecto
log_operacional = pd.read_csv("log_operacional_historico.csv", sep=";", decimal = ",")
log_reparaciones = pd.read_csv("log_reparaciones_historico.csv", sep=";", decimal = ",")


##################### PARTE 1a ##########################

#revisar que los datos estén "limpios"
#print(log_operacional["event_type"].value_counts())

#se ve que hay 41 datos que son "evento_mal_escrito"
#considerar qué hacer con ellos

##RUTINAS##
rutinas = log_operacional[log_operacional["event_type"] == "visit"].copy()
print(rutinas["routine"].value_counts())





