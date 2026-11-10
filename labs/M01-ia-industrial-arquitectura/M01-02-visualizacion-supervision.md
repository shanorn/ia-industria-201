# M01-02 — Visualización y supervisión de procesos

[← Página anterior](M01-01-arquitectura-datos.md) · [Siguiente página →](M01-03-metricas-alertas.md)

> Práctica del módulo. La teoría y la demostración están en el [README del módulo](README.md).
>
> Lanza los comandos desde la carpeta `infra/` del repositorio. Un paso que cuadra termina con una línea que empieza por `OK`.

### Objetivo

Comprender qué es la **[observabilidad](../glosario/02-observabilidad.md#observabilidad) de un proceso**: qué señales tiene que emitir para poder entender su estado, cómo se convierten en indicadores que se interpretan de un vistazo, qué límites tiene vigilar con un umbral fijo y cómo se completa.

### Prerrequisitos

- M01-01 hecho: mosquitto, sensor y archivador en marcha.
- RAM adicional del panel: hasta 512 MB. Puerto 8501 libre.
- Para la sección «IA sobre el dato»: unos 2 GB más para el contenedor `llm` y, si aún no está en `infra/modelos/`, salida a Hugging Face para bajar el modelo (~470 MB, una sola vez).

### Qué está pasando

Para saber si el proceso va bien no basta con que la máquina funcione: tiene que **emitir señales** (sus registros, con pieza, hora y medidas) y alguien tiene que poder **interpretarlas**. A esa capacidad de entender el estado de un sistema a partir de lo que emite se la llama **observabilidad**.

En este lab trabajas la capa que convierte esas señales en **indicadores**: el **panel** del puesto de supervisión. Se coloca al final de la arquitectura del M01-01:

```
 estación ──▶ broker ──▶ archivador ──▶ historial.sqlite ──▶ panel ──▶ operario
```

El panel **no escucha al [broker](../glosario/01-datos-arquitectura.md#broker)**: lee el [histórico](../glosario/01-datos-arquitectura.md#historico). Enseña tres indicadores de la última [carcasa](../glosario/01-datos-arquitectura.md#pieza), la tendencia de las últimas 120 lecturas y un aviso con un **margen fijo de 70 °C**, el del procedimiento de la estación. Es una regla escrita por una persona, no un modelo.

Conviene distinguir tres cosas que se parecen:

| | Pregunta que responde | Cuándo | En el curso |
|--|-----------------------|--------|-------------|
| **Supervisión** | ¿Está todo dentro de lo normal ahora? | En tiempo real | Este panel |
| **Observabilidad** | ¿Puedo entender qué le pasa al proceso con lo que emite, incluso ante preguntas no previstas? | En tiempo real y después | Panel + logs (M01-01, paso 3) + histórico consultable con `lab sql` |
| **Análisis a posteriori** | ¿Qué pasó, por qué y con qué se relaciona? | Después | Preparación de datos y modelos (M02 y M03) |

Y una precisión: el panel enseña **indicadores de proceso** (temperatura, vibración, lecturas fuera de margen). No enseña **[KPI](../glosario/02-observabilidad.md#kpi) de producción** como el OEE, el [tiempo de ciclo](../glosario/01-datos-arquitectura.md#tiempo-ciclo) o la tasa de rechazo. Vigila la salud del proceso, no el rendimiento de la línea.

| En la realidad | En este laboratorio |
|----------------|---------------------|
| [SCADA](../glosario/01-datos-arquitectura.md#scada), HMI o un panel tipo Grafana sobre el histórico | Contenedor `panel` (Streamlit), código en `infra/linea/panel.py` |
| Margen de operación del procedimiento | 70 °C, en `infra/linea/config.py` |

### 1 — Arrancar el panel

**Qué ocurre:** enciendes la pantalla del puesto de supervisión. Cada vez que se abre o se recarga, lee las últimas 120 lecturas del histórico y las convierte en indicadores.

```bash
# Arranca el panel
docker compose up -d panel
```

Abre <http://localhost:8501> en Chrome.

**Resultado esperado:** la pieza actual, la temperatura, la vibración, el recuadro del margen y la serie de las últimas lecturas.

![Panel de EST-01 con pieza, temperatura, vibración, margen y serie](../img/M01-02-panel.png)

**Cómo se lee:**

| Elemento | Qué es |
|----------|--------|
| Pieza, Temperatura, Vibración | La última carcasa guardada en el histórico |
| Recuadro verde o rojo | Si **la última** lectura está por debajo o por encima del margen |
| «Lecturas fuera en esta ventana» | Cuántas de las **últimas 120** lecturas pasan del margen |
| Gráfica | Temperatura y vibración de las últimas 120 lecturas |

El panel no se actualiza solo: recarga la página para ver la carcasa más reciente.

### 2 — Comprobar el dato detrás del dibujo

**Qué ocurre:** ya has visto el panel con tus ojos. Ahora usas un comando de ayuda que comprueba que el panel responde y cuenta, directamente en el histórico, cuántas lecturas pasan de 70 °C.

```bash
# Pide la página del panel y cuenta lecturas por encima del margen en el histórico
docker compose --profile lab run --rm --no-deps lab m01-02
```

📋 Ficha del comando [`m01-02`](../comandos-lab.md#m01-02): qué hace, qué lee, qué escribe y cuándo da `OK`.

**Resultado esperado** (cambia el número de lecturas):

```text
panel_http=200 lecturas=29 fuera_de_margen=0 umbral=70.0
OK m01-02: panel vivo, 29 lecturas, 0 fuera de 70 C
```

Fíjate en que `m01-02` cuenta en **todo el histórico**, y el panel solo en las **últimas 120**. Con el margen en 70 °C los dos dan 0, porque la estación nunca pasa de 63 °C. En el apartado «Experimenta» verás qué pasa cuando no es así.

<details>
<summary>Qué hace por dentro (<code>infra/linea/cli.py</code>)</summary>

```python
respuesta = httpx.get(PANEL_URL)                       # el panel tiene que contestar (200)
df = pd.read_sql_query("SELECT temperatura_c FROM lecturas", con)   # TODO el histórico
fuera = int((df["temperatura_c"] > UMBRAL_TEMPERATURA).sum())       # regla fija: 70 °C
```

</details>

## Comprueba tu entendimiento

**Qué mira el recuadro**

Si la carcasa anterior pasó de 70 °C pero la última no, ¿de qué color está el recuadro?

→ Verde. El color solo mira **la última** lectura. La anterior aparece en el [contador](../glosario/02-observabilidad.md#metrica) «Lecturas fuera en esta ventana».

## Investiga: calcula tú los indicadores

Un indicador no es magia: es una consulta sobre el histórico. Vas a calcular con `lab sql` (el comando de ayuda para consultar el histórico que usaste en el M01-01) lo mismo que enseña el panel.

📋 Ficha del comando [`sql`](../comandos-lab.md#sql).

### 1 — La última carcasa

**Qué ocurre:** pides la fila más reciente del histórico, que es la que enseñan los tres indicadores de arriba.

```bash
docker compose --profile lab run --rm --no-deps lab sql \
  "SELECT pieza_id, ts, temperatura_c, vibracion_mm_s FROM lecturas ORDER BY id DESC LIMIT 1"
```

**Resultado esperado** (cambian los valores):

```text
pieza_id                        ts  temperatura_c  vibracion_mm_s
   P0153 2026-11-05T12:12:27+00:00          62.97            0.22
```

Recarga el panel: enseña la misma carcasa, o una posterior si ha pasado algún segundo.

### 2 — La ventana del panel

**Qué ocurre:** reproduces el contador del panel: cuántas de las últimas 120 lecturas pasan del margen, y la temperatura media de esa ventana.

```bash
docker compose --profile lab run --rm --no-deps lab sql \
  "SELECT COUNT(*) AS lecturas, ROUND(AVG(temperatura_c), 2) AS media, SUM(temperatura_c > 70) AS fuera_de_margen
   FROM (SELECT temperatura_c FROM lecturas ORDER BY id DESC LIMIT 120)"
```

**Resultado esperado:**

```text
 lecturas  media  fuera_de_margen
      120  62.04                0
```

### 3 — Leer la gráfica

**Qué ocurre:** miras la gráfica del panel con atención. La temperatura dibuja una línea con dientes entre 61 y 63 °C. La vibración parece una línea plana pegada al 0.

**Pregunta:** ¿la vibración no cambia?

<details>
<summary>Ver solución</summary>

Sí cambia, entre 0,22 y 0,28 mm/s, pero la gráfica usa **la misma escala** para las dos señales, de 0 a 63. Con esa escala, una variación de 0,06 no se ve.

```bash
docker compose --profile lab run --rm --no-deps lab sql \
  "SELECT MIN(vibracion_mm_s) AS minima, MAX(vibracion_mm_s) AS maxima FROM lecturas"
```

```text
 minima  maxima
   0.22   0.28
```

Interpretar un panel también es desconfiar de cómo está dibujado: dos señales con unidades distintas necesitan escalas distintas.

</details>

## Experimenta: mueve el margen

**Qué ocurre:** el margen de 70 °C está tan lejos de lo que hace la estación (61–63 °C) que nunca salta. Vas a bajarlo a **62,5 °C** para ver cómo se comporta el panel cuando sí hay lecturas fuera.

**Antes de hacerlo, predice:**
1. ¿De qué color se pondrá el recuadro?
2. ¿Darán el mismo número el panel y `m01-02`?

Abre `infra/linea/config.py` en VS Code y cambia esta línea:

```python
UMBRAL_TEMPERATURA = 70.0
```

por:

```python
UMBRAL_TEMPERATURA = 62.5
```

Reinicia el panel para que lea el valor nuevo, y lanza la comprobación:

```bash
docker compose restart panel
docker compose --profile lab run --rm --no-deps lab m01-02
```

**Resultado esperado** (cambian los números):

```text
panel_http=200 lecturas=181 fuera_de_margen=51 umbral=62.5
OK m01-02: panel vivo, 181 lecturas, 51 fuera de 62 C
```

Recarga el panel:

![Panel con el margen en 62,5 °C: recuadro verde y 35 lecturas fuera en la ventana](../img/M01-02-margen-625.png)

**Cómo se lee:**

- **El recuadro puede seguir verde** aunque haya decenas de lecturas por encima: solo mira la última carcasa, y la temperatura sube y baja en dientes de sierra. Recarga varias veces y lo verás cambiar entre verde y rojo.
- **El panel dice 35 y `m01-02` dice 51.** No es un error: el panel cuenta en las últimas 120 lecturas, y `m01-02` en todo el histórico. Dos indicadores con el mismo nombre y distinta ventana dan números distintos.
- **El panel escribe «62 °C»** en lugar de 62,5 °C: redondea al mostrar. Un detalle así, en planta, genera discusiones sobre si una pieza estaba dentro o fuera.

**Deja el margen como estaba** antes de seguir:

```python
UMBRAL_TEMPERATURA = 70.0
```

```bash
docker compose restart panel
```

## Reto

### 1 — Quita el panel

Para el panel y recarga la página. ¿Se pierden datos?

```bash
docker compose stop panel
```

<details>
<summary>Ver solución</summary>

La página deja de abrir, pero los registros siguen archivándose: el panel no es el origen. Para recuperarlo:

```bash
docker compose start panel
```

</details>

### 2 — Quita el archivador

Ahora para el archivador, espera 20 segundos y recarga el panel varias veces. ¿Qué ve el operario?

```bash
docker compose stop archivador
```

<details>
<summary>Ver solución</summary>

El panel **sigue en verde**, con la misma pieza y la misma temperatura cada vez que recargas. Parece que todo va bien, pero los datos están congelados: el histórico no crece y el panel enseña lo último que hubo. Nada avisa de que los indicadores no son actuales.

Es el fallo más peligroso de un sistema de supervisión: **un «todo normal» que en realidad es «no sé nada»**. Vuelve a arrancarlo:

```bash
docker compose start archivador
```

</details>

## Mejora el panel: ¿el dato está vivo?

**Qué ocurre:** vas a añadir al panel lo que le faltaba en el reto 2: la **[hora del último dato](../glosario/02-observabilidad.md#frescura)** y un aviso si lleva más de 10 segundos sin llegar nada. Es una mejora de observabilidad: el panel no solo vigila el proceso, también vigila que su propia información esté al día.

Abre `infra/linea/panel.py` en VS Code. Busca esta línea:

```python
c3.metric("Vibración (mm/s)", f"{ultimo['vibracion_mm_s']:.3f}")
```

y añade debajo:

```python
# ¿El dato está vivo? Hora del último registro y aviso si lleva más de 10 s sin llegar
from datetime import datetime, timezone
retraso = (datetime.now(timezone.utc) - datetime.fromisoformat(ultimo["ts"])).total_seconds()
if retraso > 10:
    st.warning(f"Sin datos nuevos desde hace {retraso:.0f} s (último: {ultimo['ts']}). Los indicadores no son actuales.")
else:
    st.caption(f"Último dato: {ultimo['ts']} (hace {retraso:.0f} s)")
```

Reinicia el panel y repite el reto 2:

```bash
docker compose restart panel
docker compose stop archivador
# … espera unos 15 segundos y recarga el panel …
docker compose start archivador
```

**Resultado esperado** con el archivador parado:

![Panel con aviso amarillo: sin datos nuevos desde hace 16 s](../img/M01-02-sin-datos.png)

**Cómo se lee:** el aviso amarillo dice lo que antes nadie decía: los indicadores no son actuales. Fíjate en que el recuadro de margen sigue en verde debajo. Son dos preguntas distintas: «¿el proceso va bien?» y «¿me puedo fiar de lo que veo?».

Con el archivador en marcha, el aviso desaparece y aparece una línea gris con la hora del último dato.

Si quieres volver al panel original: `git checkout linea/panel.py` y `docker compose restart panel`.

## IA sobre el dato: un resumen para el operario

**Qué ocurre:** en lugar de mirar el panel, el operario le pide al **[modelo de lenguaje](../glosario/04-ia-generativa.md#llm) local** (el que verás a fondo en el M05) que le diga en dos frases cómo va la estación. El comando `lab resumen` toma las últimas 60 lecturas del histórico, calcula unas medias y se las pasa al modelo para que redacte.

Necesita el modelo en marcha. Si tienes [Prometheus](../glosario/02-observabilidad.md#prometheus) arrancado, puedes pararlo un momento para dejar memoria:

```bash
# baja el fichero del modelo si aún no lo tienes (~470 MB, solo la primera vez)
docker compose run --rm modelo
docker compose up -d llm
# espera a que conteste: {"estado":"ok",...}
curl -s http://localhost:8088/salud
```

📋 Ficha del comando [`resumen`](../comandos-lab.md#resumen).

### 1 — Pedir el resumen

```bash
docker compose --profile lab run --rm --no-deps lab resumen
```

**Resultado esperado** (cambian los valores y la redacción):

```text
datos: {"ultima_pieza": "P0636", "hora_ultimo_dato": "2026-11-06T01:18:18+00:00", "lecturas": 60, "temperatura_media_c": 62.08, "temperatura_max_c": 63.21, "vibracion_media_mm_s": 0.25, "corriente_media_a": 4.04, "lecturas_por_encima_de_70c": 0}
resumen: La estación EST-01 está en funcionamiento y tiene 60 lecturas. La temperatura media es de 62.08°C, la temperatura máxima es de 63.21°C, …
```

`datos` es lo que calcula el código; `resumen`, lo que redacta el modelo con esos datos.

### 2 — Pedirlo con los datos congelados

**Qué ocurre:** repites lo del reto 2: paras el archivador y, pasado un minuto y medio, vuelves a pedir el resumen.

**Predice:** ¿se dará cuenta el modelo de que los datos son viejos?

```bash
docker compose stop archivador
# … espera 90 segundos …
docker compose --profile lab run --rm --no-deps lab resumen
```

**Resultado esperado:**

```text
resumen: La estación EST-01 tiene 60 lecturas, la temperatura media es de 62.07°C, la temperatura máxima es de 63.23°C, …
```

El modelo cuenta tan tranquilo cómo va la estación con datos de hace minuto y medio. No tiene forma de saberlo: nadie le ha dado la hora.

### 3 — Darle la hora

**Qué ocurre:** `con-hora` añade a los datos la hora actual y los segundos que han pasado desde el último dato.

```bash
docker compose --profile lab run --rm --no-deps lab resumen con-hora
```

**Resultado esperado:**

```text
datos: {…, "hora_actual": "2026-11-06T01:20:07+00:00", "segundos_desde_ultimo_dato": 97}
resumen: La estación EST-01 está en funcionamiento y tiene una temperatura media de 62.07°C, … y no ha tenido lecturas por encima de 70°C en los últimos 60 minutos.
```

**Cómo se lee:** con el dato delante (`97` segundos sin datos), el modelo **sigue diciendo que la estación está en funcionamiento**. Y además [se inventa](../glosario/04-ia-generativa.md#alucinacion) «los últimos 60 minutos»: son 60 lecturas, es decir, 60 segundos. Un modelo de lenguaje redacta con fluidez, pero **no razona** sobre si sus datos tienen sentido.

### 4 — Que lo compruebe el código

**Qué ocurre:** `comprobado` hace lo mismo que tu mejora del panel: antes de preguntar al modelo, el **código** mira si el último dato tiene más de 10 segundos. Si es así, no le deja hablar.

```bash
docker compose --profile lab run --rm --no-deps lab resumen comprobado
docker compose start archivador
```

**Resultado esperado:**

```text
resumen: Sin datos nuevos desde hace 34 s (último: 2026-11-06T01:23:18+00:00). No se puede decir cómo va la estación: revisar el archivador.
OK resumen: comprobado por código: datos no actuales, no se pregunta al modelo
```

**Cómo se lee:** la comprobación que importa la hace una regla sencilla y fiable, no el modelo. El modelo solo redacta cuando el dato es bueno. Es la misma idea que verás en el [agente](../glosario/04-ia-generativa.md#agente) del M07-03: **el código mide y decide; el modelo pone las palabras**.

## Constrúyelo tú: tus propios indicadores

**Qué está pasando:** el panel calcula sus indicadores por dentro y solo enseña el resultado. Ahora los calculas tú, uno a uno, leyendo el mismo histórico que lee el panel: la última carcasa, cuánto hace que llegó, cuántas lecturas salen del margen y a qué ritmo fabrica la estación. Al final tendrás un informe de una línea que, a diferencia del panel original, **dice cuándo los datos no son actuales**.

**Cómo se trabaja en cada paso:**

1. Lees para qué es el paso y qué hace el bloque.
2. Copias el bloque y lo pegas en el fichero, **debajo del comentario de ese paso** (`# --- PASO N …`), en lugar de la línea `# (pega aquí el bloque del paso N)`.
3. Guardas y ejecutas el script. Cada ejecución repite todo desde el principio, así que la salida crece paso a paso: lo nuevo aparece al final.

### 1 — Abrir el fichero y ejecutarlo tal cual

**Para qué:** asegurarte de que tu código lee el mismo histórico que el panel.

**Qué ocurre:** abres en VS Code el fichero [`infra/construye/m01_02_mis_indicadores.py`](../../infra/construye/m01_02_mis_indicadores.py). Arriba están las **decisiones** (`VENTANA`, `MARGEN_C`, `MAX_ANTIGUEDAD_S`, `CICLO_NOMINAL_S`); debajo, el paso 1 ya escrito: abre `historial.sqlite` en solo lectura y trae las últimas `VENTANA` lecturas. Lo ejecutas sin tocar nada.

```bash
# Ejecuta tu script con el Python del contenedor lab (-W ignore oculta avisos de las librerías)
docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m01_02_mis_indicadores.py
```

**Resultado esperado:**

```text
lecturas leídas del histórico: 120
```

**Cómo se lee:** has leído las 120 lecturas más recientes, las mismas que dibuja el panel. Abrir en **solo lectura** (`mode=ro`) es lo que hace cualquier pantalla de supervisión: mirar sin poder estropear el histórico. `--entrypoint python` hace que el contenedor `lab` ejecute tu fichero; `/data/` dentro es `infra/data/` en tu equipo.

### 2 — La última carcasa y cuánto hace que llegó

**Para qué:** saber de cuándo es lo que estás a punto de enseñar al operario.

**Qué ocurre:** tomas la última lectura, enseñas su carcasa y su temperatura, y calculas cuántos segundos han pasado desde su hora (`ts`) hasta ahora.

Pega debajo de `# --- PASO 2`:

```python
ultima = df.iloc[-1]
hora = datetime.fromisoformat(ultima["ts"])                    # la hora con la que la guardó el archivador
antiguedad_s = (datetime.now(timezone.utc) - hora).total_seconds()
print(f"última carcasa: {ultima['pieza_id']} a {ultima['temperatura_c']} °C, hace {antiguedad_s:.0f} s")
```

Ejecuta de nuevo (el mismo comando del paso 1).

**Resultado esperado** (línea nueva; cambian la carcasa y la temperatura):

```text
última carcasa: P0277 a 62.32 °C, hace 1 s
```

**Cómo se lee:** con la línea funcionando, la última carcasa tiene uno o dos segundos. Ese número, la **antigüedad del dato**, es justo lo que el panel original no enseña.

### 3 — Decidir si el dato está vivo

**Para qué:** que el informe diga por sí solo si se puede confiar en él.

**Qué ocurre:** comparas la antigüedad con `MAX_ANTIGUEDAD_S`. Si es mayor, el dato está **congelado**: lo que enseñes es lo último que hubo, no lo que pasa ahora.

Pega debajo de `# --- PASO 3`:

```python
vivo = antiguedad_s <= MAX_ANTIGUEDAD_S
estado = "VIVO" if vivo else f"CONGELADO (sin datos nuevos desde hace {antiguedad_s:.0f} s)"
print(f"estado del dato: {estado}")
```

**Resultado esperado** (líneas nuevas):

```text
estado del dato: VIVO
```

**Cómo se lee:** ahora el programa distingue «todo normal» de «no sé nada», que en el reto 2 el panel confundía. Lo provocarás en el paso 7.

### 4 — Lecturas fuera de margen

**Para qué:** resumir en un número si la temperatura se está saliendo.

**Qué ocurre:** cuentas cuántas de las lecturas de la ventana superan `MARGEN_C` y calculas la temperatura media.

Pega debajo de `# --- PASO 4`:

```python
fuera = int((df["temperatura_c"] > MARGEN_C).sum())
print(f"temperatura media={df['temperatura_c'].mean():.2f} °C  lecturas fuera de margen={fuera} de {len(df)}")
```

**Resultado esperado** (línea nueva; cambia la media):

```text
temperatura media=62.05 °C  lecturas fuera de margen=0 de 120
```

**Cómo se lee:** es el indicador «lecturas fuera» del panel, calculado por ti. Con la estación en su régimen normal, en torno a 62 °C, ninguna lectura pasa de 70.

### 5 — El ritmo de la estación

**Para qué:** añadir un indicador de producción, que el panel no tiene.

**Qué ocurre:** calculas el tiempo de ciclo medio de la ventana y lo comparas con el nominal. El cociente es el **rendimiento** del OEE: cuánto se fabrica frente a lo que se podría.

Pega debajo de `# --- PASO 5`:

```python
ciclo_medio = df["tiempo_ciclo_s"].mean()
rendimiento = CICLO_NOMINAL_S / ciclo_medio                    # 1,0 = al ritmo previsto
print(f"tiempo de ciclo medio={ciclo_medio:.2f} s  rendimiento={rendimiento:.0%}")
```

**Resultado esperado** (línea nueva; cambian los números):

```text
tiempo de ciclo medio=1.07 s  rendimiento=93%
```

**Cómo se lee:** un ciclo medio de 1,07 s deja el rendimiento en el 93 %: en esa ventana hubo una microparada, que alarga el ciclo de una carcasa varios segundos y sube la media. Es un KPI de producción, distinto de los indicadores de proceso que enseña el panel.

### 6 — Un informe de una línea

**Para qué:** dar al operario todo lo anterior de un vistazo, sin que pueda leer como actual un dato congelado.

**Qué ocurre:** juntas los indicadores en una línea. Si el dato está congelado, el informe lo dice **primero** y no enseña los indicadores como si fueran de ahora.

Pega debajo de `# --- PASO 6`:

```python
if vivo:
    print(f"INFORME EST-01: {ultima['pieza_id']} {ultima['temperatura_c']} °C | fuera de margen {fuera}/{len(df)} | rendimiento {rendimiento:.0%}")
else:
    print(f"INFORME EST-01: SIN DATOS ACTUALES desde hace {antiguedad_s:.0f} s; último dato {ultima['pieza_id']} {ultima['temperatura_c']} °C")
```

**Resultado esperado** (línea nueva):

```text
INFORME EST-01: P0277 62.32 °C | fuera de margen 0/120 | rendimiento 93%
```

**Cómo se lee:** el informe enseña lo mismo que el panel y una cosa más, la que lo hace fiable: si los datos son de ahora.

### 7 — Decide tú: congela el dato

**Para qué:** comprobar que tu informe avisa donde el panel no avisaba.

**Qué ocurre:** repites el reto 2: paras el archivador, esperas 20 segundos y ejecutas tu script. Después vuelves a arrancarlo.

```bash
docker compose stop archivador
sleep 20
docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m01_02_mis_indicadores.py
docker compose start archivador
```

**Resultado esperado** (líneas que cambian; cambian los números):

```text
última carcasa: P0287 a 60.98 °C, hace 22 s
estado del dato: CONGELADO (sin datos nuevos desde hace 22 s)
temperatura media=62.03 °C  lecturas fuera de margen=0 de 120
tiempo de ciclo medio=1.07 s  rendimiento=93%
INFORME EST-01: SIN DATOS ACTUALES desde hace 22 s; último dato P0287 60.98 °C
```

**Cómo se lee:** tu informe dice **SIN DATOS ACTUALES** y cuánto tiempo lleva así, mientras el panel original seguía en verde. La diferencia son tres líneas de código: comparar la hora del último dato con la hora actual, lo mismo que añadiste al panel en «Mejora el panel».

### 8 — Decide tú: cuándo es «demasiado viejo»

**Para qué:** elegir con criterio a partir de cuántos segundos un dato deja de ser actual.

**Qué ocurre:** cambias `MAX_ANTIGUEDAD_S = 10` por `MAX_ANTIGUEDAD_S = 2` y ejecutas tu script muchas veces seguidas durante unos minutos, con la línea funcionando y sin provocar nada. El bucle de abajo lo lanza 45 veces y cuenta cuántas sale cada estado.

```bash
# 45 ejecuciones seguidas; se queda con la línea del estado y cuenta cuántas veces sale cada una
for i in $(seq 45); do
  docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore \
    /construye/m01_02_mis_indicadores.py | grep "estado del dato"
  sleep 1
done | sort | uniq -c
```

**Resultado esperado** (cambian los números):

```text
     43 estado del dato: VIVO
      1 estado del dato: CONGELADO (sin datos nuevos desde hace 6 s)
      1 estado del dato: CONGELADO (sin datos nuevos desde hace 4 s)
```

**Cómo se lee:** sin fallo ninguno, dos veces de 45 dice **CONGELADO**: coincidieron con una microparada, que deja la estación de 3 a 8 s sin fabricar. El dato estaba vivo, solo que la máquina estaba parada. El límite tiene que ser mayor que el silencio normal más largo, incluidas las paradas cortas: con 10 s no salta en una microparada y avisa enseguida de un archivador caído. Vuelve a dejar `MAX_ANTIGUEDAD_S = 10`.
## Errores frecuentes

| Síntoma | Causa probable | Cómo arreglarlo |
|---------|----------------|-----------------|
| <http://localhost:8501> no abre | el panel no está en marcha o el puerto está ocupado | `docker compose ps` y `docker compose logs panel` |
| El panel dice que no hay histórico | el archivador acaba de crear la base | espera unos segundos y recarga |
| El cambio de margen no se ve | el panel no se reinició | `docker compose restart panel` |
| El panel da un error en rojo tras editar `panel.py` | falta un paréntesis o la sangría no cuadra | compara con el bloque del lab, o `git checkout linea/panel.py` |
| `lab resumen` da error de conexión con `http://llm:8088` | el modelo no está en marcha o sigue cargando | `docker compose up -d llm` y espera a `/salud` |
| `docker compose logs llm` dice `Falta el modelo en /modelos/…` | no se ha bajado el fichero del modelo | `docker compose run --rm modelo` y vuelve a `docker compose up -d llm` |
| `NameError: name '…' is not defined` | pegaste un bloque en el hueco de otro paso, o te saltaste uno | cada bloque va debajo de su `# --- PASO N`, en orden |
| `IndentationError` | el bloque quedó con espacios de más o de menos al pegarlo | las líneas de cada bloque empiezan en la columna 0, salvo las de dentro de `for`, `if`, `while` y `def` |
| `ModuleNotFoundError` | ejecutaste el script con el Python de tu equipo | ejecútalo con el comando del paso 1, dentro del contenedor `lab` |
| `sqlite3.OperationalError: unable to open database file` | no hay histórico todavía | haz antes el M01-01: arranca mosquitto, sensor y archivador |

## Conclusiones

### Qué es la observabilidad de un proceso

Es poder entender el estado del proceso a partir de lo que emite. Necesita tres cosas: que la máquina **emita señales** con identidad y hora, que se **guarden** y que haya una capa que las **interprete**. El panel es esa última capa: convierte el histórico en indicadores que se entienden de un vistazo.

```
 señales (registros) ──▶ histórico ──▶ indicadores (panel) ──▶ interpretación (persona)
```

### Cómo debe ser un panel útil

| Requisito | En el panel de EST-01 |
|-----------|-----------------------|
| Muestra el estado actual | Pieza, temperatura y vibración de la última carcasa |
| Muestra la tendencia | Gráfica de las últimas 120 lecturas |
| Avisa con un criterio explícito | Margen del procedimiento, en `config.py` |
| Cada indicador se puede reproducir | Lo has calculado tú con `lab sql` |
| Dice si se puede fiar de él | Solo después de tu mejora: hora del último dato |

### Sus límites y cómo los has visto

| Límite | Cómo lo has visto | Qué provoca |
|--------|-------------------|-------------|
| El color solo mira la última lectura | Con 62,5 °C, verde con 35 lecturas fuera | Un vistazo rápido no ve que el proceso roza el margen |
| Indicadores con distinta ventana | Panel 35, `m01-02` 51 | Dos personas discuten con números «del mismo indicador» |
| Escala compartida | La vibración parece plana | Una variación real no se ve |
| Datos congelados sin aviso | Reto 2: archivador parado y panel en verde | «Todo normal» cuando en realidad no llega nada |
| Regla fija sobre una sola señal | Solo mira la temperatura | No ve combinaciones raras de varias señales |
| La IA no ve que el dato es viejo | `lab resumen` con el archivador parado, incluso dándole la hora | Un resumen fluido y falso |

### Cómo se mejora

| Límite | Mejora |
|--------|--------|
| Datos congelados | Hora del último dato y aviso de dato no actual (lo has hecho) |
| Ventanas distintas | Decir siempre en qué ventana se calcula cada indicador |
| Escala compartida | Una gráfica por señal, cada una con su escala |
| Aviso que solo ve quien mira | [Alertas](../glosario/02-observabilidad.md#alerta) que llegan a alguien y se registran (M03-02 y M07-02) |
| Regla fija sobre una señal | Detectores y modelos que miran varias señales a la vez (M03) |
| Un modelo de lenguaje que resume datos viejos sin avisar | Comprobar con código que el dato está al día antes de dejarle hablar (`resumen comprobado`) |

### En una frase

> 🔑 Un panel solo es observabilidad si cada indicador se puede reproducir y si te dice cuándo no te puedes fiar de él.
