"""Constrúyelo tú (M07-01): tu propio servicio de inferencia.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m07_01_mi_servicio.py
"""
import hashlib
from datetime import datetime, timezone

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

# --- PASO 1: el modelo que va a servir (ya está hecho) -----------------------
RUTA = "/data/modelo_defecto.joblib"
MODELO = joblib.load(RUTA)
VERSION = open("/data/VERSION").read().strip()                       # la etiqueta que alguien escribió
HUELLA = hashlib.sha256(open(RUTA, "rb").read()).hexdigest()[:12]     # calculada del propio fichero
print(f"servirá el modelo {VERSION} con huella {HUELLA}")

# --- PASO 2: el contrato de entrada --------------------------------------------
# (pega aquí el bloque del paso 2)
class Pieza(BaseModel):
    pieza_id: str
    temperatura_c: float
    vibracion_mm_s: float
    corriente_a: float
    presion_bar: float

print("contrato de entrada:", list(Pieza.model_fields))

# --- PASO 3: la salud del servicio ---------------------------------------------
# (pega aquí el bloque del paso 3)
app = FastAPI(title="mi servicio de inferencia")

@app.get("/salud")
def salud():
    return {"estado": "ok", "version": VERSION, "huella_modelo": HUELLA}

print("direcciones del servicio:", [r.path for r in app.routes if r.path in ("/salud", "/predecir")])

# --- PASO 4: el dictamen -------------------------------------------------------
# (pega aquí el bloque del paso 4)
@app.post("/predecir")
def predecir(pieza: Pieza):
    fila = pd.DataFrame([pieza.model_dump(exclude={"pieza_id"})])
    p = float(MODELO.predict_proba(fila)[0, 1])
    return {"pieza_id": pieza.pieza_id, "dictamen": "revisar" if p >= 0.5 else "seguir", "probabilidad": round(p, 3),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version": VERSION, "huella_modelo": HUELLA}

print("direcciones del servicio:", [r.path for r in app.routes if r.path in ("/salud", "/predecir")])

# --- PASO 5: llamarlo como un cliente ------------------------------------------
# (pega aquí el bloque del paso 5)
cliente = TestClient(app)
print("GET /salud ->", cliente.get("/salud").json())
pieza = pd.read_csv("/data/limpio.csv").iloc[0]
cuerpo = {"pieza_id": pieza["pieza_id"], **{c: float(pieza[c]) for c in ["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]}}
r = cliente.post("/predecir", json=cuerpo)
print(f"POST /predecir -> HTTP {r.status_code}", r.json())

# Una pieza con el sensor de temperatura clavado
falsa = {**cuerpo, "pieza_id": "CLAVADO", "temperatura_c": 9999}
r = cliente.post("/predecir", json=falsa)
print(f"9999 °C -> HTTP {r.status_code}", r.json())