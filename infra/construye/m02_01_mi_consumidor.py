"""Constrúyelo tú (M02-01): tu propio consumidor de telemetría.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m02_01_mi_consumidor.py
"""
import json
import time
from collections import Counter

import paho.mqtt.client as mqtt # type: ignore

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
DURACION_S = 30                              # cuánto tiempo escucha
TEMA_ESTADO = "linea/est01/consumidor/estado"   # donde tu consumidor anuncia si está vivo
DESPEDIRSE = True                           # False = se cae sin avisar; True = se desconecta bien

# --- PASO 1: conectar con el broker (ya está hecho) --------------------------
recibidos = []                               # (tema, hora de llegada, contenido) de cada mensaje

def al_recibir(cliente, datos, mensaje):
    recibidos.append((mensaje.topic, time.time(), mensaje.payload.decode()))

cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cliente.on_message = al_recibir
cliente.connect("mosquitto", 1883)
print("conectado al broker mosquitto:1883")

# --- PASO 2: escuchar todos los temas de la estación ---------------------------
# (pega aquí el bloque del paso 2)
cliente.subscribe("linea/est01/#")               # todos los temas de EST-01
cliente.loop_start()
time.sleep(DURACION_S)
cliente.loop_stop()
cliente.disconnect()
for tema, veces in Counter(t for t, _, _ in recibidos).most_common():
    print(f"{veces:4d} mensajes en {tema}")

# --- PASO 3: medir los silencios entre carcasas --------------------------------
# (pega aquí el bloque del paso 3)
llegadas = [hora for tema, hora, _ in recibidos if tema == "linea/est01/ciclo"]
silencios = [b - a for a, b in zip(llegadas, llegadas[1:])]
grupos = Counter("normal (<1,5 s)" if s < 1.5 else "lento (1,5-3 s)" if s < 3 else "parada (>3 s)"
                 for s in silencios)
print(f"silencio más largo: {max(silencios):.1f} s")
for grupo, veces in grupos.items():
    print(f"  {grupo}: {veces}")

# --- PASO 4: anunciarse con un testamento --------------------------------------
# (pega aquí el bloque del paso 4)
vivo = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mi-consumidor")
# El testamento: el broker lo publicará POR TI si te desconectas sin avisar
vivo.will_set(TEMA_ESTADO, json.dumps({"consumidor": "desconectado"}), qos=1, retain=True)
vivo.connect("mosquitto", 1883, keepalive=5)
vivo.loop_start()
vivo.publish(TEMA_ESTADO, json.dumps({"consumidor": "conectado"}), qos=1, retain=True).wait_for_publish()
print(f"anunciado en {TEMA_ESTADO}: conectado")

# --- PASO 5: caerse sin despedirse ---------------------------------------------
# (pega aquí el bloque del paso 5)
time.sleep(1)
vivo.loop_stop()
if DESPEDIRSE:
    vivo.disconnect()                  # despedida correcta: el broker descarta el testamento
else:
    vivo.socket().close()              # caída: se corta la conexión sin despedirse
time.sleep(2)

oido = []
tarde = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
tarde.on_message = lambda c, d, m: oido.append(m.payload.decode())
tarde.connect("mosquitto", 1883)
tarde.subscribe(TEMA_ESTADO)
tarde.loop_start()
time.sleep(2)
tarde.loop_stop()
print(f"quien llega tarde ve en {TEMA_ESTADO}: {oido}")