"""Constrúyelo tú (M03-02): tu propio detector de anomalías.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m03_02_mi_detector.py
"""
import numpy as np
from linea.datos import generar_limpio, vigilancia   # los mismos generadores que usa lab m03-02

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
SENALES = ["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]
UMBRAL = 13.3                 # distancia a partir de la cual se avisa
VIBRACION_AVERIA = None     # None = la avería del lab (vibración ~1,3 mm/s); un número = otra avería
CICLOS_POR_TURNO = 8 * 3600   # un ciclo por segundo durante un turno de 8 h

# --- PASO 1: los ciclos (ya está hecho) --------------------------------------
base = generar_limpio(400, seed=3)
normal = base[base["defecto"] == 0]                   # solo ciclos sanos: con esto aprende
vig = vigilancia()                                    # 200 ciclos nuevos que hay que vigilar
if VIBRACION_AVERIA is not None:                    # otra avería: cambia la vibración de las 20 averías simuladas
    vig.loc[vig["averia_simulada"] == 1, "vibracion_mm_s"] = VIBRACION_AVERIA
averia = vig["averia_simulada"] == 1                      # la marca: solo se usa para contar al final
print(f"ciclos normales para aprender={len(normal)} ciclos a vigilar={len(vig)} averias_simuladas={int(averia.sum())}")

# --- PASO 2: aprender cómo es lo normal --------------------------------------
# (pega aquí el bloque del paso 2)
media = normal[SENALES].mean()                        # el valor habitual de cada señal
desviacion = normal[SENALES].std(ddof=0)              # cuánto varía cada señal normalmente
print("señal            media  desviación")
for senal in SENALES:
    print(f"{senal:15s} {media[senal]:6.3f}  {desviacion[senal]:6.3f}")

# --- PASO 3: un detector sencillo, señal a señal -----------------------------
# (pega aquí el bloque del paso 3)
# z = a cuántas desviaciones está cada señal de su media (0 = justo en la media)
z_vig = (vig[SENALES] - media) / desviacion

# Regla sencilla: avisa si ALGUNA señal está a más de 3 desviaciones de su media
aviso_simple = (z_vig.abs() > 3).any(axis=1)
print(f"señal a señal: averías avisadas={int((aviso_simple & averia).sum())} de {int(averia.sum())}"
      f"  falsas alarmas={int((aviso_simple & ~averia).sum())} de {int((~averia).sum())}")

# --- PASO 4: la distancia, con todas las señales a la vez --------------------
# (pega aquí el bloque del paso 4)
# Pasa los ciclos normales a la misma escala (z) y mide cómo varían juntas las señales
z_normal = (normal[SENALES] - media) / desviacion
covarianza = np.cov(z_normal.T, bias=True)            # tabla 4×4: cuánto se mueve cada señal con las otras
inversa = np.linalg.inv(covarianza)

# Distancia de Mahalanobis (al cuadrado) de cada ciclo a «lo normal»
z = z_vig.to_numpy()
vig["distancia"] = ((z @ inversa) * z).sum(axis=1)

columnas = ["pieza_id", "vibracion_mm_s", "distancia", "averia_simulada"]
print(vig[columnas].head(3).round(3).to_string(index=False))    # tres normales
print(vig[columnas].tail(3).round(3).to_string(index=False))    # tres con avería simulada

# --- PASO 5: avisar con un umbral y contar ------------------------------------
# (pega aquí el bloque del paso 5)
aviso = vig["distancia"] >= UMBRAL
avisados = int((aviso & averia).sum())
falsas = int((aviso & ~averia).sum())
print(f"umbral={UMBRAL}: averías avisadas={avisados} de {int(averia.sum())}  falsas alarmas={falsas} de {int((~averia).sum())}")

# --- PASO 6: un ciclo raro en conjunto ----------------------------------------
# (pega aquí el bloque del paso 6)
# Un ciclo inventado: cada señal 2,5 desviaciones por encima de su media.
# Ninguna pasa de 3 por sí sola, pero las cuatro están altas a la vez.
raro = media + 2.5 * desviacion
z_raro = ((raro - media) / desviacion).to_numpy()
print(f"ciclo raro: {raro.round(3).to_dict()}")
print(f"  señal a señal avisa: {bool((np.abs(z_raro) > 3).any())}")
print(f"  distancia={float(z_raro @ inversa @ z_raro):.1f} -> avisa: {float(z_raro @ inversa @ z_raro) >= UMBRAL}")

# --- PASO 7: cuántos avisos daría en un turno ---------------------------------
# (pega aquí el bloque del paso 7)
tasa_falsas = falsas / int((~averia).sum())          # fracción de ciclos normales que dan aviso
print(f"falsas alarmas: {tasa_falsas:.1%} de los ciclos normales -> ~{tasa_falsas * CICLOS_POR_TURNO:.0f} avisos falsos por turno")