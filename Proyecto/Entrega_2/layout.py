import numpy as np
from config import LADO_CELDA,PESO_MANHATTAN,PESO_EUCLIDIANA

def coordenadas(celda):
    fila = (celda-1)//7
    columna = 6-((celda-1)%7)
    return columna*LADO_CELDA,fila*LADO_CELDA

def distancia(celda_1,celda_2):
    x1,y1 = coordenadas(celda_1)
    x2,y2 = coordenadas(celda_2)

    manhattan = abs(x1-x2)+abs(y1-y2)
    euclidiana = np.sqrt((x1-x2)**2+(y1-y2)**2)

    return PESO_MANHATTAN*manhattan+PESO_EUCLIDIANA*euclidiana

def tiempo_desplazamiento(celda_1,celda_2,velocidad):
    return distancia(celda_1,celda_2)/velocidad