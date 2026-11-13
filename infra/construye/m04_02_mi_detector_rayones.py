"""Constrúyelo tú (M04-02): tu propio localizador de rayones.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m04_02_mi_detector_rayones.py
"""
import numpy as np
import pandas as pd
from PIL import Image

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
BRILLO_RAYON = 230      # brillo medio de fila a partir del cual se considera que hay un rayón
MAS_LUZ = 0             # cuánto se aclara una foto buena en el paso 6 (0 = luz normal)

# --- PASO 1: las fotos, en números (ya está hecho) ---------------------------
fotos = pd.read_csv("/data/imagenes/manifiesto.csv")   # ruta, defecto y fila real del rayón (y)
malas = fotos[fotos["defecto"] == 1]
buenas = fotos[fotos["defecto"] == 0]

def a_numeros(ruta):
    return np.asarray(Image.open(ruta).convert("L"), dtype=np.float32)    # 64 × 64, de 0 a 255

foto = a_numeros(malas["ruta"].iloc[0])
print(f"foto defectuosa: {foto.shape[0]} filas × {foto.shape[1]} columnas; el rayón está en la fila {int(malas['y'].iloc[0])}")

# --- PASO 2: el brillo de cada fila --------------------------------------------
# (pega aquí el bloque del paso 2)
brillo_filas = foto.mean(axis=1)                    # una media por fila: 64 números
mas_claras = np.argsort(brillo_filas)[::-1][:3]      # las tres filas con más brillo
for fila in mas_claras:
    print(f"fila {fila:2d}: brillo medio {brillo_filas[fila]:.0f}")

# --- PASO 3: localizar el rayón y comprobarlo ----------------------------------
# (pega aquí el bloque del paso 3)
def fila_mas_clara(numeros):
    return int(numeros.mean(axis=1).argmax())

aciertos = sum(abs(fila_mas_clara(a_numeros(r)) - int(y)) <= 2 for r, y in zip(malas["ruta"], malas["y"]))
print(f"rayón localizado en {aciertos} de {len(malas)} fotos defectuosas")

# --- PASO 4: decidir si hay rayón ----------------------------------------------
# (pega aquí el bloque del paso 4)
def hay_rayon(numeros):
    return numeros.mean(axis=1).max() > BRILLO_RAYON

marca_malas = sum(hay_rayon(a_numeros(r)) for r in malas["ruta"])
marca_buenas = sum(hay_rayon(a_numeros(r)) for r in buenas["ruta"])
print(f"con brillo > {BRILLO_RAYON}: malas marcadas={marca_malas} de {len(malas)}  buenas marcadas={marca_buenas} de {len(buenas)}")

# Una pieza buena, fotografiada con más luz
clara = np.clip(a_numeros(buenas["ruta"].iloc[0]) + MAS_LUZ, 0, 255)
print(f"pieza buena con +{MAS_LUZ} de luz: fila más clara con brillo {clara.mean(axis=1).max():.0f} -> rayón={hay_rayon(clara)}")

# Reto 1: los mismos rayones, pero verticales (la foto girada 90°)
verticales = [np.rot90(a_numeros(r)) for r in malas["ruta"]]
print(f"rayones verticales marcados por la regla de filas: {sum(hay_rayon(v) for v in verticales)} de {len(verticales)}")

def hay_rayon_2(numeros):
    return max(numeros.mean(axis=1).max(), numeros.mean(axis=0).max()) > BRILLO_RAYON   # filas o columnas

print(f"con filas y columnas: verticales={sum(hay_rayon_2(v) for v in verticales)} de {len(verticales)}  "
      f"horizontales={sum(hay_rayon_2(a_numeros(r)) for r in malas['ruta'])} de {len(malas)}  "
      f"buenas={sum(hay_rayon_2(a_numeros(r)) for r in buenas['ruta'])} de {len(buenas)}")