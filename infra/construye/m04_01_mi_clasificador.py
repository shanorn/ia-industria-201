"""Constrúyelo tú (M04-01): tu propio clasificador de imágenes.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m04_01_mi_clasificador.py
"""
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LogisticRegression

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
LADO = 16          # la foto se reduce a LADO × LADO puntos antes de dársela al modelo

# --- PASO 1: las fotos (ya está hecho) ---------------------------------------
fotos = pd.read_csv("/data/imagenes/manifiesto.csv")     # una fila por foto: ruta y si es defectuosa
primera = Image.open(fotos["ruta"][0])
print(f"fotos={len(fotos)} defectuosas={int(fotos['defecto'].sum())}  tamaño de cada foto={primera.size}")

# --- PASO 2: convertir una foto en números -------------------------------------
# (pega aquí el bloque del paso 2)
def a_numeros(ruta):
    gris = Image.open(ruta).convert("L").resize((LADO, LADO))     # gris y más pequeña
    return np.asarray(gris, dtype=np.float32) / 255.0             # cada punto: de 0 (negro) a 1 (blanco)

tabla = a_numeros(fotos["ruta"][0])
print(f"una foto son {tabla.shape[0]} × {tabla.shape[1]} = {tabla.size} números")
print("fila central:", np.round(tabla[LADO // 2], 2))

# --- PASO 3: preparar todas las fotos ------------------------------------------
# (pega aquí el bloque del paso 3)
X = np.stack([a_numeros(ruta).reshape(-1) for ruta in fotos["ruta"]])   # cada foto, en una fila
y = fotos["defecto"].to_numpy()
print(f"tabla de entrada: {X.shape[0]} fotos × {X.shape[1]} puntos")

# --- PASO 4: entrenar y examinar -----------------------------------------------
# (pega aquí el bloque del paso 4)
buenas, malas = np.where(y == 0)[0], np.where(y == 1)[0]
n_b, n_m = int(len(buenas) * 0.7), int(len(malas) * 0.7)
ent = np.concatenate([buenas[:n_b], malas[:n_m]])                # 70 % de cada clase
exa = np.concatenate([buenas[n_b:], malas[n_m:]])                # 30 % de cada clase
modelo = LogisticRegression(max_iter=400).fit(X[ent], y[ent])
acierto = (modelo.predict(X[exa]) == y[exa]).mean()
print(f"entrenar={len(ent)} fotos  examen={len(exa)} fotos  acierto en examen={acierto:.2f}")

# --- PASO 5: ver dónde se fija el modelo ---------------------------------------
# (pega aquí el bloque del paso 5)
pesos = modelo.coef_[0].reshape(LADO, LADO)
corte = np.abs(pesos).max() / 3
for fila in pesos:
    print("".join("#" if p > corte else "." if p < -corte else " " for p in fila))

# Reto 1: las fotos malas de entrenamiento se hicieron con más luz
X_luz = X.copy()
malas_ent = ent[y[ent] == 1]
X_luz[malas_ent] = np.clip(X_luz[malas_ent] + 0.15, 0, 1)          # todas las malas, un poco más claras
atajo = LogisticRegression(max_iter=400).fit(X_luz[ent], y[ent])
print(f"con el atajo: acierto en entrenamiento={(atajo.predict(X_luz[ent]) == y[ent]).mean():.2f}  "
      f"en examen (fotos normales)={(atajo.predict(X[exa]) == y[exa]).mean():.2f}")
p = atajo.coef_[0].reshape(LADO, LADO); c = np.abs(p).max() / 3
for fila in p:
    print("".join("#" if v > c else "." if v < -c else " " for v in fila))
