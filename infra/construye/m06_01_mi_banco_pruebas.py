"""Constrúyelo tú (M06-01): tu propio banco de pruebas de inferencia.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m06_01_mi_banco_pruebas.py
"""
import os
import time

import joblib
import numpy as np
import pandas as pd

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
MODELO = "modelo_defecto.joblib"     # el elegido en el M03-03
# MODELO = "mi_modelo.joblib"
CICLO_S = 1.0                        # lo que tarda la estación en hacer una carcasa
PIEZAS = 1000                        # cuántas piezas se prueban

# --- PASO 1: el modelo y unas piezas de prueba (ya está hecho) ---------------
ruta = f"/data/{MODELO}"
modelo = joblib.load(ruta)
piezas = pd.read_csv("/data/limpio.csv")[["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]]
piezas = piezas.sample(PIEZAS, replace=True, random_state=0).reset_index(drop=True)
print(f"modelo={MODELO} tipo={type(modelo).__name__} tamaño={os.path.getsize(ruta) / 1024:.1f} KB  piezas de prueba={len(piezas)}")

# --- PASO 2: la primera inferencia y las siguientes ----------------------------
# (pega aquí el bloque del paso 2)
def medir_una(i):
    inicio = time.perf_counter()
    modelo.predict(piezas.iloc[[i]])                  # una sola pieza, como en la línea
    return (time.perf_counter() - inicio) * 1000      # milisegundos

print("ms: primera={:.2f}  segunda={:.2f}  tercera={:.2f}".format(medir_una(0), medir_una(1), medir_una(2)))

# --- PASO 3: el peor caso en mil piezas ----------------------------------------
# (pega aquí el bloque del paso 3)
tiempos = np.array([medir_una(i) for i in range(len(piezas))])
p99 = np.percentile(tiempos, 99)
print(f"ms por pieza: media={tiempos.mean():.2f}  p99={p99:.2f}  máximo={tiempos.max():.2f}")

# --- PASO 4: una a una o en lote -----------------------------------------------
# (pega aquí el bloque del paso 4)
inicio = time.perf_counter()
modelo.predict(piezas)                                 # las mil de golpe
por_pieza_lote = (time.perf_counter() - inicio) * 1000 / len(piezas)
print(f"en lote: {por_pieza_lote:.4f} ms por pieza  ({tiempos.mean() / por_pieza_lote:.0f} veces menos que una a una)")

# --- PASO 5: el margen frente al ciclo -----------------------------------------
# (pega aquí el bloque del paso 5)
peor = tiempos.max()
print(f"peor caso={peor:.2f} ms de un ciclo de {CICLO_S * 1000:.0f} ms -> usa el {peor / (CICLO_S * 1000):.2%} del ciclo")
print("veredicto:", "cabe con margen" if peor < CICLO_S * 1000 * 0.1 else "NO cabe con margen (más del 10 % del ciclo)")


# --- RETO 1 
# Reto 1: un plazo para cada dictamen; si no llega, la pieza va a revisión
PLAZO_MS = 2
tarde = int((tiempos > PLAZO_MS).sum())
print(f"plazo={PLAZO_MS} ms: dictámenes a tiempo={len(tiempos) - tarde}  tarde={tarde} -> {tarde} piezas a revisión por no tener dictamen")
