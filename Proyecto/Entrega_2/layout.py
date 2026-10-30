import numpy as np
from config import LADO_CELDA,PESO_MANHATTAN,PESO_EUCLIDIANA

#def como se calculan los desplazamientos

def coordenadas(ubicacion):
    # Si ya tenemos coordenadas en metros
    if isinstance(ubicacion, tuple):
        return ubicacion
    # Si tenemos un numero de celda
    fila = (ubicacion - 1) // 7
    columna = 6 - ((ubicacion - 1) % 7)
    return columna * LADO_CELDA, fila * LADO_CELDA

def distancia(celda_1,celda_2):
    x1,y1 = coordenadas(celda_1)
    x2,y2 = coordenadas(celda_2)

    manhattan = abs(x1-x2)+abs(y1-y2)
    euclidiana = np.sqrt((x1-x2)**2+(y1-y2)**2)

    return PESO_MANHATTAN*manhattan+PESO_EUCLIDIANA*euclidiana

def tiempo_desplazamiento(celda_1,celda_2,velocidad):
    return distancia(celda_1,celda_2)/velocidad

def interpolar_posicion(origen, destino, fraccion):
    x0, y0 = coordenadas(origen)
    x1, y1 = coordenadas(destino)
    x = x0 + fraccion * (x1 - x0)
    y = y0 + fraccion * (y1 - y0)
    return (x, y)