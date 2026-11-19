# Glosario del curso

[← Volver al índice del curso](../../README.md) · [Fichas de los comandos `lab`](../comandos-lab.md)

Los conceptos teóricos del curso, explicados con la línea EST-01 como ejemplo. En los labs y en los README de módulo, la primera vez que aparece un término en cada página está enlazado a su ficha.

Cada ficha dice **qué es**, **cómo es en la línea del curso**, **dónde se rompe** y **en qué páginas lo usas**. Cuando un concepto tiene «hermanos» (otros algoritmos u otras formas de resolver lo mismo), la hoja abre con un **mapa de familias** y una **tabla comparativa**:

- ✔ = lo usas en el curso.
- ○ = existe y se usa en la industria, pero no lo practicamos; está para que sepas situarlo.

## Las hojas

| Hoja | De qué trata | Dónde se usa |
|------|--------------|--------------|
| [Datos y arquitectura](01-datos-arquitectura.md) | Cómo sale el dato de la máquina, por dónde viaja y dónde se guarda | M01–M02 |
| [Observabilidad y alertas](02-observabilidad.md) | Cómo se sabe si la línea y sus sistemas hacen su trabajo | M01, M06, M07 |
| [Aprendizaje automático y visión](03-aprendizaje-automatico.md) | Mapa de familias de algoritmos, cómo funciona cada uno y cómo se evalúa | M03–M04, M06, M07 |
| [IA generativa y agentes](04-ia-generativa.md) | Modelos de lenguaje, cómo darles el conocimiento de la planta, RAG y agentes | M05, M01-02, M02-03, M07-03 |
| [Operación, MLOps y gobierno](05-operacion-gobierno.md) | Cuánto decide el modelo, cómo se sirve, se vigila, se protege y se rinden cuentas | M06–M08 |
| [Modelos abiertos en planta](06-modelos-abiertos.md) | Qué modelos existen para cada tarea, cuándo usarlos y cuándo no, licencias, memoria y cómo se sirven | M05-05 |

## Mapas de familias y comparaciones

| Pregunta | Dónde |
|----------|-------|
| ¿Qué tipos de algoritmo hay y cuáles usamos? | [Mapa de aprendizaje automático](03-aprendizaje-automatico.md#mapa) |
| Regresión logística, árbol, red neuronal… ¿cuál elijo? | [Comparación de clasificadores](03-aprendizaje-automatico.md#comparacion-clasificadores) |
| ¿Cómo se detecta una anomalía sin etiquetas? | [Mapa, rama no supervisada](03-aprendizaje-automatico.md#mapa) |
| ¿Qué métodos de visión hay? | [Visión: una imagen son números](03-aprendizaje-automatico.md#vision-pixeles) |
| ¿Prompt, RAG, herramientas o ajuste fino? | [Comparación: cómo darle conocimiento a un modelo](04-ia-generativa.md#comparacion-conocimiento) |
| ¿Qué tamaños y formatos de LLM hay? | [Mapa de IA generativa](04-ia-generativa.md#mapa) |
| ¿Qué modelo abierto uso para cada tarea, y cuándo no? | [Mapa de modelos abiertos](06-modelos-abiertos.md#mapa) y [comparación por tipo](06-modelos-abiertos.md#comparacion-tipos) |
| ¿Qué modelo hay para leer documentos, transcribir voz, detectar defectos en fotos o prever una serie? | [Catálogo por tarea](06-modelos-abiertos.md#catalogo) |
| ¿Qué licencia tiene un modelo y qué me obliga? | [Licencias](06-modelos-abiertos.md#licencias) |
| ¿Cuánta memoria necesita un modelo? | [Formatos y memoria](06-modelos-abiertos.md#memoria) |
| ¿llama.cpp, Ollama o vLLM? | [Cómo se sirven](06-modelos-abiertos.md#servir) |
| ¿Cuánto debe decidir el modelo? | [Mapa de modos de actuación](05-operacion-gobierno.md#mapa) |
| ¿Qué tipos de alerta hay? | [Alerta y tiempo `for`](02-observabilidad.md#alerta) |
| ¿Con qué se protege la línea? | [Superficie de ataque y medidas](05-operacion-gobierno.md#superficie) |

## Índice alfabético

| Término | Hoja |
|---------|------|
| [Agente y herramienta](04-ia-generativa.md#agente) | IA generativa y agentes |
| [Alerta y tiempo `for`](02-observabilidad.md#alerta) | Observabilidad y alertas |
| [Alucinación](04-ia-generativa.md#alucinacion) | IA generativa y agentes |
| [Anomalía](03-aprendizaje-automatico.md#anomalia) | Aprendizaje automático y visión |
| [API de inferencia](05-operacion-gobierno.md#api) | Operación, MLOps y gobierno |
| [Árbol de decisión](03-aprendizaje-automatico.md#arbol) | Aprendizaje automático y visión |
| [Autenticación](05-operacion-gobierno.md#autenticacion) | Operación, MLOps y gobierno |
| [Banda normal y pendiente](03-aprendizaje-automatico.md#banda-normal) | Aprendizaje automático y visión |
| [Broker](01-datos-arquitectura.md#broker) | Datos y arquitectura |
| [Catálogo: buscar en documentos (embeddings y rerankers)](06-modelos-abiertos.md#cat-buscar) | Modelos abiertos en planta |
| [Catálogo: filtros de seguridad para modelos de lenguaje](06-modelos-abiertos.md#cat-seguridad) | Modelos abiertos en planta |
| [Catálogo: leer documentos (OCR)](06-modelos-abiertos.md#cat-documentos) | Modelos abiertos en planta |
| [Catálogo: modelos de lenguaje](06-modelos-abiertos.md#cat-texto) | Modelos abiertos en planta |
| [Catálogo: series temporales](06-modelos-abiertos.md#cat-series) | Modelos abiertos en planta |
| [Catálogo: visión (clasificar, detectar, segmentar, anomalías)](06-modelos-abiertos.md#cat-vision) | Modelos abiertos en planta |
| [Catálogo: voz](06-modelos-abiertos.md#cat-voz) | Modelos abiertos en planta |
| [Clases desequilibradas](03-aprendizaje-automatico.md#desequilibrio) | Aprendizaje automático y visión |
| [Cómo elegir, en cinco preguntas](06-modelos-abiertos.md#elegir) | Modelos abiertos en planta |
| [Cómo se sirven](06-modelos-abiertos.md#servir) | Modelos abiertos en planta |
| [Comparación de clasificadores](03-aprendizaje-automatico.md#comparacion-clasificadores) | Aprendizaje automático y visión |
| [Comparación por tipo de modelo](06-modelos-abiertos.md#comparacion-tipos) | Modelos abiertos en planta |
| [Comparación: cómo darle a un modelo el conocimiento de la planta](04-ia-generativa.md#comparacion-conocimiento) | IA generativa y agentes |
| [Consigna](05-operacion-gobierno.md#consigna) | Operación, MLOps y gobierno |
| [Cuándo no hace falta un modelo generativo](06-modelos-abiertos.md#cuando-no) | Modelos abiertos en planta |
| [Cuantización (GGUF)](04-ia-generativa.md#cuantizacion) | IA generativa y agentes |
| [Dataset](01-datos-arquitectura.md#dataset) | Datos y arquitectura |
| [Deriva](05-operacion-gobierno.md#deriva) | Operación, MLOps y gobierno |
| [Dictamen](05-operacion-gobierno.md#dictamen) | Operación, MLOps y gobierno |
| [Distancia de Mahalanobis](03-aprendizaje-automatico.md#mahalanobis) | Aprendizaje automático y visión |
| [Edge (equipo de borde)](01-datos-arquitectura.md#edge) | Datos y arquitectura |
| [Ejemplos en el prompt (few-shot)](04-ia-generativa.md#few-shot) | IA generativa y agentes |
| [Entrenamiento y examen (partición temporal)](03-aprendizaje-automatico.md#particion) | Aprendizaje automático y visión |
| [Escalado de las señales](03-aprendizaje-automatico.md#escalado) | Aprendizaje automático y visión |
| [Etiqueta](03-aprendizaje-automatico.md#etiqueta) | Aprendizaje automático y visión |
| [Evento y muestra](01-datos-arquitectura.md#evento) | Datos y arquitectura |
| [Formatos y memoria: cuánto ocupa un modelo](06-modelos-abiertos.md#memoria) | Modelos abiertos en planta |
| [Frescura del dato](02-observabilidad.md#frescura) | Observabilidad y alertas |
| [Fuga de información](03-aprendizaje-automatico.md#fuga) | Aprendizaje automático y visión |
| [Gobierno de la IA y Reglamento europeo](05-operacion-gobierno.md#gobierno) | Operación, MLOps y gobierno |
| [Histórico (historian)](01-datos-arquitectura.md#historico) | Datos y arquitectura |
| [Incidencia](05-operacion-gobierno.md#incidencia) | Operación, MLOps y gobierno |
| [Indicador de proceso, KPI y OEE](02-observabilidad.md#kpi) | Observabilidad y alertas |
| [Inferencia](05-operacion-gobierno.md#inferencia) | Operación, MLOps y gobierno |
| [Las familias más conocidas](06-modelos-abiertos.md#familias) | Modelos abiertos en planta |
| [Latencia](05-operacion-gobierno.md#latencia) | Operación, MLOps y gobierno |
| [Licencias: lo que hay que mirar antes de instalar](06-modelos-abiertos.md#licencias) | Modelos abiertos en planta |
| [Limpieza de datos](01-datos-arquitectura.md#limpieza) | Datos y arquitectura |
| [Llamada a herramientas (tool calling)](04-ia-generativa.md#tool-calling) | IA generativa y agentes |
| [Mapa de registros](01-datos-arquitectura.md#mapa-registros) | Datos y arquitectura |
| [Matriz de confusión, recall y falsas alarmas](03-aprendizaje-automatico.md#matriz-confusion) | Aprendizaje automático y visión |
| [Mensaje retenido y Last Will](01-datos-arquitectura.md#retenido) | Datos y arquitectura |
| [Métrica: contador e indicador](02-observabilidad.md#metrica) | Observabilidad y alertas |
| [MLOps](05-operacion-gobierno.md#mlops) | Operación, MLOps y gobierno |
| [Modbus](01-datos-arquitectura.md#modbus) | Datos y arquitectura |
| [Modelo de lenguaje (LLM)](04-ia-generativa.md#llm) | IA generativa y agentes |
| [Modelo y entrenamiento](03-aprendizaje-automatico.md#modelo) | Aprendizaje automático y visión |
| [MQTT](01-datos-arquitectura.md#mqtt) | Datos y arquitectura |
| [Observabilidad](02-observabilidad.md#observabilidad) | Observabilidad y alertas |
| [OPC UA](01-datos-arquitectura.md#opcua) | Datos y arquitectura |
| [Orquestador de workflows (n8n)](04-ia-generativa.md#orquestador-workflows) | IA generativa y agentes |
| [OT e IT](01-datos-arquitectura.md#ot) | Datos y arquitectura |
| [Palabras vacías (stopwords)](04-ia-generativa.md#palabras-vacias) | IA generativa y agentes |
| [Pasarela (gateway)](01-datos-arquitectura.md#pasarela) | Datos y arquitectura |
| [Pieza (carcasa)](01-datos-arquitectura.md#pieza) | Datos y arquitectura |
| [Prometheus y scrape](02-observabilidad.md#prometheus) | Observabilidad y alertas |
| [Prompt e instrucciones](04-ia-generativa.md#prompt) | IA generativa y agentes |
| [PromQL: rate, increase y predict_linear](02-observabilidad.md#promql) | Observabilidad y alertas |
| [QoS (calidad de servicio)](01-datos-arquitectura.md#qos) | Datos y arquitectura |
| [RAG (recuperar y luego generar)](04-ia-generativa.md#rag) | IA generativa y agentes |
| [Red neuronal (MLP)](03-aprendizaje-automatico.md#red-neuronal) | Aprendizaje automático y visión |
| [Regresión logística](03-aprendizaje-automatico.md#regresion-logistica) | Aprendizaje automático y visión |
| [Runbook (procedimiento de respuesta)](04-ia-generativa.md#runbook) | IA generativa y agentes |
| [SCADA](01-datos-arquitectura.md#scada) | Datos y arquitectura |
| [Señal (característica)](03-aprendizaje-automatico.md#senal) | Aprendizaje automático y visión |
| [Serie temporal](02-observabilidad.md#serie-temporal) | Observabilidad y alertas |
| [Sobreajuste](03-aprendizaje-automatico.md#sobreajuste) | Aprendizaje automático y visión |
| [Superficie de ataque](05-operacion-gobierno.md#superficie) | Operación, MLOps y gobierno |
| [Tema (topic)](01-datos-arquitectura.md#tema) | Datos y arquitectura |
| [Temperatura del modelo](04-ia-generativa.md#temperatura-llm) | IA generativa y agentes |
| [Tiempo de ciclo y microparada](01-datos-arquitectura.md#tiempo-ciclo) | Datos y arquitectura |
| [Token](04-ia-generativa.md#token) | IA generativa y agentes |
| [Trazabilidad (el rastro)](05-operacion-gobierno.md#trazabilidad) | Operación, MLOps y gobierno |
| [Umbral de decisión](03-aprendizaje-automatico.md#umbral) | Aprendizaje automático y visión |
| [Un caso real: lo que pide un integrador](06-modelos-abiertos.md#caso-real) | Modelos abiertos en planta |
| [Ventana de contexto](04-ia-generativa.md#contexto) | IA generativa y agentes |
| [Versión y huella del modelo](05-operacion-gobierno.md#version-huella) | Operación, MLOps y gobierno |
| [Visión: una imagen son números](03-aprendizaje-automatico.md#vision-pixeles) | Aprendizaje automático y visión |
| [Zona de duda](03-aprendizaje-automatico.md#zona-duda) | Aprendizaje automático y visión |
