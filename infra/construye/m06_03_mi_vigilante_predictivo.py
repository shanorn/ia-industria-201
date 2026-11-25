"""Constrúyelo tú (M06-03): tu propio vigilante predictivo.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m06_03_mi_vigilante_predictivo.py
"""
import time

import httpx
import numpy as np

METRICA = "estacion_temperatura_husillo_celsius"
LIMITE_ALERTA = 70.0           # la alerta TemperaturaHusilloAlta de Prometheus

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
APRENDER_MIN = 10              # minutos de histórico sano con los que se aprende lo normal
VIGILAR_S = 150                 # cuánto vigila en el paso 5
VENTANA_S = 120                # con cuántos segundos recientes se calcula la subida

# --- PASO 1: pedir a Prometheus un tramo de la serie (ya está hecho) ---------
def serie(minutos, metrica=METRICA):
    """Devuelve (segundos, valores) de los últimos `minutos`, una muestra cada 5 s."""
    fin = time.time()
    r = httpx.get("http://prometheus:9090/api/v1/query_range",
                  params={"query": metrica, "start": fin - minutos * 60, "end": fin, "step": 5}, timeout=10)
    puntos = r.json()["data"]["result"][0]["values"]
    return np.array([float(t) for t, _ in puntos]), np.array([float(v) for _, v in puntos])

t, temp = serie(APRENDER_MIN)
print(f"{len(temp)} muestras de los últimos {APRENDER_MIN} min: mínima={temp.min():.2f} media={temp.mean():.2f} máxima={temp.max():.2f} °C")

# --- PASO 2: hasta dónde llega lo normal ---------------------------------------
# (pega aquí el bloque del paso 2)
sanas = temp[temp > 40]                           # fuera las muestras con la estación parada
limite_normal = np.percentile(sanas, 99.5)
print(f"lo normal llega hasta {limite_normal:.2f} °C (percentil 99,5 de {len(sanas)} muestras)")

# --- PASO 3: cuánto sube normalmente -------------------------------------------
# (pega aquí el bloque del paso 3)
def subida(ts, valores):
    """Pendiente de la recta que mejor ajusta los valores, en °C por minuto."""
    return np.polyfit(ts - ts[0], valores, 1)[0] * 60

n = VENTANA_S // 5                                  # muestras por ventana
pendientes = [subida(t[i:i + n], temp[i:i + n]) for i in range(0, len(temp) - n) if temp[i:i + n].min() > 40]
subida_max = np.percentile(pendientes, 99.5)
print(f"subida máxima normal: {subida_max:.2f} °C/min (de {len(pendientes)} ventanas de {VENTANA_S} s)")

# --- PASO 4: prever cuánto falta para la alerta --------------------------------
# (pega aquí el bloque del paso 4)
def prever():
    ts, v = serie(VENTANA_S / 60)
    ahora, ritmo = v[-1], subida(ts, v)
    minutos = (LIMITE_ALERTA - ahora) / ritmo if ritmo > 0 else None
    return ahora, ritmo, minutos

ahora, ritmo, minutos = prever()
print(f"ahora {ahora:.2f} °C, subida {ritmo:+.2f} °C/min, " +
      (f"llegaría a 70 °C en {minutos:.0f} min" if minutos else "no sube: no llegará"))

# --- PASO 5: vigilar en modo asistido ------------------------------------------
# (pega aquí el bloque del paso 5)
print("hora      temp    subida/min  previsión")
inicio = time.time()
while time.time() - inicio < VIGILAR_S:
    ahora, ritmo, minutos = prever()
    if ahora > limite_normal and ritmo > subida_max:
        aviso = f"PROPUESTA: subir refrigeración a 3 (70 °C en ~{minutos:.1f} min). La decide el operario."
    else:
        aviso = "normal"
    print(f"{time.strftime('%H:%M:%S')}  {ahora:6.2f}  {ritmo:+10.2f}  {aviso}")
    time.sleep(10)