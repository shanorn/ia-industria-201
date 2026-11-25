"""Constrúyelo tú (M07-02): tu propio vigilante de deriva.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m07_02_mi_vigilante_deriva.py
"""
import sqlite3

import joblib
import pandas as pd

SENALES = ["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
GRADOS = 8.0           # cuánto más caliente trabaja la línea en la simulación del paso 3
TOLERANCIA = 0.10      # cuánto puede cambiar la tasa de «revisar» antes de avisar
DESVIACIONES = 3       # cuántas desviaciones puede moverse la media de una señal antes de avisar

# --- PASO 1: el modelo y los datos con los que se entrenó (ya está hecho) ----
modelo = joblib.load("/data/modelo_defecto.joblib")
df = pd.read_csv("/data/limpio.csv").sort_values("pieza_id")
corte = int(len(df) * 0.7)
entrenamiento, base = df.iloc[:corte], df.iloc[corte:]            # base: el examen, cuando todo iba bien
print(f"entrenamiento={len(entrenamiento)} piezas  base de comparación={len(base)} piezas")

# --- PASO 2: la tasa de revisar de la base -------------------------------------
# (pega aquí el bloque del paso 2)
def tasa_revisar(datos):
    return float((modelo.predict_proba(datos[SENALES])[:, 1] >= 0.5).mean())

tasa_base = tasa_revisar(base)
print(f"tasa de revisar en la base: {tasa_base:.2f}")

# --- PASO 3: simular que la línea se calienta ----------------------------------
# (pega aquí el bloque del paso 3)
movida = base.copy()
movida["temperatura_c"] += GRADOS
tasa = tasa_revisar(movida)
alerta = abs(tasa - tasa_base) > TOLERANCIA
print(f"con +{GRADOS} °C: tasa de revisar={tasa:.2f}  ->  {'DERIVA: el modelo se comporta distinto' if alerta else 'normal'}")

# --- PASO 4: vigilar también los datos de entrada ------------------------------
# (pega aquí el bloque del paso 4)
def deriva_datos(nuevos):
    avisos = []
    for s in SENALES:
        media, desv = entrenamiento[s].mean(), entrenamiento[s].std()
        error_media = desv / len(nuevos) ** 0.5                # cuánto varía una media de tantas piezas
        z = (nuevos[s].mean() - media) / error_media
        if abs(z) > DESVIACIONES:
            avisos.append(f"{s} ({z:+.0f})")
    return avisos

print("señales que han cambiado:", deriva_datos(movida) or "ninguna")

# --- PASO 5: las dos comprobaciones sobre la línea de ahora --------------------
# (pega aquí el bloque del paso 5)
with sqlite3.connect("file:/data/historial.sqlite?mode=ro", uri=True) as con:
    ahora = pd.read_sql_query("SELECT temperatura_c, vibracion_mm_s, corriente_a FROM lecturas ORDER BY id DESC LIMIT 120", con)
ahora["presion_bar"] = 6.0
print(f"línea de ahora: tasa de revisar={tasa_revisar(ahora):.2f} (base {tasa_base:.2f})")
print("señales de la línea de ahora que han cambiado:", deriva_datos(ahora) or "ninguna")

# Reto 1: una deriva en otra señal
otra = base.copy()
otra["corriente_a"] += 0.3                              # el motor trabaja con más esfuerzo
tasa_otra = tasa_revisar(otra)
print(f"corriente +0,3 A: tasa de revisar={tasa_otra:.2f} (base {tasa_base:.2f})  "
      f"-> {'DERIVA en el modelo' if abs(tasa_otra - tasa_base) > TOLERANCIA else 'el modelo no se entera'}")
print("señales que han cambiado:", deriva_datos(otra) or "ninguna")