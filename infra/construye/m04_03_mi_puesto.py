"""Constrúyelo tú (M04-03): tu propio puesto de inspección.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m04_03_mi_puesto.py
"""
import csv
import hashlib
from collections import Counter
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from PIL import Image

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
UMBRAL = 0.5          # probabilidad de defecto a partir de la cual la carcasa va a revisión
DUDA = 0.0            # ± alrededor del umbral en que decide una persona (0 = sin zona de duda)

# --- PASO 1: el modelo y las carcasas que llegan (ya está hecho) -------------
RUTA_MODELO = "/data/modelo_vision.joblib"            # el que guardó lab m04-01
modelo = joblib.load(RUTA_MODELO)
fotos = pd.read_csv("/data/imagenes/manifiesto.csv")
llegan = pd.concat([fotos[fotos.defecto == 0].iloc[28:], fotos[fotos.defecto == 1].iloc[28:]])  # el examen del M04-01
print(f"carcasas que llegan al puesto: {len(llegan)} ({int(llegan.defecto.sum())} con rayón, que el puesto no sabe)")

# --- PASO 2: la probabilidad de cada carcasa -----------------------------------
# (pega aquí el bloque del paso 2)
def probabilidad(ruta):
    numeros = np.asarray(Image.open(ruta).convert("L").resize((16, 16)), dtype=np.float32).reshape(1, -1) / 255.0
    return float(modelo.predict_proba(numeros)[0, 1])

llegan = llegan.assign(probabilidad=[probabilidad(r) for r in llegan["ruta"]])
tramos = pd.cut(llegan["probabilidad"], [0, 0.2, 0.4, 0.6, 0.8, 1.0], include_lowest=True)
print(tramos.value_counts().sort_index().to_string())

# --- PASO 3: decidir con el umbral y la zona de duda ---------------------------
# (pega aquí el bloque del paso 3)
def decidir(p):
    if abs(p - UMBRAL) < DUDA:
        return "dudosa"                                  # la decide una persona
    return "revisar" if p >= UMBRAL else "aceptar"

llegan = llegan.assign(decision=[decidir(p) for p in llegan["probabilidad"]])
print(dict(Counter(llegan["decision"])))
escapan = int(((llegan["decision"] == "aceptar") & (llegan["defecto"] == 1)).sum())
paradas = int(((llegan["decision"] == "revisar") & (llegan["defecto"] == 0)).sum())
print(f"rayones aceptados={escapan}  buenas mandadas a revisar={paradas}")

# --- PASO 4: escribir el registro ----------------------------------------------
# (pega aquí el bloque del paso 4)
huella = hashlib.sha256(open(RUTA_MODELO, "rb").read()).hexdigest()[:12]
ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
with open("/data/mi_registro.csv", "w", newline="") as f:
    escritor = csv.writer(f)
    escritor.writerow(["hora", "foto", "huella_modelo", "probabilidad", "decision"])
    for _, c in llegan.iterrows():
        escritor.writerow([ahora, c["ruta"].split("/")[-1], huella, round(c["probabilidad"], 3), c["decision"]])
print(f"mi_registro.csv: {len(llegan)} líneas, modelo {huella}")

# Reto 1: elegir la zona de duda con los costes y la capacidad del turno
COSTE_RAYON, COSTE_PERSONA, CAPACIDAD = 500, 5, 10       # € por rayón aceptado, € por dudosa, dudosas que caben en el turno
print("duda  dudosas  rayones_aceptados  coste   cabe_en_el_turno")
for duda in (0.0, 0.05, 0.1, 0.2):
    dec = ["dudosa" if abs(p - UMBRAL) < duda else "revisar" if p >= UMBRAL else "aceptar" for p in llegan["probabilidad"]]
    dudosas = dec.count("dudosa")
    rayones = sum(d == "aceptar" and r == 1 for d, r in zip(dec, llegan["defecto"]))
    coste = COSTE_RAYON * rayones + COSTE_PERSONA * dudosas
    print(f"{duda:4.2f}  {dudosas:7d}  {rayones:17d}  {coste:5d} €  {'sí' if dudosas <= CAPACIDAD else 'NO'}")

# Reto 2: una carcasa llega sin foto
def probabilidad_segura(ruta):
    try:
        return probabilidad(ruta)
    except FileNotFoundError:
        return None                                     # sin foto no hay probabilidad

def decidir_seguro(p):
    return "revisar (sin foto)" if p is None else decidir(p)

for ruta in ["/data/imagenes/buenas/ok_30.png", "/data/imagenes/no_existe.png"]:
    print(ruta.split("/")[-1], "->", decidir_seguro(probabilidad_segura(ruta)))