# M05-05 — Elegir y servir un modelo abierto en planta

[← Página anterior](M05-04-agentes.md) · [Siguiente página →](M05-06-agentes-n8n.md)

> Práctica del módulo. La teoría y la demostración están en el [README del módulo](README.md).
>
> Lanza los comandos desde la carpeta `infra/` del repositorio. Un paso que cuadra termina con una línea que empieza por `OK`.

### Objetivo

Comprender qué es **elegir un [modelo abierto](../glosario/06-modelos-abiertos.md#mapa) para la planta**: qué tipos de modelo existen y para qué sirve cada uno, cómo debe compararse con preguntas y equipos reales, qué límites ponen la memoria y la [licencia](../glosario/06-modelos-abiertos.md#licencias), y cómo se mejora una búsqueda con un modelo de [embeddings](../glosario/06-modelos-abiertos.md#comparacion-tipos).

### Prerrequisitos

- El modelo del M05-01 en `infra/modelos/` y unos **1,7 GB libres** para dos modelos más (paso 1).
- CPU; unos 2 GB de memoria para el contenedor `lab`. No hace falta tener el contenedor `llm` en marcha: este lab carga los modelos directamente.
- Antes, lee la hoja de modelos abiertos del glosario: el mapa de tipos, las licencias y los formatos.

### Qué está pasando

Un integrador pide preparar en un servidor de la planta varios modelos abiertos, cada uno para una cosa: uno grande para informes, otro para resúmenes y chat, uno de **embeddings para búsqueda semántica** y dos de voz a texto. Es el caso real de la hoja de modelos abiertos.

Aquí no hay un servidor con GPU, pero sí se puede hacer lo mismo en pequeño, que es como se decide en la práctica: **descargar dos candidatos, leer su licencia, medirlos en el equipo donde van a correr y con las preguntas de la planta**, y elegir. Vas a comparar el modelo de 0,5 B del curso con uno de 1,5 B de la misma familia, y vas a añadir un tercer tipo de modelo, uno de embeddings, que no redacta: sirve para encontrar el párrafo que contesta a una pregunta aunque el técnico no use las palabras del procedimiento.

| Modelo | Tipo | Para qué en este lab |
|--------|------|----------------------|
| Qwen2.5 0.5B Instruct (Q4) | [LLM](../glosario/04-ia-generativa.md#llm) pequeño | El que ya usa el curso |
| Qwen2.5 1.5B Instruct (Q4) | LLM pequeño, tres veces más grande | El candidato a sustituirlo |
| Qwen3-Embedding 0.6B (Q8) | Embeddings | Buscar por significado en el procedimiento |

### 1 — Descargar dos modelos abiertos

**Qué ocurre:** descargas los dos modelos nuevos de Hugging Face, el sitio donde los fabricantes publican sus modelos abiertos, a `infra/modelos/`, junto al del curso. Son ficheros [GGUF](../glosario/04-ia-generativa.md#cuantizacion), el formato que usa [llama.cpp](../glosario/06-modelos-abiertos.md#servir). Después miras cuánto ocupa cada uno.

```bash
# El modelo de texto de 1,5 B (unos 1,1 GB) y el de embeddings (unos 610 MB)
curl -L -o modelos/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
curl -L -o modelos/qwen3-embedding-0.6b-q8_0.gguf \
  https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf

# Cuánto ocupa cada modelo en disco
ls -lh modelos/*.gguf
```

**Resultado esperado:**

```text
469M modelos/qwen2.5-0.5b-instruct-q4_k_m.gguf
1,1G modelos/qwen2.5-1.5b-instruct-q4_k_m.gguf
610M modelos/qwen3-embedding-0.6b-q8_0.gguf
```

**Cómo se lee:** el de 1,5 B ocupa algo más del doble que el de 0,5 B: los dos están en 4 bits (Q4), así que el tamaño crece con los parámetros. El de embeddings está en 8 bits (Q8): con 0,6 B se puede permitir más precisión sin pasar de 610 MB. Es la regla de la sección de formatos: parámetros × bytes por parámetro.

### 2 — Leer la ficha y la licencia

**Qué ocurre:** antes de usar un modelo en planta, se lee su **ficha** («model card»): qué es, para qué está pensado, en qué idiomas y con qué licencia. Abre en el navegador las dos fichas:

- <https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF>
- <https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF>

**Qué ves:** arriba, las etiquetas, entre ellas **License: apache-2.0**; en «Files and versions», el fichero `LICENSE` con el texto completo; en la descripción, para qué sirve cada modelo (uno es «Instruct», para conversar y seguir instrucciones; el otro, «Embedding», para recuperar textos). Fíjate también en los idiomas: los dos incluyen el español.

**Cómo se lee:** Apache 2.0 permite el uso comercial en la planta manteniendo el aviso de licencia. Si en la ficha apareciera otra licencia (una comunitaria con condiciones, o AGPL como la de YOLO), la decisión ya no sería del técnico: iría a compras y a legal. En el «Constrúyelo tú» y en el reto 2 verás si la licencia viene escrita también **dentro del propio fichero**.

### 3 — Comparar los dos modelos de texto

**Qué ocurre:** comparas el modelo del curso con el candidato en lo que importa en un puesto: cuánto ocupan en memoria, cuánto tardan y si contestan bien a cuatro preguntas de EST-01, con el párrafo del procedimiento delante, como el asistente del M05-03. Las preguntas y la palabra que tiene que salir en una respuesta correcta están en el código del comando (`BANCO_EST01`).

```bash
# Carga cada modelo de infra/modelos/ (salvo el de embeddings) y le pasa las mismas cuatro preguntas
docker compose --profile lab run --rm --no-deps lab m05-05
```

📋 Ficha del comando [`m05-05`](../comandos-lab.md#m05-05): qué hace, qué lee y cuándo da `OK`.

**Resultado esperado** (cambian los tiempos):

```text
preguntas=4  con el párrafo del procedimiento=sí
modelo                               tamaño  carga  memoria  tokens/s  acierto
qwen2.5-0.5b-instruct-q4_k_m.gguf     0.49 GB  0.3 s    768 MB      23.7  2 de 4
qwen2.5-1.5b-instruct-q4_k_m.gguf     1.12 GB  0.9 s   1956 MB      10.3  4 de 4
OK m05-05: 2 modelos comparados con las mismas preguntas
```

**Cómo se lee:**

| | 0,5 B (el del curso) | 1,5 B (el candidato) |
|--|----------------------|----------------------|
| Acierto con el documento delante | 2 de 4 | **4 de 4** |
| Velocidad | ~24 [tokens](../glosario/04-ia-generativa.md#token)/s | ~10 tokens/s: una respuesta de 60 tokens, unos 6 s |
| Memoria en uso | ~770 MB | **~1 950 MB**: casi todo el contenedor de 2 GB |

El de 1,5 B **contesta mejor**, y a cambio es la mitad de rápido y casi llena la memoria del contenedor. En el reto del M05-01 lo estimaste; ahora lo has medido. Ninguno de los dos es «el mejor»: depende de cuánto se puede esperar en el puesto y de cuánta memoria hay.

## Comprueba tu entendimiento

**Qué número decide**

Si el puesto tiene un equipo con 1 GB de memoria libre, ¿qué modelo puedes instalar?

→ El de 0,5 B. El de 1,5 B necesita casi 2 GB en uso, aunque el fichero ocupe 1,1 GB: se mide la memoria en uso, no el tamaño en disco.

## Experimenta: sin el documento delante

**Qué ocurre:** repites la comparación **sin** darles el párrafo del procedimiento: tienen que contestar de memoria.

**Predice:** ¿el modelo más grande sabrá a qué par se aprieta el tornillo de la brida de EST-01?

```bash
docker compose --profile lab run --rm --no-deps lab m05-05 sin-documento
```

**Resultado esperado** (cambian los tiempos):

```text
preguntas=4  con el párrafo del procedimiento=no
modelo                               tamaño  carga  memoria  tokens/s  acierto
qwen2.5-0.5b-instruct-q4_k_m.gguf     0.49 GB  0.4 s    763 MB      34.6  0 de 4
qwen2.5-1.5b-instruct-q4_k_m.gguf     1.12 GB  0.9 s   1949 MB      13.7  0 de 4
OK m05-05: 2 modelos comparados con las mismas preguntas
```

**Cómo se lee:** **ninguno acierta ninguna**, tampoco el grande. Ningún modelo, de ningún tamaño, sabe cosas de EST-01: no estaban en sus datos de entrenamiento. Un modelo más grande redacta y entiende mejor, pero el dato de la planta tiene que dárselo el sistema ([RAG](../glosario/04-ia-generativa.md#rag) o herramientas). Por eso, en el pedido del integrador, junto a los modelos que redactan hay uno de embeddings: el que encuentra el dato.

## Constrúyelo tú: tu propio buscador por significado

**Qué está pasando:** el asistente del M05-03 busca el párrafo por **palabras en común**, y falla cuando la pregunta usa otras palabras («¿cuánto calor aguanta el eje?» no comparte ninguna con «la temperatura del husillo»). Ahora construyes tú la búsqueda **por significado** con el modelo de embeddings Qwen3-Embedding 0.6B: conviertes cada párrafo en una lista de números, haces lo mismo con la pregunta y eliges el párrafo cuyos números se parecen más. Es la pieza que pedía el integrador para «búsqueda semántica» en la hoja de modelos abiertos.

**Cómo se trabaja en cada paso:**

1. Lees para qué es el paso y qué hace el bloque.
2. Copias el bloque y lo pegas en el fichero, **debajo del comentario de ese paso** (`# --- PASO N …`), en lugar de la línea `# (pega aquí el bloque del paso N)`.
3. Guardas y ejecutas el script. Cada ejecución repite todo desde el principio, así que la salida crece paso a paso: lo nuevo aparece al final.

### 1 — Abrir el fichero y ejecutarlo tal cual

**Para qué:** comprobar que el modelo de embeddings carga en el equipo y saber con qué licencia viene.

**Qué ocurre:** abres en VS Code el fichero [`infra/construye/m05_05_mi_buscador.py`](../../infra/construye/m05_05_mi_buscador.py). Arriba están las **decisiones** (`PREGUNTA`, `MINIMO_PARECIDO`); debajo, el paso 1 ya escrito: carga el modelo de embeddings que descargaste en el paso 1 del lab y lee su nombre y su licencia de los **metadatos del propio fichero**. Lo ejecutas sin tocar nada.

```bash
# Ejecuta tu script con el Python del contenedor lab (-W ignore oculta avisos de las librerías)
docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m05_05_mi_buscador.py
```

**Resultado esperado:**

```text
modelo: Qwen3 Embedding 0.6b  licencia (escrita en el propio fichero): apache-2.0
```

**Cómo se lee:** el fichero GGUF lleva dentro su nombre y su licencia, Apache 2.0: es lo mismo que dice su ficha en Hugging Face, y es una forma de comprobar qué tienes instalado sin depender de una página web. `embedding=True` le dice al motor que este modelo no va a redactar: va a convertir textos en números. `--entrypoint python` hace que el contenedor `lab` ejecute **tu fichero**.

### 2 — Un texto convertido en números

**Para qué:** ver qué produce un modelo de embeddings, que no es texto.

**Qué ocurre:** pides al modelo el embedding de la pregunta y enseñas cuántos números tiene y los primeros. Lo normalizas (lo divides por su longitud) para poder comparar dos de ellos con una multiplicación.

Pega debajo de `# --- PASO 2`:

```python
def embedding(texto):
    with _Silencio():
        v = np.array(modelo.embed(texto))
    v = v if v.ndim == 1 else v[-1]          # un vector por texto
    return v / np.linalg.norm(v)              # longitud 1: así el parecido va de -1 a 1

e = embedding(PREGUNTA)
print(f"la pregunta es ahora una lista de {len(e)} números: {np.round(e[:5], 3)} ...")
```

Ejecuta de nuevo (el mismo comando del paso 1).

**Resultado esperado** (líneas nuevas):

```text
la pregunta es ahora una lista de 1024 números: [-0.011  0.043 -0.002  0.011 -0.014] ...
```

**Cómo se lee:** una pregunta de diez palabras se ha convertido en **1 024 números**. Cada número no significa nada por sí solo; lo que importa es que **dos textos con significado parecido dan listas parecidas**, aunque no compartan ninguna palabra. Es lo que el modelo aprendió al entrenarse con muchísimos textos.

### 3 — Los párrafos del procedimiento, en números

**Para qué:** tener preparado el documento para buscar en él por significado.

**Qué ocurre:** partes el procedimiento en párrafos, como en el M05-03, y calculas el embedding de cada uno. Esto se hace una vez; en un sistema real se guarda y solo se repite si cambia el documento.

Pega debajo de `# --- PASO 3`:

```python
documento = open("/opt/linea/docs/procedimiento-est01.md", encoding="utf-8").read()
parrafos = [p.strip() for p in documento.split("\n\n") if p.strip() and not p.startswith("#")]
vectores = np.array([embedding(p) for p in parrafos])
print(f"{len(parrafos)} párrafos convertidos: una tabla de {vectores.shape[0]} × {vectores.shape[1]} números")
```

**Resultado esperado** (líneas nuevas):

```text
5 párrafos convertidos: una tabla de 5 × 1024 números
```

**Cómo se lee:** cinco párrafos, cada uno con sus 1 024 números. Es el «índice» del buscador. Con un manual de cientos de páginas serían miles de filas, y se guardan en una base de datos de vectores; aquí caben en memoria.

### 4 — Buscar por significado

**Para qué:** encontrar el párrafo que contesta a la pregunta aunque no comparta palabras con ella.

**Qué ocurre:** multiplicas el embedding de la pregunta por el de cada párrafo: el resultado es su **parecido** (1 = mismo significado, 0 = nada que ver). Enseñas el párrafo más parecido.

Pega debajo de `# --- PASO 4`:

```python
def buscar(pregunta):
    parecidos = vectores @ embedding(pregunta)          # un parecido por párrafo
    mejor = int(np.argmax(parecidos))
    return parrafos[mejor], float(parecidos[mejor])

parrafo, parecido = buscar(PREGUNTA)
print(f"por significado (parecido {parecido:.2f}): {parrafo[:90]}")
```

**Resultado esperado** (líneas nuevas):

```text
por significado (parecido 0.46): La temperatura de trabajo habitual del husillo está entre 58 °C y 66 °C. Por encima de 70
```

**Cómo se lee:** elige el párrafo de la **temperatura del husillo**, aunque la pregunta dice «calor» y «eje». El modelo de embeddings sabe que «calor» se parece a «temperatura» y «eje» a «husillo». Un parecido de 0,46 no parece alto, pero lo que cuenta es que este párrafo se parece **más** que los demás.

### 5 — Comparar con la búsqueda por palabras

**Para qué:** ver en el mismo caso qué gana la búsqueda por significado frente a la del M05-03.

**Qué ocurre:** aplicas a la misma pregunta la búsqueda por palabras en común del M05-03, con sus [palabras vacías](../glosario/04-ia-generativa.md#palabras-vacias), y enseñas lo que elige.

Pega debajo de `# --- PASO 5`:

```python
VACIAS = {"a", "al", "de", "del", "el", "la", "las", "los", "un", "una", "y", "o", "en", "se", "que",
          "qué", "es", "por", "para", "con", "cómo", "cuánto", "cuál", "antes"}

def palabras(t):
    return set(re.findall(r"[a-záéíóúñ0-9]+", t.lower())) - VACIAS

comunes = [len(palabras(p) & palabras(PREGUNTA)) for p in parrafos]
mejor = int(np.argmax(comunes))
print(f"por palabras ({comunes[mejor]} en común): {parrafos[mejor][:90]}")
```

**Resultado esperado** (líneas nuevas):

```text
por palabras (1 en común): Antes de medir el husillo, bloquear el husillo con el cerrojo mecánico. No se mide con el
```

**Cómo se lee:** por palabras gana el párrafo del **bloqueo**, porque comparte la palabra «eje» («no se mide con el eje libre»), que no tiene nada que ver con avisar por calor. Es exactamente el fallo del M05-03 cuando el técnico pregunta con sus propias palabras: una palabra suelta en común pesa más que el significado. Por eso un RAG de planta usa embeddings, que es lo que pedía el integrador.

### 6 — Decide tú: una pregunta que el procedimiento no contesta

**Para qué:** elegir a partir de qué parecido el buscador debe decir «no está».

**Qué ocurre:** cambias `PREGUNTA` por `"¿De qué color es el tornillo de recambio?"` y ejecutas. Después añades este bloque al final y pruebas `MINIMO_PARECIDO = 0.4`:

```python
# Si ni el mejor párrafo se parece lo suficiente, no hay respuesta en el documento
print("asistente:", "el procedimiento no dice nada sobre eso" if parecido < MINIMO_PARECIDO else parrafo)
```

**Resultado esperado** (las líneas que importan):

```text
# ¿De qué color es el tornillo de recambio?  (MINIMO_PARECIDO = 0.4)
por significado (parecido 0.35): El tornillo de la brida se aprieta a 12 N·m. Si el par queda por debajo, la pieza se manda
asistente: el procedimiento no dice nada sobre eso

# ¿Cuánto calor aguanta el eje antes de avisar?  (MINIMO_PARECIDO = 0.4)
asistente: La temperatura de trabajo habitual del husillo está entre 58 °C y 66 °C. Por encima de 70 °C se avisa al turno. Ese aviso es una regla, no un modelo.
```

**Cómo se lee:** la búsqueda por significado **siempre devuelve el párrafo más parecido**, aunque no tenga la respuesta: para el color del tornillo devuelve el del par de apriete, con un parecido de 0,35. Con un mínimo de 0,4, ese caso se queda fuera y el asistente dice que no está, mientras que las preguntas buenas (0,45 y 0,46) siguen pasando. Pero fíjate en lo cerca que están 0,35 y 0,45: el mínimo se fija probando con preguntas reales de la planta, las que sí tienen respuesta y las que no, y se revisa cuando cambia el documento. Vuelve a dejar la pregunta del calor, `MINIMO_PARECIDO = 0.0` y quita el bloque.
## Reto

### 1 — Elegir el modelo para el puesto

**La situación:** calidad quiere el asistente del M05-03 en la tablet de un puesto. El equipo del puesto tiene **2 GB para el contenedor**, el técnico no quiere esperar más de **5 s** por una respuesta corta (unos 30 tokens), y el asistente tiene que acertar con el documento delante.

**Qué haces:** con los números del paso 3, calculas para cada modelo cuánto tardaría una respuesta de 30 tokens y compruebas si cabe y si acierta. Basta con hacer la cuenta a mano.

**Pistas:** el tiempo de una respuesta es `tokens / (tokens por segundo)` más la búsqueda del párrafo, que con embeddings son décimas de segundo; «cabe» si la memoria en uso deja margen en 2 GB.

**Lo que buscas:** qué modelo instalarías en el puesto y qué tendrías que cambiar para poder usar el otro.

<details>
<summary>Ver solución</summary>

| | 0,5 B | 1,5 B |
|--|-------|-------|
| 30 tokens a su velocidad | 30 / 23,7 ≈ **1,3 s** | 30 / 10,3 ≈ **2,9 s** |
| Memoria en uso frente a 2 GB | 768 MB: sobra | 1 956 MB: **sin margen** |
| Acierto con el documento | 2 de 4 | 4 de 4 |

Por tiempo, los dos caben en 5 s. Por acierto, gana el de 1,5 B. Pero **no cabe con margen** en 2 GB: con una conversación algo más larga o con el modelo de embeddings cargado a la vez, el contenedor se quedaría sin memoria y el sistema lo pararía.

**Qué instalarías:** el de 1,5 B, **subiendo la memoria del equipo a 4 GB**; o, si eso no es posible, el de 0,5 B con una comprobación de la respuesta como la del M05-03, sabiendo que fallará más. **La regla:** un modelo se elige con las tres medidas a la vez (acierto, tiempo y memoria) en el equipo donde va a correr, y la decisión incluye qué cambiar en el equipo, no solo qué modelo descargar.

</details>

### 2 — ¿Se puede usar en planta?

**La situación:** alguien ha dejado en `infra/modelos/` varios modelos descargados de distintos sitios y nadie sabe con qué licencia vienen.

**Qué haces:** escribes un script corto en `infra/construye/` que abra cada fichero GGUF de `/modelos` y enseñe su nombre y su licencia, tal como vienen en sus metadatos.

**Pistas:** `Llama(model_path=..., vocab_only=True)` abre el fichero sin cargar el modelo entero; `.metadata.get("general.license")` y `.metadata.get("general.name")`; usa `_Silencio()` como en el paso 1 de «Constrúyelo tú» para callar al motor.

**Lo que buscas:** la licencia de cada modelo instalado, y qué harías si alguno no la dijera.

<details>
<summary>Ver solución</summary>

```python
from pathlib import Path

from llama_cpp import Llama

from linea.cli import _Silencio

for ruta in sorted(Path("/modelos").glob("*.gguf")):
    with _Silencio():
        m = Llama(model_path=str(ruta), vocab_only=True, verbose=False)
    print(f"{ruta.name:38s} {str(m.metadata.get('general.name')):28s} licencia={m.metadata.get('general.license', 'NO LO DICE')}")
```

```text
qwen2.5-0.5b-instruct-q4_k_m.gguf      qwen2.5-0.5b-instruct        licencia=NO LO DICE
qwen2.5-1.5b-instruct-q4_k_m.gguf      qwen2.5-1.5b-instruct        licencia=NO LO DICE
qwen3-embedding-0.6b-q8_0.gguf         Qwen3 Embedding 0.6b         licencia=apache-2.0
```

**Solo el de embeddings lleva la licencia dentro.** Los dos Qwen2.5 son también Apache 2.0, como dice su ficha del paso 2, pero su fichero no lo dice: quien los empaquetó no rellenó ese dato. Con un fichero que no dice su licencia, **no se instala** hasta encontrar su ficha oficial y apuntarla: que un fichero esté en una carpeta no dice nada de si se puede usar. **La regla:** se lleva un inventario de los modelos instalados con su origen y su licencia, igual que del software; es lo primero que pedirá una auditoría.

</details>

## Errores frecuentes

| Síntoma | Causa probable | Cómo arreglarlo |
|---------|----------------|-----------------|
| `FALLO: hace falta un segundo modelo en infra/modelos/` | no has descargado el modelo de 1,5 B | repite el paso 1 |
| `curl` descarga un fichero de pocos KB | la dirección está mal escrita y Hugging Face devuelve una página de error | comprueba la dirección; un GGUF empieza por los caracteres `GGUF` (`head -c 4 modelos/…gguf`) |
| el comando se para con `Killed` | el contenedor `lab` se ha quedado sin memoria | cierra otros contenedores (`docker compose stop llm`) y vuelve a lanzarlo |
| `NameError: name '…' is not defined` | pegaste un bloque en el hueco de otro paso, o te saltaste uno | cada bloque va debajo de su `# --- PASO N`, en orden |
| `IndentationError` | el bloque quedó con espacios de más o de menos al pegarlo | las líneas de cada bloque empiezan en la columna 0, salvo las de dentro de `for`, `if`, `while` y `def` |
| `ModuleNotFoundError` | ejecutaste el script con el Python de tu equipo | ejecútalo con el comando del paso 1, dentro del contenedor `lab` |
| `ValueError: Model path does not exist: /modelos/qwen3-embedding-0.6b-q8_0.gguf` | no has descargado el modelo de embeddings | repite el paso 1 del lab |

## Conclusiones

### Qué es elegir un modelo abierto

Es decidir **qué tipo de modelo** necesita cada tarea (redactar, buscar, transcribir, ver o predecir) y, dentro de ese tipo, **qué modelo concreto** se instala en el equipo de la planta, con qué formato y con qué licencia. Se elige midiendo, no por fama ni por tamaño.

### Cómo debe hacerse

| Requisito | Cómo se ha cumplido en el lab |
|-----------|-------------------------------|
| Leer la ficha y la licencia antes de usarlo | Paso 2 y reto 2: Apache 2.0, en la ficha y dentro del fichero |
| Medir en el equipo donde va a correr | Paso 3: memoria en uso, velocidad y tiempo de carga en el contenedor de 2 GB |
| Probar con preguntas de la planta | El banco de cuatro preguntas de EST-01 |
| Separar redactar de encontrar el dato | El de embeddings busca el párrafo; el LLM redacta con él |

### Qué límites tiene

| Límite | Cómo se ha visto |
|--------|------------------|
| Ningún modelo sabe cosas de la planta | Sin documento, 0 de 4 los dos |
| Más grande es más lento y ocupa más | 1,5 B: el doble de lento y casi 2 GB en uso |
| La memoria en uso no es el tamaño del fichero | 1,1 GB en disco, casi 2 GB en memoria |
| El parecido de los embeddings no es una certeza | La pregunta sin respuesta da 0,35, muy cerca de las buenas (0,45) |

### Cómo se mejora

- Con **embeddings** para encontrar el dato aunque el técnico pregunte con otras palabras.
- Con un modelo más grande **en un servidor** con GPU, al que llaman todos los puestos, en lugar de uno pequeño en cada puesto (vLLM, en la hoja de modelos abiertos).
- Con un **inventario** de modelos instalados, su origen y su licencia.

### En una frase

> 🔑 Cada tarea tiene su tipo de modelo, y cada modelo se elige midiendo en el equipo donde va a correr, con preguntas de la planta y con la licencia leída: ninguno sabe nada de la planta si no se le da el dato.
