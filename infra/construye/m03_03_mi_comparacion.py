"""Constrúyelo tú (M03-03): tu propia comparación de modelos.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m03_03_mi_comparacion.py
"""
import json

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier      # arriba, con los demás import

SENALES = ["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]
VERSION = "defecto-0.2"     # el nombre con el que quedará el elegido

# --- PASO 1: los datos y el corte de siempre (ya está hecho) -----------------
df = pd.read_csv("/data/limpio.csv").sort_values("pieza_id")
corte = int(len(df) * 0.7)
entrenar, examen = df.iloc[:corte], df.iloc[corte:]     # el mismo corte del M03-01

def examinar(modelo):
    """Entrena con el pasado, examina con el futuro y devuelve encontrados, escapados y falsas alarmas."""
    modelo.fit(entrenar[SENALES], entrenar["defecto"])
    tn, fp, fn, tp = confusion_matrix(examen["defecto"], modelo.predict(examen[SENALES]), labels=[0, 1]).ravel()
    return {"recall": tp / (tp + fn), "fpr": fp / (fp + tn), "encontrados": int(tp), "falsas": int(fp)}

print(f"entrenar={len(entrenar)} examen={len(examen)} defectos_en_examen={int(examen['defecto'].sum())}")

# --- PASO 2: escribir la regla antes de mirar ----------------------------------
# (pega aquí el bloque del paso 2)
REGLA = "más defectos encontrados; si empatan, menos falsas alarmas"

def clave(resultado):
    return (resultado["recall"], -resultado["fpr"])     # Python compara la tupla de izquierda a derecha

print(f"regla de elección: {REGLA}")



# --- PASO 3: los candidatos ----------------------------------------------------
# (pega aquí el bloque del paso 3)
candidatos = {
    "logreg": LogisticRegression(class_weight="balanced", max_iter=400),
    "arbol": DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=7),
    "red": make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=0)),
    "red128": make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(256, 128), max_iter=4000, random_state=0)),
    "bosque": RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=0),
    "bosqueDoble": RandomForestClassifier(n_estimators=400, class_weight="balanced", random_state=0),
    "bosqueDobleRandom": RandomForestClassifier(n_estimators=1000, class_weight="balanced", random_state=1),
}
print(f"candidatos: {list(candidatos)}")

# --- PASO 4: examinarlos con la misma vara -------------------------------------
# (pega aquí el bloque del paso 4)
resultados = {nombre: examinar(modelo) for nombre, modelo in candidatos.items()}
print("candidato  encontrados  falsas_alarmas")
for nombre, r in resultados.items():
    print(f"{nombre:9s}  {r['encontrados']:5d} de 21  {r['falsas']:6d} de 210")

# --- PASO 5: elegir con la regla y guardar -------------------------------------
# (pega aquí el bloque del paso 5)
ganador = max(resultados, key=lambda nombre: clave(resultados[nombre]))
joblib.dump(candidatos[ganador], "/data/mi_modelo.joblib")
ficha = {"modelo": ganador, "version": VERSION, "regla": REGLA, **resultados[ganador]}
with open("/data/mi_modelo.json", "w") as f:
    json.dump(ficha, f, indent=1)
print(f"elegido: {ganador} -> mi_modelo.joblib, ficha en mi_modelo.json")

# ------------- REGLA 2 ---------------------------------------------------------
REGLA_2 = "más defectos encontrados; si empatan, el que se puede explicar; después, menos falsas alarmas"
EXPLICABLE = {"logreg": True, "arbol": True, "red": False, "bosque": False, "red128": False, "bosqueDoble": False, "bosqueDobleRandom":False}

def clave_explicable(nombre):
    r = resultados[nombre]
    return (r["recall"], EXPLICABLE[nombre], -r["fpr"])

print(f"con la regla «{REGLA_2}»: elegido {max(resultados, key=clave_explicable)}")