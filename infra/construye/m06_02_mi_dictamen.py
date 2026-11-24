"""Constrúyelo tú (M06-02): tu propio publicador de dictámenes.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m06_02_mi_dictamen.py
"""
import hashlib
import json
import time
from datetime import datetime, timezone

import joblib
import pandas as pd
import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient

from linea.estado import leer                      # la última carcasa que publicó la estación

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
UMBRAL = 0.5            # probabilidad a partir de la cual el dictamen es «revisar»
PRESION_BAR = 6.0       # la presión no viaja en el registro de la estación: se supone la nominal
CARCASAS = 5            # cuántas carcasas seguidas dictamina en el paso 6

# --- PASO 1: el modelo y sus credenciales (ya está hecho) --------------------
RUTA = "/data/modelo_defecto.joblib"
modelo = joblib.load(RUTA)
VERSION = open("/data/VERSION").read().strip()
HUELLA = hashlib.sha256(open(RUTA, "rb").read()).hexdigest()[:12]
print(f"modelo {VERSION}, huella {HUELLA}")

# --- PASO 2: decidir sobre la carcasa actual -----------------------------------
# (pega aquí el bloque del paso 2)
def dictaminar():
    e = leer()
    fila = pd.DataFrame([{"temperatura_c": e["temperatura_c"], "vibracion_mm_s": e["vibracion_mm_s"],
                          "corriente_a": e["corriente_a"], "presion_bar": PRESION_BAR}])
    p = float(modelo.predict_proba(fila)[0, 1])
    return {"pieza_id": e["pieza_id"], "decision": "revisar" if p >= UMBRAL else "seguir", "probabilidad": round(p, 3),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version": VERSION, "huella": HUELLA}

dictamen = dictaminar()
print("dictamen:", json.dumps(dictamen))

# --- PASO 3: publicarlo para el automatismo ------------------------------------
# (pega aquí el bloque del paso 3)
recibidos = []
cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cliente.on_message = lambda c, d, m: recibidos.append(json.loads(m.payload))
cliente.connect("mosquitto", 1883)
cliente.subscribe("linea/est01/dictamen")
cliente.loop_start()
time.sleep(0.5)

def publicar(d):
    cliente.publish("linea/est01/dictamen", json.dumps(d)).wait_for_publish()

publicar(dictamen)
time.sleep(0.5)
print(f"recibido en linea/est01/dictamen: {recibidos[-1]['pieza_id']} -> {recibidos[-1]['decision']}")

# --- PASO 4: comprobar que el paro no se ha tocado -----------------------------
# (pega aquí el bloque del paso 4)
plc = ModbusTcpClient("modbus", port=1502)
plc.connect()
paro = plc.read_holding_registers(10, 1, slave=1).registers[0]
plc.close()
print(f"registro de paro de seguridad = {paro}", "(sin tocar)" if paro == 0 else "(¡CAMBIADO!)")

# --- PASO 5: dictaminar carcasas seguidas --------------------------------------
# (pega aquí el bloque del paso 5)
hechas = {dictamen["pieza_id"]}
while len(hechas) < CARCASAS + 1:
    d = dictaminar()
    if d["pieza_id"] not in hechas:                  # una carcasa nueva
        publicar(d)
        hechas.add(d["pieza_id"])
        print(f"{d['pieza_id']}: {d['decision']:7s} probabilidad={d['probabilidad']}")
    time.sleep(0.3)
cliente.loop_stop()
print(f"dictámenes publicados en esta ejecución: {len(recibidos)}")

# Reto 1: el automatismo comprueba cada dictamen antes de hacerle caso
def coherente(d):
    if d.get("huella") != HUELLA:
        return "NO: el modelo no es el instalado"
    esperada = "revisar" if d["probabilidad"] >= UMBRAL else "seguir"
    return "sí" if d["decision"] == esperada else f"NO: con {d['probabilidad']} tocaba {esperada}"

recibidos.clear()
cliente.loop_start()
publicar(dictaminar())                                  # un dictamen legítimo, de tu modelo
time.sleep(15)                                          # mientras, publica el dictamen falso en otra terminal
cliente.loop_stop()
for d in recibidos:
    print(f"{d['pieza_id']}: {d['decision']:7s} p={d['probabilidad']}  ¿coherente? {coherente(d)}")