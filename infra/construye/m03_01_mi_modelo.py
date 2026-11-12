"""Constrúyelo tú (M03-01): tu propio modelo de predicción de defectos.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m03_01_mi_modelo.py
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
# Señales que usará el modelo. Las cuatro las mide la estación durante el ciclo.
SENALES = ["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]
# SENALES = ["vibracion_mm_s", "corriente_a", "presion_bar"]

COSTE_ESCAPADO = 500   # € por defecto que llega al cliente
COSTE_REVISION = 5     # € por revisar a mano una pieza buena

# --- PASO 1: cargar los datos (ya está hecho) --------------------------------
df = pd.read_csv("/data/limpio.csv")   # en tu equipo: infra/data/limpio.csv
print(f"piezas={len(df)} defectuosas={int(df['defecto'].sum())} señales={SENALES}")

# --- PASO 2: partir en pasado y futuro ---------------------------------------
# (pega aquí el bloque del paso 2)
df = df.sort_values("pieza_id")           # ordena las piezas en el orden en que se fabricaron
corte = int(len(df) * 0.7)                # la fila donde acaba el 70 % más antiguo
entrenar = df.iloc[:corte]                # el pasado: con esto aprende el modelo
examen = df.iloc[corte:]                  # el futuro: piezas que el modelo no verá al aprender
print(f"entrenar={len(entrenar)} examen={len(examen)} defectos_en_examen={int(examen['defecto'].sum())}")

# --- PASO 3: entrenar --------------------------------------------------------
# (pega aquí el bloque del paso 3)
# Crea el modelo: "balanced" da más peso a la clase rara (defecto)
modelo = LogisticRegression(class_weight="balanced", max_iter=400)

# Entrena: busca un peso por señal que relacione las señales con la columna defecto
modelo.fit(entrenar[SENALES], entrenar["defecto"])

# Enseña lo que ha aprendido: un peso por señal y un término independiente
for senal, peso in zip(SENALES, modelo.coef_[0]):
    print(f"peso {senal:15s} {peso:+.3f}")
print(f"término independiente  {modelo.intercept_[0]:+.3f}")

# --- PASO 4: ver qué probabilidad da a cada pieza ----------------------------
# (pega aquí el bloque del paso 4)
# Probabilidad de defecto (de 0 a 1) para cada pieza de examen
examen = examen.assign(probabilidad=modelo.predict_proba(examen[SENALES])[:, 1])

# Las 3 piezas que el modelo ve más sospechosas y las 3 que ve más seguras
columnas = ["pieza_id", "temperatura_c", "probabilidad", "defecto"]
print(examen.sort_values("probabilidad", ascending=False)[columnas].head(3).round(3).to_string(index=False))
print(examen.sort_values("probabilidad")[columnas].head(3).round(3).to_string(index=False))

# --- PASO 5: decidir con un umbral y contar los aciertos y errores -----------
# (pega aquí el bloque del paso 5)
def evaluar(umbral):
    """Decide con un umbral y cuenta los cuatro casos sobre las piezas de examen."""
    decision = (examen["probabilidad"] >= umbral).astype(int)   # 1 = «mándala a revisar»
    tn, fp, fn, tp = confusion_matrix(examen["defecto"], decision, labels=[0, 1]).ravel()
    return int(tp), int(fp), int(fn), int(tn)

tp, fp, fn, tn = evaluar(0.5)
print(f"umbral 0.5 -> encontrados={tp} escapados={fn} falsas_alarmas={fp} correctas={tn}")

# --- PASO 6: elegir el umbral por lo que cuesta -------------------------------
# (pega aquí el bloque del paso 6)
print("umbral  escapados  falsas_alarmas  coste")
mejor = None
for i in range(1, 20):                                     # umbrales 0.05, 0.10 … 0.95
    umbral = round(i * 0.05, 2)
    tp, fp, fn, tn = evaluar(umbral)
    coste = COSTE_ESCAPADO * fn + COSTE_REVISION * fp      # lo que cuestan los errores
    print(f"{umbral:6.2f}  {fn:9d}  {fp:14d}  {coste:5d} €")
    if mejor is None or coste < mejor[1]:                  # guarda el más barato
        mejor = (umbral, coste)

buenas = int((examen["defecto"] == 0).sum())
revisar_todo = COSTE_REVISION * buenas                     # sin modelo: se revisa todo a mano
print(f"mejor umbral={mejor[0]} coste={mejor[1]} € | revisar todo={revisar_todo} €")