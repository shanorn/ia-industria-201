# Glosario 4 — IA generativa y agentes

[← Hoja anterior](03-aprendizaje-automatico.md) · [Índice del glosario](README.md) · [Siguiente hoja →](05-operacion-gobierno.md)

Modelos que redactan texto, cómo se les da el conocimiento de la planta y cómo se les deja usar herramientas. Lo usas en el M05; vuelve en el M01-02, el M02-03 y el M07-03.

---

<a id="mapa"></a>
## 1. El mapa de familias

```text
IA generativa (aprendizaje profundo → transformers)
│
├── Modelos de lenguaje (LLM)
│   ├── Por tamaño ........ ✔ 0,5 B parámetros (curso) · ○ 7–8 B (portátil con GPU) · ○ 70 B o más (servidor o nube)
│   ├── Por dónde corre ... ✔ local, en el edge (llama.cpp) · ○ en la nube, por API
│   └── Por formato ....... ✔ cuantizado a 4 bits (GGUF Q4_K_M) · ○ 8 bits · ○ 16 bits (original)
│
├── Cómo se le da el conocimiento de la planta   (de menos a más esfuerzo)
│   ├── ✔ Instrucciones en el prompt ............ M02-03, M05-02
│   ├── ✔ Ejemplos en el prompt (few-shot) ....... M02-03
│   ├── ✔ RAG: buscar el texto y dárselo ......... M05-03, M07-03
│   ├── ✔ Herramientas: que lea datos vivos ...... M05-04, M05-06, M07-03
│   └── ○ Ajuste fino (reentrenar con datos propios)
│
├── Cómo se busca el texto en un RAG
│   ├── ✔ Palabras en común (con palabras vacías) ... M05-03
│   ├── ○ BM25 (palabras en común, ponderando las raras)
│   ├── ○ Embeddings (búsqueda por significado)
│   └── ○ Híbrido (las dos, combinadas)
│
└── Quién decide qué herramienta usar
    ├── ✔ El código o el workflow, con un plan fijo ... M05-04, M05-06, M07-03
    ├── ✔ El modelo (tool calling): se prueba, no llama ... M05-06
    └── ○ Varios agentes que se reparten el trabajo
```

<a id="comparacion-conocimiento"></a>
### Comparación: cómo darle a un modelo el conocimiento de la planta

| | Prompt | Ejemplos (few-shot) | RAG | Herramientas | ○ Ajuste fino |
|--|--|--|--|--|--|
| **Qué se hace** | Se le explica la tarea | Se le enseñan casos resueltos | Se busca el texto y se le pega | El código lee el dato y se lo da | Se reentrena con datos propios |
| **Sirve para** | Formato, tono, reglas | Que entienda el formato de salida | Procedimientos, manuales | Datos que cambian (temperatura ahora) | Vocabulario o estilo muy propios |
| **Se actualiza** | Editando el texto | Editando los ejemplos | Editando el documento | Solo | Reentrenando |
| **Se comprueba de dónde sale** | No | No | **Sí: el párrafo citado** | **Sí: la traza** | No |
| **Esfuerzo** | Mínimo | Bajo | Medio | Medio | Alto, con GPU |

**Cómo se lee:** en planta, casi siempre interesa **RAG y herramientas**, porque la respuesta se puede **rastrear** hasta el documento o el dato. El ajuste fino cambia lo que el modelo «sabe» de memoria, pero no deja rastro de dónde sale cada cosa.

---

## 2. Los conceptos

<a id="llm"></a>
### Modelo de lenguaje (LLM)

**Qué es:** un modelo entrenado con enormes cantidades de texto para **predecir la palabra siguiente**. Repitiendo eso, redacta. No consulta ninguna base de datos: genera lo que **suena probable**.

**En la línea:** Qwen2.5 de 0,5 B (500 millones de parámetros), en el contenedor `llm` con llama.cpp, puerto 8088. Ocupa unos 470 MB y funciona sin GPU.

**Dónde se rompe:** no sabe nada de EST-01. Si le preguntas, se inventa algo que suena bien ([alucinación](#alucinacion)).

**Lo usas en:** <!--usos:llm-->[M01-02](../M01-ia-industrial-arquitectura/M01-02-visualizacion-supervision.md) · [M02](../M02-captura-integracion-datos/README.md) · [M02-03](../M02-captura-integracion-datos/M02-03-preparacion-datos.md) · [M05](../M05-ia-generativa/README.md) · [M05-01](../M05-ia-generativa/M05-01-modelo-local.md) · [M05-05](../M05-ia-generativa/M05-05-modelos-abiertos.md) · [M06](../M06-edge-integracion-ot/README.md) · [M07](../M07-mlops-observabilidad/README.md) · [M08](../M08-ciberseguridad-gobierno/README.md)<!--/usos-->

<a id="token"></a>
### Token

**Qué es:** el trozo de texto con el que trabaja el modelo: una palabra corta, o parte de una larga. El modelo lee y escribe token a token, y todo se mide en tokens: la longitud de la respuesta (`max_tokens`), lo que cabe en la conversación, el tiempo de respuesta.

**En la línea:** en el M05-02, con `max_tokens: 60`, la respuesta se corta y llega `finish_reason: "length"`.

**Lo usas en:** <!--usos:token-->[M05-01](../M05-ia-generativa/M05-01-modelo-local.md) · [M05-02](../M05-ia-generativa/M05-02-integracion-aplicacion.md) · [M05-05](../M05-ia-generativa/M05-05-modelos-abiertos.md)<!--/usos-->

<a id="contexto"></a>
### Ventana de contexto

**Qué es:** todo lo que el modelo «ve» de una vez: instrucciones, documento pegado, pregunta y respuesta. Tiene un máximo en tokens. Lo que no está en el contexto, el modelo no lo sabe.

**Lo usas en:** <!--usos:contexto-->[M05-01](../M05-ia-generativa/M05-01-modelo-local.md)<!--/usos-->

<a id="cuantizacion"></a>
### Cuantización (GGUF)

**Qué es:** guardar los pesos del modelo con **menos bits** (4 en vez de 16) para que ocupe y tarde menos, a cambio de perder algo de calidad. **GGUF** es el formato de fichero que usa llama.cpp. `Q4_K_M` significa 4 bits, variante media.

**Por qué importa:** es lo que permite correr un LLM en un equipo edge sin GPU.

**Lo usas en:** <!--usos:cuantizacion-->[M05](../M05-ia-generativa/README.md) · [M05-01](../M05-ia-generativa/M05-01-modelo-local.md) · [M05-05](../M05-ia-generativa/M05-05-modelos-abiertos.md) · [M06](../M06-edge-integracion-ot/README.md)<!--/usos-->

<a id="prompt"></a>
### Prompt e instrucciones

**Qué es:** el texto que se le manda al modelo. En una aplicación tiene partes: las **instrucciones del sistema** (qué es, qué puede y qué no puede hacer), el material (documento, datos) y la pregunta.

**En la línea:** `infra/linea/docs/prompt-notas.txt` (M02-03) le pide sacar datos de las notas de turno en un formato fijo.

**Lo usas en:** <!--usos:prompt-->[M02-03](../M02-captura-integracion-datos/M02-03-preparacion-datos.md)<!--/usos-->

<a id="few-shot"></a>
### Ejemplos en el prompt (few-shot)

**Qué es:** incluir en el prompt algunos casos ya resueltos para que el modelo copie el formato y el criterio. En inglés, *few-shot*: unos pocos ejemplos.

**En la línea:** `prompt-notas-ejemplos.txt` del M02-03.

**Lo usas en:** <!--usos:few-shot-->[M02-03](../M02-captura-integracion-datos/M02-03-preparacion-datos.md) · [M04](../M04-vision-control-calidad/README.md)<!--/usos-->

<a id="alucinacion"></a>
### Alucinación

**Qué es:** cuando el modelo genera algo **falso con total seguridad**: un par de apriete, un código de error, un dato. No miente: completa con lo que suena probable.

**En la línea:** en el M05-01, tres respuestas distintas e inventadas a la misma pregunta sobre el tornillo de la brida.

**Cómo se controla:** darle el texto o el dato (RAG, herramientas), pedirle que diga «no está» si no lo encuentra, y **comprobar** su salida contra los datos, como hace `lab resumen comprobado` en el M01-02.

**Lo usas en:** <!--usos:alucinacion-->[M01-02](../M01-ia-industrial-arquitectura/M01-02-visualizacion-supervision.md) · [M02](../M02-captura-integracion-datos/README.md) · [M02-01](../M02-captura-integracion-datos/M02-01-telemetria.md) · [M02-03](../M02-captura-integracion-datos/M02-03-preparacion-datos.md) · [M05](../M05-ia-generativa/README.md) · [M05-01](../M05-ia-generativa/M05-01-modelo-local.md) · [M05-02](../M05-ia-generativa/M05-02-integracion-aplicacion.md) · [M05-03](../M05-ia-generativa/M05-03-asistente-documentacion.md) · [M05-04](../M05-ia-generativa/M05-04-agentes.md) · [M05-06](../M05-ia-generativa/M05-06-agentes-n8n.md) · [M06-02](../M06-edge-integracion-ot/M06-02-integracion-ot.md) · [M07-01](../M07-mlops-observabilidad/M07-01-servicio-inferencia.md) · [M07-03](../M07-mlops-observabilidad/M07-03-incidencias-agente.md) · [M08](../M08-ciberseguridad-gobierno/README.md)<!--/usos-->

<a id="temperatura-llm"></a>
### Temperatura del modelo

**Qué es:** el ajuste que decide cuánto **azar** hay al elegir cada token. Con 0, elige siempre el más probable y repite la misma respuesta; más alta, varía más. No tiene nada que ver con la temperatura del husillo.

**En la línea:** por eso, en el M05-01, la misma pregunta da tres respuestas distintas.

**Lo usas en:** <!--usos:temperatura-llm-->[M05-01](../M05-ia-generativa/M05-01-modelo-local.md)<!--/usos-->

<a id="rag"></a>
### RAG (recuperar y luego generar)

**Qué es:** *Retrieval-Augmented Generation*. Antes de preguntar al modelo, el código **busca** en los documentos el trozo que habla del tema, y se lo da junto con la pregunta y la instrucción de usar **solo** ese texto.

**En la línea:** el M05-03 busca en el procedimiento de EST-01 el párrafo con más palabras en común con la pregunta.

**Dónde se rompe:** si la búsqueda elige mal el párrafo, el modelo contesta bien… sobre otra cosa. En el M05-03, las [palabras vacías](#palabras-vacias) («el», «de», «a») hacen ganar a un párrafo equivocado.

**Lo usas en:** <!--usos:rag-->[M05](../M05-ia-generativa/README.md) · [M05-03](../M05-ia-generativa/M05-03-asistente-documentacion.md) · [M05-05](../M05-ia-generativa/M05-05-modelos-abiertos.md)<!--/usos-->

<a id="palabras-vacias"></a>
### Palabras vacías (stopwords)

**Qué es:** las palabras que aparecen en cualquier texto y no dicen de qué trata: artículos, preposiciones. Se quitan antes de buscar.

**Lo usas en:** <!--usos:palabras-vacias-->[M05-03](../M05-ia-generativa/M05-03-asistente-documentacion.md) · [M05-05](../M05-ia-generativa/M05-05-modelos-abiertos.md)<!--/usos-->

<a id="agente"></a>
### Agente y herramienta

**Qué es:** un **agente** es un modelo al que se le dan **herramientas**: funciones del código que leen datos o hacen acciones. Una **herramienta** tiene un nombre, qué hace y qué devuelve.

**En la línea:** en el M05-04, la herramienta `leer_estacion` lee la temperatura actual. En el M07-03, el agente de incidencias tiene herramientas **solo de lectura** y **el código** decide cuáles usar según la alerta (el `PLAN`). El modelo solo redacta.

**Dónde se rompe:** si el modelo decide qué herramienta usar y tiene herramientas de escritura, una mala interpretación puede **actuar sobre la planta**. La forma más segura de que no toque el proceso es no darle con qué.

**Lo usas en:** <!--usos:agente-->[M01-02](../M01-ia-industrial-arquitectura/M01-02-visualizacion-supervision.md) · [M01-03](../M01-ia-industrial-arquitectura/M01-03-metricas-alertas.md) · [M05](../M05-ia-generativa/README.md) · [M05-04](../M05-ia-generativa/M05-04-agentes.md) · [M05-06](../M05-ia-generativa/M05-06-agentes-n8n.md) · [M07](../M07-mlops-observabilidad/README.md) · [M07-03](../M07-mlops-observabilidad/M07-03-incidencias-agente.md) · [M08](../M08-ciberseguridad-gobierno/README.md) · [M08-01](../M08-ciberseguridad-gobierno/M08-01-evaluacion-riesgos.md)<!--/usos-->

<a id="tool-calling"></a>
### Llamada a herramientas (tool calling)

**Qué es:** la forma en que un modelo **pide** usar una herramienta. Se le envía la lista de herramientas (nombre, descripción, parámetros) y, en lugar de texto, contesta con una «llamada» en un formato fijo; el programa la ejecuta y le devuelve el resultado. Es lo que permite que **el modelo** decida qué herramienta usar.

**En la línea:** en el M05-06, el nodo **AI Agent** de n8n lo intenta con `leer_estacion`, pero la herramienta no se ejecuta: el servicio `llm` del curso no pasa la lista de herramientas al modelo, y un modelo de 0,5 B lo haría mal de todos modos.

**Dónde se rompe:** el modelo puede no llamar a la herramienta y contestar de memoria, llamar a la que no toca o inventar parámetros. Por eso en planta la herramienta la llama **el código** o el workflow, y el modelo solo redacta.

**Lo usas en:** <!--usos:tool-calling-->[M05-06](../M05-ia-generativa/M05-06-agentes-n8n.md)<!--/usos-->

<a id="orquestador-workflows"></a>
### Orquestador de workflows (n8n)

**Qué es:** una herramienta para automatizar uniendo **nodos** con flechas: un disparador (un chat, un mensaje MQTT, una hora) y pasos que leen, transforman, deciden y escriben. Cada ejecución queda registrada con la entrada y la salida de cada nodo. n8n, Node-RED o Apache Airflow son ejemplos.

**En la línea:** en el M05-06, n8n monta el agente del M05-04 sin programar: lee `estado.json`, decide con un nodo If, pide a Qwen la frase, escribe la traza y publica en Mosquitto.

**Dónde se rompe:** que se programe de forma visual no lo hace más seguro. Lo que puede hacer depende de los nodos que tenga y de los permisos del contenedor. Las **credenciales** se guardan aparte, cifradas, y el workflow se puede exportar a git como cualquier otro código.

**Lo usas en:** <!--usos:orquestador-workflows-->[M05-06](../M05-ia-generativa/M05-06-agentes-n8n.md)<!--/usos-->

<a id="runbook"></a>
### Runbook (procedimiento de respuesta)

**Qué es:** el documento que dice, para cada alerta, **qué significa, qué mirar y qué hacer**. Lo escriben las personas que conocen el sistema; el agente lo consulta.

**En la línea:** `infra/linea/docs/runbook-est01.md`, una sección por alerta.

**Lo usas en:** <!--usos:runbook-->[M07](../M07-mlops-observabilidad/README.md) · [M07-03](../M07-mlops-observabilidad/M07-03-incidencias-agente.md)<!--/usos-->
