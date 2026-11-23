"""Constrúyelo tú (M05-05): tu propio buscador por significado (embeddings).

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m05_05_mi_buscador.py
"""
import re

import numpy as np
from llama_cpp import Llama

from linea.cli import _Silencio            # calla los mensajes internos de llama.cpp

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
PREGUNTA = "¿De qué color es el tornillo de recambio?"
MINIMO_PARECIDO = 0.4                      # parecido mínimo para dar un párrafo por bueno (0 = cualquiera)

# --- PASO 1: el modelo de embeddings y su licencia (ya está hecho) -----------
with _Silencio():
    modelo = Llama(model_path="/modelos/qwen3-embedding-0.6b-q8_0.gguf", embedding=True, n_ctx=512, verbose=False)
print(f"modelo: {modelo.metadata.get('general.name')}  licencia (escrita en el propio fichero): {modelo.metadata.get('general.license')}")

# --- PASO 2: un texto convertido en números ------------------------------------
# (pega aquí el bloque del paso 2)
def embedding(texto):
    with _Silencio():
        v = np.array(modelo.embed(texto))
    v = v if v.ndim == 1 else v[-1]          # un vector por texto
    return v / np.linalg.norm(v)              # longitud 1: así el parecido va de -1 a 1

e = embedding(PREGUNTA)
print(f"la pregunta es ahora una lista de {len(e)} números: {np.round(e[:5], 3)} ...")

# --- PASO 3: los párrafos del procedimiento, en números ------------------------
# (pega aquí el bloque del paso 3)
documento = open("/opt/linea/docs/procedimiento-est01.md", encoding="utf-8").read()
parrafos = [p.strip() for p in documento.split("\n\n") if p.strip() and not p.startswith("#")]
vectores = np.array([embedding(p) for p in parrafos])
print(f"{len(parrafos)} párrafos convertidos: una tabla de {vectores.shape[0]} × {vectores.shape[1]} números")

# --- PASO 4: buscar por significado --------------------------------------------
# (pega aquí el bloque del paso 4)
def buscar(pregunta):
    parecidos = vectores @ embedding(pregunta)          # un parecido por párrafo
    mejor = int(np.argmax(parecidos))
    return parrafos[mejor], float(parecidos[mejor])

parrafo, parecido = buscar(PREGUNTA)
print(f"por significado (parecido {parecido:.2f}): {parrafo[:90]}")

# --- PASO 5: comparar con la búsqueda por palabras -----------------------------
# (pega aquí el bloque del paso 5)
VACIAS = {"a", "al", "de", "del", "el", "la", "las", "los", "un", "una", "y", "o", "en", "se", "que",
          "qué", "es", "por", "para", "con", "cómo", "cuánto", "cuál", "antes"}

def palabras(t):
    return set(re.findall(r"[a-záéíóúñ0-9]+", t.lower())) - VACIAS

comunes = [len(palabras(p) & palabras(PREGUNTA)) for p in parrafos]
mejor = int(np.argmax(comunes))
print(f"por palabras ({comunes[mejor]} en común): {parrafos[mejor][:90]}")

# Si ni el mejor párrafo se parece lo suficiente, no hay respuesta en el documento
print("asistente:", "el procedimiento no dice nada sobre eso" if parecido < MINIMO_PARECIDO else parrafo)
