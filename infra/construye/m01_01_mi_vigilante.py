"""Constrúyelo tú (M01-01): tu propio vigilante del flujo de datos.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m01_01_mi_vigilante.py
"""
import json
import time

import paho.mqtt.client as mqtt

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
DURACION_S = 180        # cuántos segundos escucha el vigilante
PARADA_S = 2.5         # segundos sin carcasa a partir de los que se considera una parada

# --- PASO 1: conectar con el broker (ya está hecho) --------------------------
recibidos = []                                   # cada registro que llegue, con la hora a la que llegó

def al_recibir(cliente, datos, mensaje):
    """La llama paho cada vez que llega un mensaje de un tema al que estás suscrito."""
    recibidos.append((time.time(), json.loads(mensaje.payload)))

cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cliente.on_message = al_recibir
cliente.connect("mosquitto", 1883)               # el broker, por su nombre en la red de Docker
print("conectado al broker mosquitto:1883")

# --- PASO 2: suscribirse y escuchar --------------------------------------------
cliente.subscribe("linea/est01/ciclo")          # a partir de aquí el broker te reenvía cada carcasa
cliente.loop_start()                             # paho recibe en segundo plano
time.sleep(DURACION_S)                           # escuchas durante DURACION_S segundos
cliente.loop_stop()
cliente.disconnect()
print(f"registros recibidos en {DURACION_S} s: {len(recibidos)}")
print("primer registro:", json.dumps(recibidos[0][1], ensure_ascii=False))

# --- PASO 3: leer los campos de cada registro ----------------------------------
print("pieza  secuencia  tiempo_ciclo_s")
for _, registro in recibidos[:3]:                # los tres primeros; el _ es la hora de llegada, que aquí no usas
    print(f"{registro['pieza_id']}  {registro['secuencia']:9d}  {registro['tiempo_ciclo_s']:14.2f}")

# --- PASO 4: detectar carcasas que faltan y reinicios --------------------------
huecos = reinicios = 0
for (_, anterior), (_, actual) in zip(recibidos, recibidos[1:]):     # cada registro con el siguiente
    salto = actual["secuencia"] - anterior["secuencia"]
    if salto > 1:
        huecos += 1
        print(f"FALTAN {salto - 1} carcasas entre {anterior['pieza_id']} y {actual['pieza_id']}")
    elif salto < 1:
        reinicios += 1
        print(f"REINICIO: después de {anterior['pieza_id']} llega {actual['pieza_id']}")
print(f"huecos={huecos} reinicios={reinicios}")

# --- PASO 5: distinguir una parada de una pérdida ------------------------------
paradas = 0
for (llegada_ant, anterior), (llegada, actual) in zip(recibidos, recibidos[1:]):
    silencio = llegada - llegada_ant
    if silencio > PARADA_S and actual["secuencia"] == anterior["secuencia"] + 1:
        paradas += 1
        print(f"PARADA de {silencio:.1f} s antes de {actual['pieza_id']} (sin carcasas perdidas)")
print(f"paradas={paradas}")

# --- PASO 6: conciliar lo fabricado con lo recibido ----------------------------
fabricadas = recibidos[-1][1]["secuencia"] - recibidos[0][1]["secuencia"] + 1
if reinicios:
    print("conciliación: no se puede, la estación se reinició mientras escuchabas")
else:
    print(f"conciliación: fabricadas={fabricadas} recibidas={len(recibidos)} sin_registro={fabricadas - len(recibidos)}")
