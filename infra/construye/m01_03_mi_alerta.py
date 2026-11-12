"""Constrúyelo tú (M01-03): tu propia alerta.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m01_03_mi_alerta.py
"""
import time

import httpx

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
LIMITE_S = 15          # segundos sin guardar a partir de los que algo va mal
FOR_S = 5              # cuánto tiempo seguido tiene que cumplirse para disparar
VIGILAR_S = 30         # cuánto tiempo vigila tu alerta
CADA_S = 5             # cada cuánto pregunta (lo mismo que tarda Prometheus en recoger)

# --- PASO 1: preguntar a Prometheus (ya está hecho) --------------------------
def consultar(promql):
    """Hace una consulta PromQL instantánea y devuelve [(etiquetas, valor), ...]."""
    r = httpx.get("http://prometheus:9090/api/v1/query", params={"query": promql}, timeout=5)
    return [(s["metric"], float(s["value"][1])) for s in r.json()["data"]["result"]]

print("servicios que vigila Prometheus:", consultar("count(up)"))

# --- PASO 2: ¿está vivo cada servicio? -----------------------------------------
for etiquetas, valor in consultar("up"):
    print(f"vivo {etiquetas['job']:11s} = {valor:.0f}")

# --- PASO 3: ¿hace su trabajo el archivador? -----------------------------------
def segundos_sin_guardar():
    resultado = consultar("time() - archivador_ultimo_registro_timestamp_seconds")
    return resultado[0][1]

print(f"segundos sin guardar: {segundos_sin_guardar():.1f}")

# --- PASO 4: ¿se pierden carcasas? ---------------------------------------------
fabricadas = consultar("sum(increase(estacion_piezas_fabricadas_total[1m]))")[0][1]
guardadas = consultar("sum(increase(archivador_registros_guardados_total[1m]))")[0][1]
print(f"último minuto: fabricadas={fabricadas:.0f} guardadas={guardadas:.0f} diferencia={fabricadas - guardadas:.0f}")


# --- PASO 5: una alerta con su tiempo for --------------------------------------
estado, desde = "normal", None
inicio = time.time()
while time.time() - inicio < VIGILAR_S:
    valor = segundos_sin_guardar()
    if valor > LIMITE_S:
        desde = desde or time.time()                     # cuándo empezó a cumplirse
        estado = "disparada" if time.time() - desde >= FOR_S else "pendiente"
    else:
        estado, desde = "normal", None
    print(f"{time.strftime('%H:%M:%S')}  sin guardar={valor:5.1f} s  alerta={estado}")
    time.sleep(CADA_S)
