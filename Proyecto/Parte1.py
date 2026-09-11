import pandas as pd
import numpy as np
import simpy
from scipy.stats import expon, lognorm, kstest, kruskal, binom, chi2, gamma, poisson
import matplotlib.pyplot as plt


#se leen los archivos y se agrega el separador junto con el decimal para "adaptar" los datos al lenguaje de py, ya que venían con el decimal "," por defecto
log_operacional = pd.read_csv("log_operacional_historico.csv", sep=";", decimal = ",")
log_reparaciones = pd.read_csv("log_reparaciones_historico.csv", sep=";", decimal = ",")


##################### PARTE 1a ##########################

print(log_operacional["event_type"].value_counts())