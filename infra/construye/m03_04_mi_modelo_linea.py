"""Constrúyelo tú (M03-04): tu propio modelo con los datos de tu línea.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m03_04_mi_modelo_linea.py
"""
import pandas as pd
from sklearn.metrics import confusion_matrix
from sklearn.tree import DecisionTreeClassifier, export_text

SENALES = ["temperatura_c", "vibracion_mm_s", "corriente_a"]   # las que mide la estación en vivo

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
PROFUNDIDAD = 3        # cuántas preguntas seguidas puede hacer el árbol

# --- PASO 1: tu dataset y el corte en el tiempo (ya está hecho) --------------
df = pd.read_csv("/data/dataset_linea.csv").sort_values("ts")    # el de M02-04
corte = int(len(df) * 0.7)
entrenar, examen = df.iloc[:corte], df.iloc[corte:]
print(f"carcasas: entrenar={len(entrenar)} examen={len(examen)} defectuosas_en_examen={int(examen['defecto'].sum())}")

# --- PASO 2: entrenar un árbol y leer sus reglas -------------------------------
# (pega aquí el bloque del paso 2)
arbol = DecisionTreeClassifier(max_depth=PROFUNDIDAD, class_weight="balanced", random_state=7)
arbol.fit(entrenar[SENALES], entrenar["defecto"])
print(export_text(arbol, feature_names=SENALES, class_names=["buena", "defectuosa"]))

# --- PASO 3: examinar el modelo ------------------------------------------------
# (pega aquí el bloque del paso 3)
def examinar(modelo, datos=examen):
    tn, fp, fn, tp = confusion_matrix(datos["defecto"], modelo.predict(datos[SENALES]), labels=[0, 1]).ravel()
    return tp, fn, fp, tn

tp, fn, fp, tn = examinar(arbol)
print(f"encontrados={tp} de {tp + fn}  falsas_alarmas={fp} de {fp + tn}")

# --- PASO 4: ¿cuántos datos hacen falta? ---------------------------------------
# (pega aquí el bloque del paso 4)
print("carcasas_para_aprender  defectuosas_entre_ellas  encontrados  falsas_alarmas")
for n in (60, 120, 300, 600, len(entrenar)):
    parte = entrenar.iloc[:n]
    modelo = DecisionTreeClassifier(max_depth=PROFUNDIDAD, class_weight="balanced", random_state=7)
    modelo.fit(parte[SENALES], parte["defecto"])
    tp, fn, fp, tn = examinar(modelo)
    print(f"{n:22d}  {int(parte['defecto'].sum()):23d}  {tp:5d} de {tp + fn}  {fp:7d} de {fp + tn}")

# --- PASO 5: ¿los fallos son del modelo o de la etiqueta? ----------------------
# (pega aquí el bloque del paso 5)
pred = arbol.predict(examen[SENALES])
criterio = ((examen["vibracion_mm_s"] >= 0.265) & (examen["corriente_a"] > 4.08)).astype(int)
discrepan = pred != examen["defecto"]
razon_al_modelo = int((discrepan & (pred == criterio)).sum())
print(f"el árbol y calidad no coinciden en {int(discrepan.sum())} carcasas; en {razon_al_modelo} el criterio da la razón al árbol")

# Reto 1: tres ventanas distintas de 120 carcasas
for inicio in (0, 700, 1400):
    parte = entrenar.iloc[inicio:inicio + 120]
    modelo = DecisionTreeClassifier(max_depth=PROFUNDIDAD, class_weight="balanced", random_state=7)
    modelo.fit(parte[SENALES], parte["defecto"])
    tp, fn, fp, tn = examinar(modelo)
    print(f"carcasas {inicio}-{inicio + 119}: defectuosas={int(parte['defecto'].sum()):2d}  encontrados={tp} de {tp + fn}  falsas_alarmas={fp} de {fp + tn}")

# Reto 2: las carcasas en las que el árbol y calidad no coinciden
tabla = examen.assign(arbol=pred, criterio=criterio)[discrepan]
print(tabla[["pieza_id", "vibracion_mm_s", "corriente_a", "defecto", "arbol", "criterio"]].head(5).to_string(index=False))
