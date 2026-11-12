"""Constrúyelo tú (M02-04): tu propio dataset de la línea.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m02_04_mi_dataset.py
"""
import sqlite3

import pandas as pd

# --- PASO 1: leer las dos bases (ya está hecho) ------------------------------
def leer(base, consulta):
    with sqlite3.connect(f"file:/data/{base}?mode=ro", uri=True) as con:   # solo lectura
        return pd.read_sql_query(consulta, con)

lecturas = leer("historial.sqlite", "SELECT pieza_id, ts, temperatura_c, vibracion_mm_s, corriente_a FROM lecturas")
inspecciones = leer("calidad.sqlite", "SELECT pieza_id, ts_pieza, defecto FROM inspecciones")
print(f"histórico: {len(lecturas)} registros   calidad: {len(inspecciones)} inspecciones")

# --- PASO 2: unir solo por identificador ---------------------------------------
# (pega aquí el bloque del paso 2)
por_id = lecturas.merge(inspecciones, on="pieza_id")
inspecciones_por_id = inspecciones.groupby("pieza_id").size()
print(f"unión por pieza_id: {len(por_id)} filas")
print(f"identificadores con más de una inspección: {int((inspecciones_por_id > 1).sum())}")

# --- PASO 3: ver una carcasa mal unida -----------------------------------------
# (pega aquí el bloque del paso 3)
# Un identificador que calidad ha marcado unas veces como buena y otras como defectuosa
resultados = inspecciones.groupby("pieza_id")["defecto"].nunique()
ejemplo = resultados[resultados > 1].index[0]
filas = por_id[por_id["pieza_id"] == ejemplo][["pieza_id", "ts", "ts_pieza", "defecto"]]
print(f"{ejemplo}: {len(filas)} filas en la unión; las primeras:")
print(filas.head(6).to_string(index=False))

# --- PASO 4: unir por identificador y hora -------------------------------------
# (pega aquí el bloque del paso 4)
bien = lecturas.merge(inspecciones, left_on=["pieza_id", "ts"], right_on=["pieza_id", "ts_pieza"])
desde = inspecciones["ts_pieza"].min()                    # calidad empezó a inspeccionar aquí
registros_desde = int((lecturas["ts"] >= desde).sum())
print(f"unión por pieza_id + hora: {len(bien)} filas")
print(f"registros sin inspección: {registros_desde - len(bien)}   inspecciones sin registro: {len(inspecciones) - len(bien)}")

# --- PASO 5: guardar el dataset ------------------------------------------------
# (pega aquí el bloque del paso 5)
dataset = bien[["pieza_id", "ts", "temperatura_c", "vibracion_mm_s", "corriente_a", "defecto"]].sort_values("ts")
dataset.to_csv("/data/mi_dataset.csv", index=False)
print(f"mi_dataset.csv: {len(dataset)} piezas, defectuosas={int(dataset['defecto'].sum())} ({dataset['defecto'].mean():.0%})")
del_comando = pd.read_csv("/data/dataset_linea.csv")
print(f"dataset_linea.csv del comando: {len(del_comando)} piezas (el tuyo tiene las carcasas fabricadas desde entonces)")