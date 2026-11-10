# M05-01 — Ejecución local de modelos generativos

[← Página anterior](README.md) · [Siguiente página →](M05-02-integracion-aplicacion.md)

> Práctica del módulo. La teoría y la demostración están en el [README del módulo](README.md).
>
> Lanza los comandos desde la carpeta `infra/` del repositorio. Un paso que cuadra termina con una línea que empieza por `OK`.

### Objetivo

Comprender qué es **ejecutar un modelo generativo en local**: qué hace falta para que funcione en el puesto, cómo debe dimensionarse, qué se gana y qué se pierde frente a un servicio externo, y cómo se decide el tamaño.

### Prerrequisitos

- El fichero `infra/modelos/qwen2.5-0.5b-instruct-q4_k_m.gguf` (~[470 MB](../glosario/04-ia-generativa.md#cuantizacion)). Lo deja la prueba del puesto; si falta, paso 1.
- RAM: el contenedor `llm` tiene un techo de 2 GB. CPU, sin GPU.

### Qué está pasando

Los **técnicos de mantenimiento** quieren un asistente al que preguntar cosas de la estación en lenguaje normal. La condición de la planta es clara: **ningún dato sale de la fábrica**. Nada de enviar preguntas ni procedimientos a un servicio de internet.

La solución es un **[modelo de lenguaje](../glosario/04-ia-generativa.md#llm) que se ejecuta en el propio puesto**. Es pequeño (Qwen2.5 de 0,5B, 500 millones de parámetros, comprimido a 4 bits), funciona en CPU y no necesita GPU. En este lab lo arrancas y mides lo que tarda en responder, que es lo que decide si el asistente es usable en planta.

### 1 — Tener el modelo en disco

Vas a comprobar que el fichero del modelo está en el puesto. Un modelo local es, ante todo, un fichero.

```bash
# ¿Está el modelo?
ls -lh modelos/

# Solo si no está: descarga única (~470 MB)
docker compose run --rm modelo
```

Si te lo saltas no pasa nada: `docker compose up -d llm` arranca antes el servicio `modelo`, que baja el fichero si falta. Con `-d` no ves el progreso; por eso es mejor hacerlo aquí.

**Resultado esperado:** un fichero `qwen2.5-0.5b-instruct-q4_k_m.gguf` de unos 470 MB.

### 2 — Arrancar el modelo y esperar a que cargue

Vas a liberar memoria parando el panel, arrancar el servicio del modelo y esperar a que diga que está listo. Hasta que el proceso no tiene el modelo en memoria, no hay respuesta.

```bash
# El panel no hace falta en M05 y ocupa memoria
docker compose stop panel

# Arranca el servicio del modelo
docker compose up -d llm

# Pregunta si está listo (repite hasta que conteste)
curl -s http://localhost:8088/salud
```

También puedes abrir <http://localhost:8088/salud> en Chrome, y <http://localhost:8088/docs> para ver la documentación del servicio.

**Resultado esperado:**

```json
{"estado":"ok","modelo":"qwen2.5-0.5b-instruct-q4_k_m.gguf"}
```

Si `curl` da `Connection refused` o no contesta, el modelo sigue cargando: espera unos segundos y repite.

### 3 — Una pregunta corta

Vas a pedir una respuesta corta y medir cuánto tarda. Es la medida que importa del puesto: segundos por respuesta.

```bash
# Pide "hola" al servicio local y cronometra
docker compose --profile lab run --rm --no-deps lab m05-01
```

📋 Ficha del comando [`m05-01`](../comandos-lab.md#m05-01): qué hace, qué lee, qué escribe y cuándo da `OK`.

**Resultado esperado** (el tiempo depende del puesto):

```text
respuesta='¡Hola! ¿Cómo puedo ayudarte hoy?' segundos=0.5 url=http://llm:8088
OK m05-01: inferencia local en 0.5s via http://llm:8088
```

`http://llm:8088` es el contenedor `llm` dentro de la red de Docker del puesto, no un dominio de internet.

## Comprueba tu entendimiento

**Sigue en local**

La URL del `OK`, ¿sale del puesto o va a un proveedor externo?

→ Es `http://llm:8088`, el contenedor del puesto.

## Investiga: cuánto ocupa y cuánto tarda

**Qué ocurre:** mides lo que cuesta tener el modelo en el puesto: memoria y tiempo para una respuesta larga.

```bash
# Memoria que usa el contenedor del modelo
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}' | grep -E "NAME|llm"

# Tiempo para una respuesta de hasta 200 tokens (trozos de palabra)
time curl -s http://localhost:8088/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"messages": [{"role": "user", "content": "Escribe un párrafo sobre el mantenimiento preventivo."}], "max_tokens": 200}' > /dev/null
```

**Resultado esperado** (depende del puesto):

```text
NAME                  MEM USAGE / LIMIT
ia-linea-llm-1        192MiB / 2GiB
```

```text
real	0m2,759s
```

**Cómo se lee:** el contenedor marca unos 200 MB porque el modelo se lee del fichero según lo necesita (el sistema lo mantiene en memoria caché, que `docker stats` no cuenta entera). El tiempo es lo que importa: aquí, menos de 3 segundos para 200 [tokens](../glosario/04-ia-generativa.md#token); en un portátil más modesto, varias veces más. Ese número decide si el asistente es usable en el puesto: un técnico no espera un minuto por una respuesta.

## Experimenta: la misma pregunta, tres veces

**Qué ocurre:** haces la misma pregunta tres veces con el comando de ayuda `lab preguntar`.

```bash
for i in 1 2 3; do
  docker compose --profile lab run --rm --no-deps lab preguntar "¿A qué par se aprieta el tornillo de la brida de EST-01?" | grep respuesta
done
```

📋 Ficha del comando [`preguntar`](../comandos-lab.md#preguntar).

**Resultado esperado** (cada vez una cosa distinta):

```text
respuesta: El tornillo de la brida de EST-01 se aprieta con el pincho de la brida.
respuesta: El tornillo de la brida de EST-01 se aprieta con el pincho de la estación.
respuesta: El tornillo de la brida de EST-01 se aprieta con el pinza de la estación.
```

**Cómo se lee:** **tres respuestas distintas e [inventadas](../glosario/04-ia-generativa.md#alucinacion)**. El modelo elige cada palabra [con algo de azar](../glosario/04-ia-generativa.md#temperatura-llm), así que no es determinista; y como no conoce el procedimiento, se inventa algo que suene a respuesta. Las dos cosas juntas dicen cómo **no** usar un modelo de lenguaje: como fuente de datos de la planta. En el M05-03 verás cómo se corrige.

## Constrúyelo tú: tu propio cliente del modelo

**Qué está pasando:** hasta aquí has preguntado al modelo con `curl` y con `lab preguntar`. Ahora escribes tú el cliente: compruebas que el servicio está vivo, le haces una pregunta, mides cuánto tarda y cuántos tokens usa, y averiguas cómo crece el tiempo con la longitud de la respuesta. Son los números con los que se decide si un modelo local sirve en un puesto.

**Cómo se trabaja en cada paso:**

1. Lees para qué es el paso y qué hace el bloque.
2. Copias el bloque y lo pegas en el fichero, **debajo del comentario de ese paso** (`# --- PASO N …`), en lugar de la línea `# (pega aquí el bloque del paso N)`.
3. Guardas y ejecutas el script. Cada ejecución repite todo desde el principio, así que la salida crece paso a paso: lo nuevo aparece al final.

### 1 — Abrir el fichero y ejecutarlo tal cual

**Para qué:** asegurarte de que tu código llega al modelo antes de preguntarle nada.

**Qué ocurre:** abres en VS Code el fichero [`infra/construye/m05_01_mi_cliente_llm.py`](../../infra/construye/m05_01_mi_cliente_llm.py). Arriba están las **decisiones** (`PREGUNTA`, `LONGITUDES`); debajo, el paso 1 ya escrito: pide `/salud` al contenedor `llm`. Lo ejecutas sin tocar nada.

```bash
# Ejecuta tu script con el Python del contenedor lab (-W ignore oculta avisos de las librerías)
docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m05_01_mi_cliente_llm.py
```

**Resultado esperado:**

```text
salud: {'estado': 'ok', 'modelo': 'qwen2.5-0.5b-instruct-q4_k_m.gguf'}
```

**Cómo se lee:** el servicio contesta y dice qué fichero de modelo tiene cargado: el de 470 MB que descargaste. Todo pasa dentro de tu equipo: la dirección es `llm:8088`, el contenedor de al lado. `--entrypoint python` hace que el contenedor `lab` ejecute **tu fichero**.

### 2 — Hacer una pregunta

**Para qué:** hablar con el modelo exactamente como lo hará una aplicación de planta.

**Qué ocurre:** mandas la `PREGUNTA` por HTTP, en el formato de mensajes que espera el servicio, y enseñas la respuesta y cuánto ha tardado.

Pega debajo de `# --- PASO 2`:

```python
def preguntar(texto, max_tokens=80):
    peticion = {"messages": [{"role": "user", "content": texto}], "max_tokens": max_tokens}
    inicio = time.time()
    respuesta = httpx.post(f"{LLM}/v1/chat/completions", json=peticion, timeout=180).json()
    return respuesta, time.time() - inicio

respuesta, segundos = preguntar(PREGUNTA)
print(f"respuesta ({segundos:.1f} s): {respuesta['choices'][0]['message']['content']}")
```

Ejecuta de nuevo (el mismo comando del paso 1).

**Resultado esperado** (línea nueva; cambian el texto y el tiempo):

```text
respuesta (1.8 s): El mantenimiento preventivo es una práctica que se utiliza para prevenir el uso excesivo de recursos y evitar el desperdicio. Este proceso se basa en la observación y la revisión periódicas de los sistemas y los equipos, con el objetivo de detectar y prevenir problemas antes de que se vuelvan negativos. Es un proceso que se utiliza en muchos sectores
```

**Cómo se lee:** una respuesta razonable en menos de dos segundos, sin GPU, aunque le pediste **una** frase y escribe tres, y se corta a media frase: llegó a los 80 tokens de `max_tokens`. La petición es un JSON con la conversación (`messages`) y un máximo de longitud; la respuesta, otro JSON. Cualquier aplicación que sepa hacer una petición HTTP puede usar el modelo.

### 3 — Contar los tokens

**Para qué:** medir el trabajo del modelo en su propia unidad.

**Qué ocurre:** la respuesta trae, en `usage`, cuántos tokens tenía la pregunta y cuántos ha escrito el modelo. Con el tiempo, calculas los tokens por segundo.

Pega debajo de `# --- PASO 3`:

```python
uso = respuesta["usage"]
print(f"tokens: pregunta={uso['prompt_tokens']} respuesta={uso['completion_tokens']}  "
      f"velocidad={uso['completion_tokens'] / segundos:.0f} tokens/s")
```

**Resultado esperado** (línea nueva; cambian los números):

```text
tokens: pregunta=44 respuesta=80  velocidad=45 tokens/s
```

**Cómo se lee:** unos 45 tokens por segundo en este equipo. La pregunta ocupa 44 tokens aunque tiene 9 palabras: el servicio añade por dentro las instrucciones de formato de la conversación. Un token es un trozo de palabra. Esta cifra decide si el modelo es usable: un técnico no espera un minuto por una respuesta.

### 4 — Cómo crece el tiempo con la longitud

**Para qué:** saber cuánto tardará una respuesta antes de pedirla.

**Qué ocurre:** pides una respuesta larga con distintos máximos de tokens (`LONGITUDES`) y mides cuántos escribe y cuánto tarda en cada caso.

Pega debajo de `# --- PASO 4`:

```python
print("max_tokens  escritos  segundos")
for maximo in LONGITUDES:
    r, s = preguntar("Escribe un párrafo largo sobre el mantenimiento de un husillo.", maximo)
    print(f"{maximo:10d}  {r['usage']['completion_tokens']:8d}  {s:8.1f}")
```

**Resultado esperado** (líneas nuevas; cambian los números):

```text
max_tokens  escritos  segundos
        20        20       0.5
        80        80       1.4
       200       200       3.3
```

**Cómo se lee:** el tiempo crece **casi en proporción a los tokens escritos**: unos 0,015 s por token, más un poco fijo por petición. El modelo escribe token a token, y cada uno cuesta lo mismo. Por eso, en una aplicación, `max_tokens` es también un límite de tiempo.

### 5 — Decide tú: una pregunta de la planta

**Para qué:** ver qué hace el modelo cuando le preguntas algo que no puede saber.

**Qué ocurre:** cambias `PREGUNTA` por `"¿A qué par se aprieta el tornillo de la brida de EST-01? Si no lo sabes, di: no lo sé."` y ejecutas dos veces.

**Resultado esperado** (dos ejecuciones; la respuesta cambia en cada una):

```text
respuesta (1.4 s): Lo siento, pero no puedo proporcionar información sobre mi personalidad o características específicas. Soy Qwen, un modelo de IA creado por Alibaba Cloud, y no tengo una personalidad ni características específicas. ...
respuesta (3.1 s): Lo siento, pero no puedo proporcionar información sobre mi par o mi identidad personal. Soy un modelo de inteligencia artificial creado por Alibaba Cloud, y no tengo una identidad física ni una par. ...
```

**Cómo se lee:** no dice «no lo sé», y tampoco contesta a lo que le preguntas: **entiende la pregunta al revés** y habla de sí mismo («mi par», «mi identidad»). En otras ejecuciones se inventa una cifra, como en «Experimenta». Un modelo de 0,5 B no conoce la planta ni entiende bien el contexto: sin el documento, sus respuestas no son fiables ni cuando parecen prudentes. Pedirle prudencia en la pregunta no basta; hay que darle el dato, que es lo que harás en el M05-03. Vuelve a dejar la pregunta de antes.
## Reto

### 1 — ¿Y un modelo más grande?

**La situación:** alguien propone cambiar el modelo de 0,5 B (500 millones de parámetros) por uno de 7 B, que contesta mucho mejor. El contenedor `llm` tiene 2 GB de memoria y el técnico del puesto no debería esperar más de 30 s por una respuesta de unos 200 tokens.

**Qué haces:** con la velocidad que mediste en el paso 3, añades al final de tu script un cálculo aproximado para modelos de 1,5 B y de 7 B. Supón que, sin GPU, la velocidad baja y la memoria sube en proporción a los parámetros, y que el fichero de 0,5 B ocupa 470 MB.

**Pistas:** un modelo 14 veces más grande (7 / 0,5) escribe unas 14 veces más despacio y ocupa unas 14 veces más; los segundos para 200 tokens son `200 / velocidad`.

**Lo que buscas:** qué tamaño de modelo cabe en el contenedor y responde a tiempo.

<details>
<summary>Ver solución</summary>

```python
# Reto 1: estimar otros tamaños con la velocidad medida
velocidad = uso["completion_tokens"] / segundos
print("modelo  tokens/s  segundos_para_200  memoria_aprox")
for tamano in (0.5, 1.5, 7):
    veces = tamano / 0.5
    print(f"{tamano:4.1f} B  {velocidad / veces:8.1f}  {200 / (velocidad / veces):17.0f}  {470 * veces / 1000:10.1f} GB")
```

```text
modelo  tokens/s  segundos_para_200  memoria_aprox
 0.5 B      64.6                  3         0.5 GB
 1.5 B      21.5                  9         1.4 GB
 7.0 B       4.6                 43         6.6 GB
```

El de **7 B tardaría más de 40 s** en cada respuesta y **no cabe** en 2 GB. El de 1,5 B todavía cabe y responde a tiempo, a costa de ser tres veces más lento. Tus números cambian con cada ejecución, porque la velocidad medida varía, pero la conclusión no. Es una estimación (la velocidad real depende del procesador y de cómo esté comprimido el modelo), pero da el orden de magnitud. **La regla:** el tamaño de un modelo local se elige por lo que cabe en el equipo del puesto y por el tiempo que se puede esperar, no por lo bien que contesta. Lo que le falta a un modelo pequeño se compensa dándole el documento (M05-03) o los datos (M05-04).

</details>

## Errores frecuentes

| Síntoma | Causa probable | Cómo arreglarlo |
|---------|----------------|-----------------|
| `FALLO: el servicio local no responde` | sigue cargando o falta el `.gguf` | `docker compose logs llm` y `ls -lh modelos/` |
| `Falta el modelo en /modelos/…` en los logs | el fichero no está o tiene otro nombre | paso 1 |
| tarda mucho | es la primera carga en CPU | espera a que `/salud` conteste antes de repetir |
| `NameError: name '…' is not defined` | pegaste un bloque en el hueco de otro paso, o te saltaste uno | cada bloque va debajo de su `# --- PASO N`, en orden |
| `IndentationError` | el bloque quedó con espacios de más o de menos al pegarlo | las líneas de cada bloque empiezan en la columna 0, salvo las de dentro de `for`, `if`, `while` y `def` |
| `ModuleNotFoundError` | ejecutaste el script con el Python de tu equipo | ejecútalo con el comando del paso 1, dentro del contenedor `lab` |
| `httpx.ConnectError` | el contenedor `llm` está parado o todavía cargando el modelo | `docker compose up -d llm` y espera a que `/salud` conteste |

## Conclusiones

### Qué es un modelo generativo local

Es un modelo de lenguaje que se ejecuta **en el propio equipo**, sin enviar nada fuera. Tiene dos partes: un **fichero** con el modelo (aquí, unos 470 MB) y un **proceso** que lo carga en memoria y responde por HTTP.

### Cómo debe dimensionarse

| Requisito | En el lab |
|-----------|-----------|
| Cabe en la memoria del puesto | Techo de 2 GB para el contenedor `llm` |
| Responde a tiempo | Una respuesta corta en menos de un segundo en CPU |
| No sale de la fábrica | La dirección es `http://llm:8088`, el propio puesto |

### Qué se gana y qué se pierde

| | Modelo local pequeño (este) | Servicio externo grande |
|--|------------------------------|-------------------------|
| Datos | No salen del puesto | Salen de la fábrica |
| Disponibilidad | No depende de internet | Depende de la conexión y del proveedor |
| Calidad de las respuestas | Limitada: se equivoca y no siempre obedece | Mucho mejor |
| Coste | El del equipo | Por uso |

### Cómo se decide el tamaño

- Se empieza por la **condición de la planta** (aquí: ningún dato sale de la fábrica, sin GPU).
- Se elige el **modelo más capaz que responda a tiempo** en el equipo real.
- Se compensa su tamaño dándole **[buen contexto](../glosario/04-ia-generativa.md#contexto)** (los documentos de la planta, en M05-03) en lugar de esperar que lo sepa todo.

### En una frase

> 🔑 «Local» significa que la pregunta y la respuesta no salen del puesto. El precio es un modelo más pequeño, y eso se compensa con buen contexto.
