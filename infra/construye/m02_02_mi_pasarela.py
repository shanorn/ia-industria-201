"""Constrúyelo tú (M02-02): tu propia pasarela Modbus → MQTT.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m02_02_mi_pasarela.py
"""
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
# El mapa de registros: qué hay en cada uno y por cuánto hay que dividir
MAPA = {0: ("temperatura_c", 1), 1: ("vibracion_mm_s", 1000), 2: ("corriente_a", 100), 3: ("secuencia", 1)}
PERIODO_S = 1.0        # cada cuánto pregunta la pasarela al autómata
LECTURAS = 10          # cuántas veces pregunta en el bucle del paso 6

# --- Valores originales ------------------------------------------------------
#PERIODO_S = 1.0        # cada cuánto pregunta la pasarela al autómata
#LECTURAS = 10          # cuántas veces pregunta en el bucle del paso 6

# --- PASO 1: conectar con el autómata por Modbus (ya está hecho) -------------
plc = ModbusTcpClient("modbus", port=1502)
print("Modbus conectado:", plc.connect())

# --- PASO 2: leer los registros en crudo ---------------------------------------
# (pega aquí el bloque del paso 2)
def leer_crudo():
    respuesta = plc.read_holding_registers(0, 4, slave=1)      # 4 registros desde el 0
    return respuesta.registers

crudo = leer_crudo()
print("registros 0-3 en crudo:", crudo)

# --- PASO 3: aplicar el mapa de registros --------------------------------------
# (pega aquí el bloque del paso 3)
def interpretar(crudo):
    return {nombre: crudo[registro] / escala for registro, (nombre, escala) in MAPA.items()}

senales = interpretar(crudo)
print("con el mapa:", senales)

# --- PASO 4: comprobar contra el MQTT de la estación ---------------------------
# (pega aquí el bloque del paso 4)
llegado = []
oyente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
oyente.on_message = lambda c, d, m: llegado.append(json.loads(m.payload))
oyente.connect("mosquitto", 1883)
oyente.subscribe("linea/est01/ciclo")
oyente.loop_start()
while not llegado:                       # espera a que llegue una carcasa
    time.sleep(0.1)
oyente.loop_stop()
por_modbus = interpretar(leer_crudo())
print(f"MQTT:   {llegado[0]['pieza_id']}  {llegado[0]['temperatura_c']} °C")
print(f"Modbus: secuencia {por_modbus['secuencia']:.0f}  {por_modbus['temperatura_c']} °C")

# --- PASO 5: publicar en mqtt con nombres y unidades ---------------------------
# (pega aquí el bloque del paso 5)
salida = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
salida.connect("mosquitto", 1883)
salida.loop_start()

def publicar(senales):
    registro = {"fuente": "modbus", "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **senales}
    salida.publish("linea/est01/pasarela", json.dumps(registro)).wait_for_publish()
    return registro

print("publicado:", json.dumps(publicar(por_modbus)))

# --- PASO 6: el bucle de la pasarela -------------------------------------------
# (pega aquí el bloque del paso 6)
publicadas = repetidas = saltadas = 0
ultima = None
for _ in range(LECTURAS):
    senales = interpretar(leer_crudo())
    secuencia = int(senales["secuencia"])
    if secuencia == ultima:
        repetidas += 1                                  # preguntaste y no había nada nuevo
    else:
        if ultima is not None and secuencia > ultima + 1:
            saltadas += secuencia - ultima - 1          # hubo carcasas que no llegaste a leer
        publicar(senales)
        publicadas += 1
        ultima = secuencia
    time.sleep(PERIODO_S)
salida.loop_stop()
print(f"cada {PERIODO_S} s: lecturas={LECTURAS} publicadas={publicadas} repetidas={repetidas} carcasas_saltadas={saltadas}")


# --- RETO 1 --------------------------------------------------------------------
RANGOS = {"temperatura_c": (0, 150), "vibracion_mm_s": (0, 5), "corriente_a": (0, 20)}   # lo físicamente posible

def publicar_si_es_posible(senales):
    for nombre, (minimo, maximo) in RANGOS.items():
        if not minimo <= senales[nombre] <= maximo:
            print(f"RECHAZADO: {nombre}={senales[nombre]} fuera de {minimo}-{maximo}; revisa el mapa de registros")
            return None
    return publicar(senales)

publicar_si_es_posible(interpretar(leer_crudo()))