# Entorno de la línea EST-01

Los laboratorios ocurren en una **estación de mecanizado simulada** (EST-01). No hay PLC, cámara ni nube del cliente: cada señal nace en un contenedor y se puede volver a generar.

Trabaja siempre desde esta carpeta (`infra/`).

```bash
docker compose up -d mosquitto sensor archivador
docker compose --profile lab run --rm --no-deps lab m01-01
```

## Qué proceso es cada contenedor

| Servicio | Proceso | Puerto en tu máquina | Qué emula |
|----------|---------|----------------------|-----------|
| `mosquitto` | Broker MQTT | 1883 | El transporte de eventos de la estación |
| `sensor` | Publica un ciclo por segundo y escribe `/data/estado.json`. Métricas en <http://localhost:9102/metrics> | 9102 | El origen: husillo, vibración y corriente |
| `archivador` | Se suscribe a `linea/est01/ciclo` y guarda SQLite. Métricas en <http://localhost:9101/metrics> | 9101 | El histórico del turno |
| `calidad` | Se suscribe a `linea/est01/ciclo`, inspecciona cada carcasa con un criterio oculto y guarda el resultado en `calidad.sqlite` | — | El sistema de calidad de la planta |
| `opcua` | Servidor OPC-UA que lee el mismo estado | 4840 | Un equipo que ya habla OPC-UA |
| `modbus` | Esclavo Modbus TCP. La temperatura va en décimas en el registro 0. El registro 10 es el paro de seguridad y **nadie lo escribe** | 1502 (en planta el puerto habitual es 502) | Un automatismo sencillo |
| `panel` | Streamlit sobre el SQLite | 8501 | El panel del turno |
| `llm` | Modelo generativo en local (Qwen2.5 0.5B, GGUF Q4) | 8088 | Asistencia, sin salir a una API |
| `api` | FastAPI con el clasificador entrenado en M03 | 8000 | El servicio de inferencia en operación |
| `prometheus` | Recoge métricas de `sensor` (:9102) y `archivador` (:9101) cada 5 s y evalúa las alertas de `prometheus/alertas.yml` | 9090 | El sistema de monitorización y alarmas |
| `lab` | No se queda arrancado. `docker compose run` ejecuta un paso | — | Tus comandos de laboratorio |

El estado vivo está en `infra/data/` (no se versiona). El modelo generativo está en `infra/modelos/` (el fichero `.gguf` tampoco se versiona).

## De dónde sale el dato

| Dato | Origen | Cómo se crea |
|------|--------|----------------|
| Ciclo en vivo | `sensor` | Un mensaje por carcasa en `linea/est01/ciclo`: unas 60 por minuto, con tiempo de ciclo variable (±10 %), rampa de arranque y microparadas de 3–8 s cada ~2,5 min. Las medidas son deterministas; el ritmo, no |
| Misma señal por OPC-UA y Modbus | `opcua` y `modbus` leen `estado.json` | No hay un segundo proceso físico |
| Histórico para entrenar | `python -m linea.cli m02-03` | 800 piezas sintéticas, con huecos, temperaturas en décimas y algún 9999 |
| Imágenes de calidad | `m04-01` | 64×64 generadas con Pillow: pieza gris y, si hay defecto, un rayón blanco |
| Procedimiento del asistente | `linea/docs/procedimiento-est01.md` | Texto fijo del laboratorio. El par de apriete es 12 N·m |
| Modelo de lenguaje | descarga única | Ver M05 |

Nada de esto es telemetría de una planta real.

## Cómo levantar los emuladores

No hace falta tenerlos todos a la vez.

```bash
# Dato en vivo: MQTT, origen y archivo
docker compose up -d mosquitto sensor archivador

# Las otras dos puertas al mismo valor
docker compose up -d opcua modbus

# Panel
docker compose up -d panel

# Generativo (M01-02, M02-03 y M05): si falta el fichero del modelo, el servicio `modelo` lo baja antes (~470 MB, una vez)
docker compose up -d llm

# Servicio del clasificador (después de M03-03)
docker compose up -d api

docker compose ps
docker compose logs -f sensor
docker compose stop sensor    # provoca el hueco de telemetría
docker compose start sensor
```

Un paso de laboratorio:

```bash
docker compose --profile lab run --rm --no-deps lab m01-01
```

El comando imprime una línea `OK m01-01: ...` cuando el paso cuadra.

## Requisitos del curso

El puesto se prepara antes de clase. El día del laboratorio no se instala nada en el equipo: solo se usan los contenedores.

El puesto de aula es Linux en el propio equipo. Hardware, software, red y la prueba de aceptación están en [PUESTO.md](PUESTO.md). Desde esta carpeta, `./comprobar-puesto.sh` tiene que imprimir `PUESTO_OK`.

Los techos de cada contenedor son los `mem_limit` del `docker-compose.yml`. Cuando corre el modelo generativo hacen falta 8 GB libres para Docker. Python en el host, GPU y webcam quedan fuera.

La imagen de la línea se construye o se baja al empezar. Mosquitto sale de Docker Hub. El fichero de Qwen (~470 MB) se baja de Hugging Face una vez, a `infra/modelos/`. Los laboratorios no llaman a una API de pago: el modelo corre en el contenedor `llm`.

Cualquier otra herramienta del curso (visión, flujos, trazas del modelo) es otro contenedor que se baja de un registry. No se instala nada más en el puesto.

En el M05, detén el panel (`docker compose stop panel`) antes de arrancar `llm`.

## Requisitos por laboratorio

| Lab | Contenedores que tienen que estar arriba | RAM de esos contenedores | Disco extra | Red |
|-----|------------------------------------------|--------------------------|-------------|-----|
| M01-01 | mosquitto, sensor, archivador | ~0,5 GB | el histórico crece unos KB/s | no |
| M01-02 | los anteriores + panel | ~1 GB | igual | no |
| M01-03 | mosquitto, sensor, archivador + prometheus | ~0,8 GB | las métricas, unos MB | no |
| M02-01 | mosquitto, sensor | ~0,3 GB | — | no |
| M02-02 | los anteriores + opcua + modbus | ~0,7 GB | — | no |
| M02-03 | solo `lab` (genera CSV) | ~0,4 GB en el run | < 5 MB | no |
| M02-04 | mosquitto, sensor, archivador + calidad, unos minutos | ~0,7 GB | `calidad.sqlite` y `dataset_linea.csv`, pocos MB | no |
| M03-01 a M03-03 | `lab` y el CSV de M02-03 | ~0,5 GB | el `.joblib` | no |
| M03-04 | `lab` y el `dataset_linea.csv` de M02-04 | ~0,5 GB | el `.joblib` | no |
| M04-01 a M04-04 | `lab` | ~0,5 GB | ~80 PNG pequeñas | no |
| M05-01 a M05-04 | `llm` (+ sensor en M05-04) | hasta 2 GB | ~470 MB del GGUF | solo la primera descarga |
| M05-05 | solo `lab` | hasta 2 GB | ~1,7 GB más (dos modelos abiertos) | descarga en el paso 1 |
| M01-02 (IA sobre el dato), M02-03 (notas de turno) | además, `llm` | hasta 2 GB más | ~470 MB del GGUF | solo la primera descarga |
| M06-01 | `lab` con el modelo de M03 | ~0,4 GB | — | no |
| M06-02 | `lab` + mosquitto + modbus + sensor | ~0,7 GB | — | no |
| M06-03 | mosquitto, sensor, archivador, prometheus (con 10 min de métricas normales) | ~0,8 GB | `metricas.csv`, `modelo_termico.json`, `actuaciones.jsonl` | no |
| M07-01, M07-02 | `api` + el `.joblib` | ~0,8 GB | el registro jsonl | no |
| M07-03 | mosquitto, sensor, archivador, prometheus, llm | hasta 3 GB | `incidencias.jsonl` | no |
| M08-01 | modbus (registro de paro) | ~0,2 GB | — | no |
| M08-02 | `api` | ~0,8 GB | el jsonl de predicciones | no |

Para el panel: <http://localhost:8501>. Para el servicio de inferencia: <http://localhost:8000/salud>. Para el modelo generativo: <http://localhost:8088/salud>. Para Prometheus: <http://localhost:9090>.

## Eventos y consignas simulados (M06-03)

La estación acepta dos mensajes de control por MQTT, solo para practicar:

| Tema | Mensaje | Efecto |
|------|---------|--------|
| `linea/est01/evento` | `{"tipo": "fallo_refrigeracion"}` o `{"tipo": "fin"}` | Provoca o termina un fallo: el husillo gana ~0,05 °C por carcasa |
| `linea/est01/consigna` | `{"refrigeracion": N}` | Nivel de refrigeración; la estación lo limita a 1–3 |

Se envían con `lab evento …` y `lab consigna …`. Sin ellos, la estación se comporta siempre igual. Si la temperatura se queda alta tras un fallo, `lab evento fin` y `lab consigna 3`; cuando baje de 63 °C, `lab consigna 1`. Reiniciar la estación (`docker compose restart sensor`) también la devuelve a su estado normal.
