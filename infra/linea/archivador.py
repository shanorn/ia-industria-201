"""Almacén: cada ciclo MQTT queda en SQLite."""
import json
import sqlite3
import time

import paho.mqtt.client as mqtt

from linea.config import DATA, MQTT_HOST, MQTT_PORT, TOPIC_CICLO
from linea.metricas import Metricas


def conectar_db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATA / "historial.sqlite")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lecturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pieza_id TEXT,
            ts TEXT,
            temperatura_c REAL,
            vibracion_mm_s REAL,
            corriente_a REAL,
            payload TEXT
        )
        """
    )
    # Históricos creados antes de existir el tiempo de ciclo: se añade la columna
    columnas = [fila[1] for fila in con.execute("PRAGMA table_info(lecturas)")]
    if "tiempo_ciclo_s" not in columnas:
        con.execute("ALTER TABLE lecturas ADD COLUMN tiempo_ciclo_s REAL")
    con.commit()
    return con


def main() -> None:
    con = conectar_db()

    # Métricas para Prometheus en http://archivador:9101/metrics
    metricas = Metricas()
    metricas.definir("archivador_registros_guardados_total", "counter", "Registros guardados en el histórico desde que arrancó el archivador")
    metricas.definir("archivador_ultimo_registro_timestamp_seconds", "gauge", "Hora (epoch) en que se guardó el último registro")
    metricas.servir(9101)

    def on_message(_client, _userdata, msg):
        estado = json.loads(msg.payload.decode())
        con.execute(
            "INSERT INTO lecturas (pieza_id, ts, temperatura_c, vibracion_mm_s, corriente_a, tiempo_ciclo_s, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                estado.get("pieza_id"),
                estado.get("ts"),
                estado.get("temperatura_c"),
                estado.get("vibracion_mm_s"),
                estado.get("corriente_a"),
                estado.get("tiempo_ciclo_s"),
                msg.payload.decode(),
            ),
        )
        con.commit()
        metricas.sumar("archivador_registros_guardados_total")
        metricas.poner("archivador_ultimo_registro_timestamp_seconds", time.time())
        print(f"archivador: {estado.get('pieza_id')}", flush=True)

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="archivador-est01")
    cliente.on_message = on_message

    # Suscribirse cada vez que se conecta, también tras una reconexión
    def on_connect(client, _userdata, _flags, _reason, _properties):
       client.subscribe(TOPIC_CICLO)
       print("archivador: suscrito a", TOPIC_CICLO, flush=True)

    cliente.on_connect = on_connect

    while True:
        try:
            cliente.connect(MQTT_HOST, MQTT_PORT, 30)
            break
        except Exception as exc:
            print(f"archivador: esperando al broker ({exc})", flush=True)
            time.sleep(1)
    cliente.subscribe(TOPIC_CICLO)
    cliente.loop_forever()


if __name__ == "__main__":
    main()
