"""Constrúyelo tú (M01-02): tus propios indicadores.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m01_02_mis_indicadores.py
"""
import sqlite3
from datetime import datetime, timezone

import pandas as pd

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
VENTANA = 120              # cuántas lecturas recientes miran los indicadores (las mismas que el panel)
MARGEN_C = 70.0            # temperatura a partir de la cual una lectura está fuera de margen
MAX_ANTIGUEDAD_S = 2      # a partir de cuántos segundos sin datos nuevos el dato ya no es actual
CICLO_NOMINAL_S = 1.0      # lo que debería tardar la estación en hacer una carcasa

# --- PASO 1: leer el histórico (ya está hecho) -------------------------------
con = sqlite3.connect("file:/data/historial.sqlite?mode=ro", uri=True)   # solo lectura, como el panel
df = pd.read_sql_query(
    "SELECT pieza_id, ts, temperatura_c, tiempo_ciclo_s FROM lecturas ORDER BY id DESC LIMIT ?",
    con, params=(VENTANA,))
df = df.iloc[::-1]                     # de la más antigua a la más reciente
print(f"lecturas leídas del histórico: {len(df)}")

# --- PASO 2: la última carcasa y cuánto hace que llegó -------------------------
ultima = df.iloc[-1]
hora = datetime.fromisoformat(ultima["ts"])                    # la hora con la que la guardó el archivador
antiguedad_s = (datetime.now(timezone.utc) - hora).total_seconds()
print(f"última carcasa: {ultima['pieza_id']} a {ultima['temperatura_c']} °C, hace {antiguedad_s:.0f} s")

# --- PASO 3: decidir si el dato está vivo --------------------------------------
vivo = antiguedad_s <= MAX_ANTIGUEDAD_S
estado = "VIVO" if vivo else f"CONGELADO (sin datos nuevos desde hace {antiguedad_s:.0f} s)"
print(f"estado del dato: {estado}")

# --- PASO 4: lecturas fuera de margen ------------------------------------------
fuera = int((df["temperatura_c"] > MARGEN_C).sum())
print(f"temperatura media={df['temperatura_c'].mean():.2f} °C  lecturas fuera de margen={fuera} de {len(df)}")

# --- PASO 5: el ritmo de la estación -------------------------------------------
ciclo_medio = df["tiempo_ciclo_s"].mean()
rendimiento = CICLO_NOMINAL_S / ciclo_medio                    # 1,0 = al ritmo previsto
print(f"tiempo de ciclo medio={ciclo_medio:.2f} s  rendimiento={rendimiento:.0%}")

# --- PASO 6: un informe de una línea -------------------------------------------
if vivo:
    print(f"INFORME EST-01: {ultima['pieza_id']} {ultima['temperatura_c']} °C | fuera de margen {fuera}/{len(df)} | rendimiento {rendimiento:.0%}")
else:
    print(f"INFORME EST-01: SIN DATOS ACTUALES desde hace {antiguedad_s:.0f} s; último dato {ultima['pieza_id']} {ultima['temperatura_c']} °C")
