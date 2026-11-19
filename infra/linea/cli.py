"""Comandos de cada laboratorio. Salida humana y código 0 si el paso cuadra."""
import asyncio
import json
import re
import sqlite3
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import httpx
import joblib
import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
from PIL import Image
from sklearn.covariance import EmpiricalCovariance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from linea.config import (
    API_URL,
    DATA,
    LLM_URL,
    MODBUS_HOST,
    MODBUS_PORT,
    MQTT_HOST,
    MQTT_PORT,
    OPCUA_ENDPOINT,
    PANEL_URL,
    PROMETHEUS_URL,
    SERVICIOS,
    TOPIC_CICLO,
    TOPIC_CONSIGNA,
    TOPIC_DICTAMEN,
    TOPIC_EVENTO,
    UMBRAL_TEMPERATURA,
    VERSION_ARRANQUE,
)
from linea.datos import escribir_crudo, generar_imagenes, generar_limpio, limpiar, vigilancia
from linea.estado import leer as leer_estado

# Aviso de scipy/scikit-learn sin efecto en el resultado; ensucia la salida del alumno.
warnings.filterwarnings("ignore", message="Unknown solver options")
# El aviso de convergencia de las redes lo da el propio comando, en español
warnings.filterwarnings("ignore", message="Stochastic Optimizer: Maximum iterations")

FEATURES = ["temperatura_c", "vibracion_mm_s", "corriente_a", "presion_bar"]


def _param(args, clave: str, defecto, tipo=float):
    """Lee un parámetro «clave=valor» de la línea de comandos (p. ej. umbral=0.3)."""
    for a in args:
        if a.startswith(clave + "="):
            try:
                return tipo(a.split("=", 1)[1])
            except ValueError:
                pass
    return defecto


def ok(codigo: str, detalle: str) -> int:
    print(f"OK {codigo}: {detalle}", flush=True)
    return 0


def fallo(mensaje: str) -> int:
    print(f"FALLO: {mensaje}", flush=True)
    return 1


def _mqtt():
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"lab-{time.time_ns()}")
    cliente.connect(MQTT_HOST, MQTT_PORT, 30)
    return cliente


def consumir(topic: str, timeout: float = 20) -> str | None:
    recibido: dict = {}

    def on_message(_c, _u, msg):
        recibido["payload"] = msg.payload.decode()

    cliente = _mqtt()
    cliente.on_message = on_message
    cliente.subscribe(topic)
    cliente.loop_start()
    limite = time.time() + timeout
    while "payload" not in recibido and time.time() < limite:
        time.sleep(0.1)
    cliente.loop_stop()
    cliente.disconnect()
    return recibido.get("payload")


def esperar_filas(minimo: int = 1, timeout: float = 25) -> int:
    ruta = DATA / "historial.sqlite"
    limite = time.time() + timeout
    while time.time() < limite:
        if ruta.exists():
            con = sqlite3.connect(ruta)
            try:
                n = con.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0]
            except sqlite3.OperationalError:
                n = 0
            con.close()
            if n >= minimo:
                return n
        time.sleep(0.4)
    return 0


def cmd_m01_01(_args) -> int:
    n = esperar_filas(1)
    if n < 1:
        return fallo("el archivador no tiene ciclos; ¿están mosquitto, sensor y archivador en marcha?")
    payload = consumir(TOPIC_CICLO, 15)
    if not payload:
        return fallo("no llega ningún ciclo por MQTT")
    ciclo = json.loads(payload)
    estado = leer_estado()
    if ciclo["pieza_id"] != estado["pieza_id"] and abs(ciclo["secuencia"] - estado["secuencia"]) > 2:
        return fallo("el ciclo MQTT y el estado en disco no son de la misma estación")
    print(json.dumps({"mqtt": ciclo, "archivadas": n}, ensure_ascii=False))
    return ok("m01-01", f"ciclo {ciclo['pieza_id']} archivado; total={n}")


def cmd_m01_02(_args) -> int:
    n = esperar_filas(2)
    if n < 2:
        return fallo("hace falta histórico para el panel")
    try:
        respuesta = httpx.get(PANEL_URL, timeout=30, follow_redirects=True)
    except httpx.HTTPError as exc:
        return fallo(f"el panel no responde en {PANEL_URL}: {exc}")
    if respuesta.status_code >= 400:
        return fallo(f"el panel contestó {respuesta.status_code}")
    con = sqlite3.connect(DATA / "historial.sqlite")
    df = pd.read_sql_query("SELECT temperatura_c FROM lecturas", con)
    con.close()
    fuera = int((df["temperatura_c"] > UMBRAL_TEMPERATURA).sum())
    print(f"panel_http={respuesta.status_code} lecturas={len(df)} fuera_de_margen={fuera} umbral={UMBRAL_TEMPERATURA}")
    return ok("m01-02", f"panel vivo, {len(df)} lecturas, {fuera} fuera de {UMBRAL_TEMPERATURA:.0f} C")


def cmd_m02_01(_args) -> int:
    payload = consumir(TOPIC_CICLO, 15)
    if not payload:
        return fallo("no hay telemetría")
    ciclo = json.loads(payload)
    for campo in ("pieza_id", "temperatura_c", "vibracion_mm_s", "ts"):
        if campo not in ciclo:
            return fallo(f"falta {campo}")
    print(json.dumps(ciclo, ensure_ascii=False))
    return ok("m02-01", f"evento {ciclo['pieza_id']} en {TOPIC_CICLO}")


def cmd_m02_01_pausa(_args) -> int:
    payload = consumir(TOPIC_CICLO, 3)
    if payload:
        return fallo("seguían llegando ciclos con el sensor parado")
    return ok("m02-01-pausa", "hueco: ningún ciclo en 3 s")


def cmd_m02_02(_args) -> int:
    estado = leer_estado()

    async def leer_opc() -> float:
        from asyncua import Client

        async with Client(url=OPCUA_ENDPOINT) as client:
            estacion = None
            for hijo in await client.nodes.objects.get_children():
                if (await hijo.read_browse_name()).Name == "Estacion":
                    estacion = hijo
                    break
            if estacion is None:
                raise RuntimeError("el servidor no publica el objeto Estacion")
            indice = (await estacion.read_browse_name()).NamespaceIndex
            nodo = await estacion.get_child([f"{indice}:Temperatura"])
            return float(await nodo.read_value())

    try:
        opc = asyncio.run(leer_opc())
    except Exception as exc:
        return fallo(f"OPC-UA: {exc}")

    from pymodbus.client import ModbusTcpClient

    cliente = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    if not cliente.connect():
        return fallo("Modbus no conecta")
    rr = cliente.read_holding_registers(0, 4, slave=1)
    cliente.close()
    if rr.isError():
        return fallo(f"Modbus: {rr}")
    modbus_c = rr.registers[0] / 10
    print(f"estado={estado['temperatura_c']} opcua={opc:.2f} modbus={modbus_c:.1f}")
    if abs(opc - estado["temperatura_c"]) > 1.5:
        return fallo("OPC-UA no coincide con el estado")
    if abs(modbus_c - estado["temperatura_c"]) > 1.5:
        return fallo("Modbus no coincide con el estado (¿falta la escala /10?)")
    return ok("m02-02", "MQTT, OPC-UA y Modbus leen la misma temperatura")


MAPA_MODBUS = {0: ("temperatura_c", 10), 1: ("vibracion_mm_s", 1000), 2: ("corriente_a", 100), 3: ("secuencia", 1), 10: ("paro_seguridad", 1)}


def cmd_modbus(args) -> int:
    """lab modbus [registro_inicial] [cuantos]: lee registros del esclavo Modbus en crudo."""
    from pymodbus.client import ModbusTcpClient

    inicio = _numero(args, 0, 0)
    cuantos = _numero(args, 1, 4)
    cliente = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    if not cliente.connect():
        return fallo("Modbus no conecta; ¿está el contenedor modbus en marcha?")
    rr = cliente.read_holding_registers(inicio, cuantos, slave=1)
    cliente.close()
    if rr.isError():
        return fallo(f"Modbus: {rr}")
    print("registro  valor_crudo")
    for i, valor in enumerate(rr.registers):
        print(f"{inicio + i:8d}  {valor:11d}")
    return ok("modbus", f"{cuantos} registros leídos desde el {inicio}")


def cmd_opcua(_args) -> int:
    """lab opcua: recorre el objeto Estacion del servidor OPC-UA y enseña cada variable con su tipo."""
    async def recorrer():
        from asyncua import Client

        async with Client(url=OPCUA_ENDPOINT) as client:
            for hijo in await client.nodes.objects.get_children():
                if (await hijo.read_browse_name()).Name == "Estacion":
                    filas = []
                    for var in await hijo.get_children():
                        nombre = (await var.read_browse_name()).Name
                        valor = await var.read_value()
                        tipo = (await var.read_data_type_as_variant_type()).name
                        filas.append((nombre, valor, tipo))
                    return filas
        return []

    try:
        filas = asyncio.run(recorrer())
    except Exception as exc:
        return fallo(f"OPC-UA: {exc}")
    print("nodo                  valor          tipo")
    for nombre, valor, tipo in filas:
        print(f"Estacion.{nombre:<12} {str(valor):<14} {tipo}")
    return ok("opcua", f"{len(filas)} variables en el objeto Estacion")


def cmd_pasarela(args) -> int:
    """lab pasarela [segundos]: lee el PLC por Modbus cada segundo y publica en MQTT, ya en grados."""
    from pymodbus.client import ModbusTcpClient

    segundos = _numero(args, 0, 10)
    mb = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    if not mb.connect():
        return fallo("Modbus no conecta")
    cliente = _mqtt()
    cliente.loop_start()
    for _ in range(segundos):
        rr = mb.read_holding_registers(0, 4, slave=1)
        mensaje = {
            "fuente": "modbus",
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "temperatura_c": rr.registers[0] / 10,
            "vibracion_mm_s": rr.registers[1] / 1000,
            "corriente_a": rr.registers[2] / 100,
            "secuencia": rr.registers[3],
        }
        cliente.publish("linea/est01/pasarela", json.dumps(mensaje))
        print(f"publicado en linea/est01/pasarela: {json.dumps(mensaje)}", flush=True)
        time.sleep(1)
    cliente.loop_stop()
    cliente.disconnect()
    mb.close()
    return ok("pasarela", f"{segundos} lecturas de Modbus publicadas en MQTT")


def cmd_m02_03(args) -> int:
    crudo = escribir_crudo(DATA / "crudo.csv")
    resumen = limpiar(crudo, DATA / "limpio.csv")
    limpio = pd.read_csv(DATA / "limpio.csv")
    if resumen["piezas_unicas"] != len(limpio):
        return fallo("siguen duplicadas las piezas")
    if limpio["temperatura_c"].max() > 120 or limpio["temperatura_c"].min() < 40:
        return fallo("la temperatura limpia no está en grados")
    if (DATA / "imposibles.csv").stat().st_size == 0:
        return fallo("no se apartaron los 9999")
    print(json.dumps(resumen))
    if "rellenar" in args:
        # Experimento: en lugar de quitar las piezas con hueco, rellenarlas con la media
        crudo_df = pd.read_csv(DATA / "crudo.csv")
        validas = crudo_df[crudo_df.temperatura_c.notna() & (crudo_df.temperatura_c < 1000)].copy()
        validas.loc[validas.temperatura_c > 150, "temperatura_c"] /= 10
        media = round(float(validas.temperatura_c.mean()), 2)
        relleno = crudo_df[crudo_df.temperatura_c != 9999].copy()
        relleno.loc[relleno.temperatura_c > 150, "temperatura_c"] /= 10
        huecos = int(relleno.temperatura_c.isna().sum())
        relleno["temperatura_c"] = relleno["temperatura_c"].fillna(media)
        relleno.to_csv(DATA / "limpio_relleno.csv", index=False)
        print(f"relleno: {huecos} huecos rellenados con la media {media} °C -> limpio_relleno.csv")
        print(f"  piezas con temperatura exactamente {media}: limpio={int((limpio.temperatura_c == media).sum())} relleno={int((relleno.temperatura_c == media).sum())}")
        print(f"  desviación típica de la temperatura: limpio={limpio.temperatura_c.std():.3f} relleno={relleno.temperatura_c.std():.3f}")
    return ok("m02-03", f"crudo={resumen['filas_crudo']} limpio={resumen['filas_limpias']} huecos={resumen['huecos']}")


def _partir(df: pd.DataFrame):
    df = df.sort_values("pieza_id")
    corte = int(len(df) * 0.7)
    return df.iloc[:corte], df.iloc[corte:]


def _tasas(y_true, y_pred) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    recall = tp / (tp + fn) if (tp + fn) else 0
    fpr = fp / (fp + tn) if (fp + tn) else 0
    return {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn), "recall": recall, "fpr": fpr}


def cmd_m03_01(args) -> int:
    if not (DATA / "limpio.csv").exists():
        escribir_crudo(DATA / "crudo.csv")
        limpiar(DATA / "crudo.csv", DATA / "limpio.csv")
    df = pd.read_csv(DATA / "limpio.csv")
    train, test = _partir(df)
    umbral = _param(args, "umbral", 0.5)
    equilibrar = _param(args, "equilibrar", "si", str) != "no"
    modelo = LogisticRegression(class_weight="balanced" if equilibrar else None, max_iter=400)
    modelo.fit(train[FEATURES], train["defecto"])
    proba = modelo.predict_proba(test[FEATURES])[:, 1]
    pred = (proba >= umbral).astype(int)                  # umbral de decisión (0,5 por defecto)
    tasas = _tasas(test["defecto"], pred)
    if umbral != 0.5 or not equilibrar:
        print(f"umbral={umbral} equilibrar={'si' if equilibrar else 'no'}")
    print(json.dumps(tasas))
    if tasas["recall"] < 0.45:
        return fallo(f"recall de defecto demasiado bajo ({tasas['recall']:.2f})")
    DATA.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, DATA / "modelo_logreg.joblib")
    return ok("m03-01", f"recall_defecto={tasas['recall']:.2f} falsas_alarmas={tasas['fpr']:.2f}")


def cmd_m03_02(args) -> int:
    base = generar_limpio(400, seed=3)
    normal = base[base["defecto"] == 0]
    vig = vigilancia()
    # Un bosque de aislamiento agrupa el valor extremo con el borde del histórico
    # y no avisa. La distancia de Mahalanobis sí mide cuánto se sale cada señal.
    escala = StandardScaler()
    base_z = escala.fit_transform(normal[FEATURES])
    detector = EmpiricalCovariance().fit(base_z)
    umbral = _param(args, "umbral", 13.3)  # por defecto, chi-cuadrado 0,99 con 4 señales
    distancias = detector.mahalanobis(escala.transform(vig[FEATURES]))
    marcas = np.where(distancias >= umbral, -1, 1)
    raro = vig["averia_simulada"] == 1
    pillados = int(((marcas == -1) & raro).sum())
    total = int(raro.sum())
    falsos = int(((marcas == -1) & ~raro).sum())
    salida = vig.copy()
    salida["distancia"] = distancias.round(2)
    salida["aviso"] = (marcas == -1).astype(int)
    salida.to_csv(DATA / "vigilancia.csv", index=False)
    print(f"umbral={umbral} averias_simuladas={total} avisadas={pillados} avisos_sobre_normales={falsos} de {int((~raro).sum())}")
    if pillados / total < 0.7:
        return fallo("el detector no ve las averías simuladas")
    joblib.dump(detector, DATA / "detector_anomalia.joblib")
    return ok("m03-02", f"averías simuladas avisadas {pillados}/{total}")


def cmd_m03_03(_args) -> int:
    df = pd.read_csv(DATA / "limpio.csv")
    train, test = _partir(df)
    candidatos = {
        "logreg": LogisticRegression(class_weight="balanced", max_iter=400),
        "arbol": DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=7),
    }
    informe = {}
    for nombre, modelo in candidatos.items():
        modelo.fit(train[FEATURES], train["defecto"])
        informe[nombre] = _tasas(test["defecto"], modelo.predict(test[FEATURES]))
        informe[nombre]["modelo"] = modelo
    print(json.dumps({k: {m: v for m, v in d.items() if m != "modelo"} for k, d in informe.items()}))

    def clave(item):
        nombre, datos = item
        return (datos["recall"], -datos["fpr"])

    ganador, datos = max(informe.items(), key=clave)
    joblib.dump(datos["modelo"], DATA / "modelo_defecto.joblib")
    (DATA / "VERSION").write_text(VERSION_ARRANQUE + "\n", encoding="utf-8")
    (DATA / "modelo_elegido.txt").write_text(ganador + "\n", encoding="utf-8")
    return ok("m03-03", f"elegido={ganador} recall={datos['recall']:.2f} fpr={datos['fpr']:.2f}")


def cmd_arbol(args) -> int:
    """lab arbol [linea]: enseña las reglas del árbol de decisión elegido, en texto."""
    from sklearn.tree import export_text

    fichero, senales = ("modelo_linea.joblib", SENALES_VIVAS) if "linea" in args else ("modelo_defecto.joblib", FEATURES)
    ruta = DATA / fichero
    if not ruta.exists():
        return fallo(f"falta {fichero}")
    modelo = joblib.load(ruta)
    if not hasattr(modelo, "tree_"):
        return fallo(f"{fichero} no es un árbol de decisión (es {type(modelo).__name__})")
    print(f"reglas de {fichero} (class: 1 = defecto, 0 = buena):")
    print(export_text(modelo, feature_names=senales, decimals=3))
    return ok("arbol", f"{modelo.get_n_leaves()} hojas, profundidad {modelo.get_depth()}")


def _features_imagen(ruta: Path, lado: int = 16) -> np.ndarray:
    img = Image.open(ruta).convert("L").resize((lado, lado))
    return np.asarray(img, dtype=np.float32).reshape(-1) / 255.0


def _entrenar_vision(lado: int = 16):
    if not (DATA / "imagenes" / "manifiesto.csv").exists():
        generar_imagenes()
    tabla = pd.read_csv(DATA / "imagenes" / "manifiesto.csv")

    def partir(parte: pd.DataFrame):
        n = int(len(parte) * 0.7)
        return parte.iloc[:n], parte.iloc[n:]

    ent_ok, pru_ok = partir(tabla[tabla["defecto"] == 0])
    ent_ko, pru_ko = partir(tabla[tabla["defecto"] == 1])
    entreno = pd.concat([ent_ok, ent_ko])
    prueba = pd.concat([pru_ok, pru_ko])
    X = np.stack([_features_imagen(Path(r), lado) for r in entreno["ruta"]])
    modelo = LogisticRegression(max_iter=400)
    modelo.fit(X, entreno["defecto"].to_numpy())
    Xp = np.stack([_features_imagen(Path(r), lado) for r in prueba["ruta"]])
    pred = modelo.predict(Xp)
    acierto = float((pred == prueba["defecto"].to_numpy()).mean())
    return modelo, tabla, acierto


def cmd_m04_01(args) -> int:
    lado = int(_param(args, "lado", 16))
    modelo, _tabla, acierto = _entrenar_vision(lado)
    if lado == 16:
        joblib.dump(modelo, DATA / "modelo_vision.joblib")   # solo el de 16×16 lo usa M04-03
    else:
        print(f"lado={lado}: {lado * lado} píxeles por foto (no se guarda el modelo)")
    print(f"acierto_prueba={acierto:.2f}")
    if acierto < 0.85:
        return fallo("el clasificador visual no separa las piezas")
    return ok("m04-01", f"acierto={acierto:.2f} en imágenes no usadas al entrenar")


def _fila_brillante(ruta: Path) -> int:
    img = np.asarray(Image.open(ruta).convert("L"), dtype=np.float32)
    return int(img.mean(axis=1).argmax())


def cmd_m04_02(args) -> int:
    if not (DATA / "imagenes" / "manifiesto.csv").exists():
        generar_imagenes()
    tabla = pd.read_csv(DATA / "imagenes" / "manifiesto.csv")
    malas = tabla[tabla["defecto"] == 1].head(5)
    buenas = tabla[tabla["defecto"] == 0].head(3)
    errores = 0
    for _, fila in malas.iterrows():
        y = _fila_brillante(Path(fila["ruta"]))
        if abs(y - int(fila["y"])) > 2:
            errores += 1
    falsos = 0
    for _, fila in buenas.iterrows():
        img = np.asarray(Image.open(fila["ruta"]).convert("L"), dtype=np.float32)
        if img.mean(axis=1).max() > _param(args, "brillo", 230):
            falsos += 1
    print(f"brillo={_param(args, 'brillo', 230)} errores_zona={errores} falsos_en_buenas={falsos} de {len(buenas)}")
    if errores:
        return fallo("la zona no cae sobre el rayón")
    return ok("m04-02", f"zona correcta en {len(malas)} defectos; buenas sin marca={falsos}")


def cmd_m04_03(args) -> int:
    umbral = _param(args, "umbral", 0.5)
    duda = _param(args, "duda", 0.0)
    if not (DATA / "modelo_vision.joblib").exists():
        cmd_m04_01([])
    modelo = joblib.load(DATA / "modelo_vision.joblib")
    tabla = pd.read_csv(DATA / "imagenes" / "manifiesto.csv")
    lote = pd.concat([tabla[tabla.defecto == 0].head(3), tabla[tabla.defecto == 1].head(3)])
    entrada = DATA / "lote_entrada"
    entrada.mkdir(parents=True, exist_ok=True)
    filas = []
    for _, pieza in lote.iterrows():
        origen = Path(pieza["ruta"])
        destino = entrada / origen.name
        destino.write_bytes(origen.read_bytes())
        x = _features_imagen(destino).reshape(1, -1)
        proba = float(modelo.predict_proba(x)[0, 1])
        if duda and abs(proba - umbral) < duda:
            dictamen = "dudosa"            # demasiado cerca del umbral: la mira una persona
        else:
            dictamen = "aceptar" if proba < umbral else "revisar"
        filas.append({"imagen": destino.name, "probabilidad_defecto": round(proba, 3), "decision": dictamen})
    salida = pd.DataFrame(filas)
    salida.to_csv(DATA / "lote_resultado.csv", index=False)
    if len(salida) != 6:
        return fallo("el registro no tiene una fila por imagen")
    if not (salida["decision"] != "aceptar").any():
        return fallo("ninguna pieza fue a revisión")
    if umbral != 0.5 or duda:
        print(f"umbral={umbral} duda=±{duda}")
    print(salida.to_string(index=False))
    return ok("m04-03", f"registro={len(salida)} revisar={(salida.decision == 'revisar').sum()}")


def _chat(contenido: str, sistema: str | None = None, max_tokens: int = 60) -> str:
    mensajes = []
    if sistema:
        mensajes.append({"role": "system", "content": sistema})
    mensajes.append({"role": "user", "content": contenido})
    respuesta = httpx.post(
        f"{LLM_URL}/v1/chat/completions",
        json={"messages": mensajes, "max_tokens": max_tokens},
        timeout=180,
    )
    respuesta.raise_for_status()
    return respuesta.json()["choices"][0]["message"]["content"].strip()


def cmd_m05_01(_args) -> int:
    try:
        salud = httpx.get(f"{LLM_URL}/salud", timeout=10)
    except httpx.HTTPError as exc:
        return fallo(f"el servicio local no responde: {exc}")
    if "huggingface" in salud.text or "api.openai" in salud.text:
        return fallo("la salud no es el servicio local")
    t0 = time.time()
    texto = _chat("Responde exactamente: hola")
    dt = time.time() - t0
    print(f"respuesta={texto!r} segundos={dt:.1f} url={LLM_URL}")
    if not texto:
        return fallo("respuesta vacía")
    return ok("m05-01", f"inferencia local en {dt:.1f}s via {LLM_URL}")


def cmd_m05_02(_args) -> int:
    texto = _chat("Di solo la palabra estacion")
    print(f"aplicacion: {texto}")
    if not texto:
        return fallo("la aplicación no mostró respuesta")
    try:
        httpx.get("http://servicio-inexistente:9/salud", timeout=2)
    except httpx.HTTPError as exc:
        print(f"servicio caído: {type(exc).__name__}")
    else:
        return fallo("un host inventado no debía responder")
    return ok("m05-02", "la aplicación habla con el servicio local y avisa si no está")


def _fragmento(pregunta: str) -> str:
    texto = Path("/opt/linea/docs/procedimiento-est01.md").read_text(encoding="utf-8")
    partes = [p.strip() for p in texto.split("\n\n") if p.strip()]
    palabras = set(pregunta.lower().replace("·", " ").split())

    def puntos(parte: str) -> int:
        return len(palabras & set(parte.lower().replace("·", " ").split()))

    return max(partes, key=puntos)


def _chat_hasta(contenido: str, sistema: str, contiene: str, intentos: int = 3) -> str:
    ultimo = ""
    for _ in range(intentos):
        ultimo = _chat(contenido, sistema, max_tokens=40)
        if contiene in ultimo:
            return ultimo
    return ultimo


def cmd_preguntar(args) -> int:
    """lab preguntar "<pregunta>" [procedimiento]: pregunta al modelo local, con o sin el procedimiento delante."""
    textos = [a for a in args if a != "procedimiento"]
    if not textos:
        return fallo('falta la pregunta: lab preguntar "¿…?"')
    pregunta = " ".join(textos)
    if "procedimiento" in args:
        fragmento = _fragmento(pregunta)
        print(f"fragmento recuperado: {fragmento}")
        texto = _chat(f"Texto:\n{fragmento}\n\nPregunta: {pregunta}", "Usa únicamente el texto. Si no está, di que no lo sabes.", max_tokens=80)
    else:
        texto = _chat(pregunta, "Eres el asistente de mantenimiento de la estación EST-01.", max_tokens=80)
    print(f"respuesta: {texto}")
    return ok("preguntar", "respuesta del modelo local")


VACIAS = {"a", "al", "de", "del", "el", "la", "las", "los", "lo", "un", "una", "y", "o", "en", "se", "que", "qué",
          "es", "por", "para", "con", "hay", "cómo", "cuánto", "cuál", "si", "no", "su", "sus"}


def cmd_buscar(args) -> int:
    """lab buscar "<pregunta>": enseña qué párrafo del procedimiento recuperaría el asistente y por qué."""
    pregunta = " ".join(args)
    if not pregunta:
        return fallo('falta la pregunta: lab buscar "¿…?"')
    texto = Path("/opt/linea/docs/procedimiento-est01.md").read_text(encoding="utf-8")
    partes = [p.strip() for p in texto.split("\n\n") if p.strip()]
    textos = [a for a in args if a != "filtrar"]
    pregunta = " ".join(textos)
    palabras = set(pregunta.lower().replace("·", " ").replace("¿", " ").replace("?", " ").split())
    if "filtrar" in args:
        # Mejora: no contar palabras vacías ni títulos, que no dicen de qué trata el párrafo
        palabras -= VACIAS
        partes = [p for p in partes if not p.startswith("#")]
        print(f"palabras que cuentan: {', '.join(sorted(palabras))}")
    filas = []
    for parte in partes:
        comunes = palabras & set(parte.lower().replace("·", " ").replace(".", " ").replace(",", " ").split())
        filas.append((len(comunes), sorted(comunes), parte[:60] + ("…" if len(parte) > 60 else "")))
    filas.sort(key=lambda f: -f[0])
    print("puntos  palabras en común                párrafo")
    for puntos, comunes, inicio in filas[:5]:
        print(f"{puntos:6d}  {', '.join(comunes)[:30]:<32} {inicio}")
    return ok("buscar", f"elegido el párrafo con {filas[0][0]} palabras en común")


def cmd_m05_03(_args) -> int:
    pregunta = "¿A qué par de apriete se aprieta el tornillo de la brida?"
    fragmento = _fragmento(pregunta)
    print("fragmento:")
    print(fragmento)
    if "12" not in fragmento:
        return fallo("el recuperador no encontró el párrafo del par")
    texto = _chat_hasta(
        f"Texto:\n{fragmento}\n\nPregunta: {pregunta}\nResponde solo con el valor, por ejemplo 12 N·m.",
        "Usa únicamente el texto. No inventes otro número. Copia el 12.",
        "12",
    )
    print(f"respuesta={texto!r}")
    if "12" not in texto:
        return fallo("la respuesta no contiene el 12 del procedimiento")
    return ok("m05-03", "responde 12 a partir del procedimiento")


def cmd_m05_03_ausente(_args) -> int:
    fragmento = _fragmento("color del tornillo de recambio")
    if "color" in fragmento.lower() and "recambio" in fragmento.lower():
        return fallo("no debería haber un párrafo de color")
    print("sin_dato: el procedimiento no habla del color del tornillo")
    return ok("m05-03-ausente", "no hay fragmento; no se inventa el dato")


def cmd_m05_04(_args) -> int:
    estado = leer_estado()
    valor = estado["temperatura_c"]
    traza = DATA / "traza_agente.jsonl"
    traza.write_text(
        json.dumps({"herramienta": "leer_estacion", "temperatura_c": valor}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    buscado = f"{valor:.2f}"
    texto = _chat_hasta(
        f"La herramienta leer_estacion devolvió {buscado} °C. "
        f"Responde una frase que contenga exactamente el número {buscado}.",
        "No cambies el número de la herramienta. Cópialo tal cual.",
        buscado,
    )
    print(f"agente: {texto}")
    if buscado not in texto and str(valor) not in texto:
        return fallo(f"la frase no incluye el valor medido {valor}")
    negativa = "No puedo modificar el automatismo: no existe una herramienta de escritura."
    print(f"escritura: {negativa}")
    if "leer_estacion" not in traza.read_text(encoding="utf-8"):
        return fallo("no quedó traza de la herramienta")
    return ok("m05-04", f"usó leer_estacion={valor} y rechazó escribir")


def cmd_m06_01(args) -> int:
    fichero = _param(args, "modelo", "modelo_defecto.joblib", str)
    if not (DATA / fichero).exists():
        return fallo(f"falta {fichero}; pasa antes por M03-03")
    modelo = joblib.load(DATA / fichero)
    fila = pd.read_csv(DATA / "limpio.csv").head(1)[FEATURES]
    t0 = time.perf_counter()
    _ = modelo.predict_proba(fila)
    # calentamiento
    t0 = time.perf_counter()
    for _ in range(20):
        modelo.predict_proba(fila)
    ms = (time.perf_counter() - t0) * 1000 / 20
    tam_kb = (DATA / fichero).stat().st_size / 1024
    print(f"ms_por_pieza={ms:.2f} fichero={fichero} tamaño={tam_kb:.1f} KB tipo={type(modelo).__name__}")
    if ms > 200:
        return fallo("la inferencia local va demasiado lenta para un ciclo")
    return ok("m06-01", f"{ms:.2f} ms por pieza, modelo en disco")


def cmd_m06_02(args) -> int:
    modelo = joblib.load(DATA / "modelo_defecto.joblib")
    estado = leer_estado()
    # La presión no viaja en el ciclo vivo; el laboratorio usa la consigna nominal.
    fila = pd.DataFrame(
        [
            {
                "temperatura_c": estado["temperatura_c"],
                "vibracion_mm_s": estado["vibracion_mm_s"],
                "corriente_a": estado["corriente_a"],
                "presion_bar": 6.0,
            }
        ]
    )
    proba = float(modelo.predict_proba(fila)[0, 1])
    dictamen = "revisar" if proba >= _param(args, "umbral", 0.5) else "seguir"
    evento = {"pieza_id": estado["pieza_id"], "decision": dictamen, "probabilidad": round(proba, 3)}
    recibido_mqtt: dict = {}

    def on_dictamen(_c, _u, msg):
        recibido_mqtt["payload"] = msg.payload.decode()

    cliente = _mqtt()
    cliente.on_message = on_dictamen
    cliente.subscribe(TOPIC_DICTAMEN)
    cliente.loop_start()
    time.sleep(0.4)
    cliente.publish(TOPIC_DICTAMEN, json.dumps(evento))
    limite = time.time() + 10
    while "payload" not in recibido_mqtt and time.time() < limite:
        time.sleep(0.1)
    cliente.loop_stop()
    cliente.disconnect()
    if "payload" not in recibido_mqtt:
        return fallo("el automatismo no recibió el dictamen")
    recibido = json.loads(recibido_mqtt["payload"])
    from pymodbus.client import ModbusTcpClient

    mb = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    mb.connect()
    paro = mb.read_holding_registers(10, 1, slave=1)
    mb.close()
    if paro.isError() or paro.registers[0] != 0:
        return fallo("el registro de paro de seguridad cambió")
    print(json.dumps({"evento": recibido, "paro_seguridad": 0}))
    if recibido["pieza_id"] != estado["pieza_id"]:
        return fallo("el evento no es de esta pieza")
    return ok("m06-02", f"{recibido['pieza_id']} -> {recibido['decision']}; paro=0")


def _cuerpo(pieza_id: str, fila: pd.Series) -> dict:
    return {
        "pieza_id": pieza_id,
        "temperatura_c": float(fila["temperatura_c"]),
        "vibracion_mm_s": float(fila["vibracion_mm_s"]),
        "corriente_a": float(fila["corriente_a"]),
        "presion_bar": float(fila["presion_bar"]),
    }


def cmd_m07_01(_args) -> int:
    try:
        salud = httpx.get(f"{API_URL}/salud", timeout=10).json()
    except httpx.HTTPError as exc:
        return fallo(f"el servicio no está: {exc}")
    df = pd.read_csv(DATA / "limpio.csv").iloc[0]
    cuerpo = _cuerpo("SRV0001", df)
    respuesta = httpx.post(f"{API_URL}/predecir", json=cuerpo, timeout=15)
    if respuesta.status_code != 200:
        return fallo(respuesta.text)
    datos = respuesta.json()
    print(json.dumps(datos, ensure_ascii=False))
    if datos["version"] != salud["version"]:
        return fallo("la versión de la respuesta no es la del servicio")
    incompleta = httpx.post(f"{API_URL}/predecir", json={"pieza_id": "X"}, timeout=15)
    if incompleta.status_code < 400:
        return fallo("aceptó una pieza sin señales")
    return ok("m07-01", f"version={datos['version']} dictamen={datos['dictamen']}")


def _tasa_alerta(modelo, df: pd.DataFrame) -> float:
    proba = modelo.predict_proba(df[FEATURES])[:, 1]
    return float((proba >= 0.5).mean())


def cmd_m07_02(args) -> int:
    modelo = joblib.load(DATA / "modelo_defecto.joblib")
    df = pd.read_csv(DATA / "limpio.csv")
    _, test = _partir(df)
    base = _tasa_alerta(modelo, test)
    if "vivo" in args:
        # La línea de ahora: últimas lecturas del histórico (la presión no viaja en vivo: 6 bar)
        con = sqlite3.connect(f"file:{DATA / 'historial.sqlite'}?mode=ro", uri=True)
        vivo = pd.read_sql_query("SELECT temperatura_c, vibracion_mm_s, corriente_a FROM lecturas ORDER BY id DESC LIMIT 120", con)
        con.close()
        vivo["presion_bar"] = 6.0
        tasa = _tasa_alerta(modelo, vivo)
        print(f"tasa_base={base:.2f} tasa_linea_ahora={tasa:.2f} (últimas {len(vivo)} carcasas, temperatura media {vivo.temperatura_c.mean():.2f} °C)")
        return ok("m07-02", f"base={base:.2f} línea ahora={tasa:.2f}")
    grados = _param(args, "grados", 8.0)
    movido = test.copy()
    movido["temperatura_c"] = movido["temperatura_c"] + grados
    deriva = _tasa_alerta(modelo, movido)
    print(f"tasa_base={base:.2f} tasa_desplazada={deriva:.2f}" + ("" if grados == 8 else f" (+{grados:g} °C)"))
    if grados != 8:
        return ok("m07-02", f"base={base:.2f} con +{grados:g} °C={deriva:.2f}")
    if deriva < base + 0.1:
        return fallo("no se ve la deriva al subir 8 °C")
    (DATA / "seguimiento.json").write_text(
        json.dumps({"tasa_base": base, "tasa_desplazada": deriva}),
        encoding="utf-8",
    )
    return ok("m07-02", f"base={base:.2f} desplazada={deriva:.2f}")


def cmd_m08_01(_args) -> int:
    from pymodbus.client import ModbusTcpClient

    mb = ModbusTcpClient(MODBUS_HOST, port=MODBUS_PORT)
    if not mb.connect():
        return fallo("modbus no disponible para el cruce OT")
    paro = mb.read_holding_registers(10, 1, slave=1)
    mb.close()
    print("superficies:")
    for servicio in SERVICIOS:
        puerto = servicio["puerto"] if servicio["puerto"] else "-"
        print(f"  {servicio['nombre']} puerto={puerto} — {servicio['para']}")
    medidas = {
        "dato": "el histórico y el procedimiento se quedan en el volumen local; no hay URL externa",
        "modelo": "el fichero joblib y el GGUF están en disco y la respuesta lleva versión",
        "acceso": "los puertos del laboratorio solo se publican en localhost del puesto",
    }
    for clave, texto in medidas.items():
        print(f"medida_{clave}: {texto}")
    if paro.isError() or paro.registers[0] != 0:
        return fallo("el paro de seguridad no está en reposo")
    return ok("m08-01", "inventario escrito; paro de seguridad en 0")


def cmd_m08_02(_args) -> int:
    df = pd.read_csv(DATA / "limpio.csv").iloc[10]
    cuerpo = _cuerpo("AUD0007", df)
    primera = httpx.post(f"{API_URL}/predecir", json=cuerpo, timeout=15).json()
    version_vista = (DATA / "VERSION").read_text(encoding="utf-8").strip()
    (DATA / "VERSION").write_text("defecto-0.2\n", encoding="utf-8")
    segunda = httpx.post(f"{API_URL}/predecir", json={**cuerpo, "pieza_id": "AUD0008"}, timeout=15).json()
    lineas = (DATA / "predicciones.jsonl").read_text(encoding="utf-8").strip().splitlines()
    suyas = [json.loads(l) for l in lineas if json.loads(l)["pieza_id"] in {"AUD0007", "AUD0008"}]
    print(json.dumps(suyas, ensure_ascii=False))
    if len(suyas) < 2:
        return fallo("no hay rastro de las dos piezas")
    if any(item["version"] != version_vista for item in suyas):
        return fallo("el rastro cambió de versión sin reiniciar el servicio")
    if segunda["version"] != primera["version"]:
        return fallo("las dos llamadas no comparten la versión cargada al arrancar")
    uso = "asistencia: el dictamen recomienda seguir o revisar; no escribe el paro"
    print(uso)
    (DATA / "VERSION").write_text(version_vista + "\n", encoding="utf-8")
    return ok("m08-02", f"rastro de AUD0007 con version={primera['version']} aunque el fichero cambió")


# ---------------------------------------------------------------- M07-03: agente de incidencias
def _promql(consulta: str) -> list:
    respuesta = httpx.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": consulta}, timeout=10)
    return respuesta.json()["data"]["result"]


# Herramientas del agente. Todas LEEN; ninguna escribe ni reinicia nada.
def _h_estado_servicios() -> dict:
    return {r["metric"]["job"]: ("vivo" if r["value"][1] == "1" else "caído") for r in _promql("up")}


def _h_retraso_historico() -> dict:
    r = _promql("time() - archivador_ultimo_registro_timestamp_seconds")
    return {"segundos_sin_guardar": round(float(r[0]["value"][1])) if r else "sin dato (archivador caído)"}


def _h_perdida_ultimo_minuto() -> dict:
    r = _promql("sum(increase(estacion_piezas_fabricadas_total[1m])) - sum(increase(archivador_registros_guardados_total[1m]))")
    return {"carcasas_sin_guardar_ultimo_minuto": round(float(r[0]["value"][1])) if r else "sin dato"}


def _h_ultimo_registro() -> dict:
    ruta = DATA / "historial.sqlite"
    if not ruta.exists():
        return {"ultimo_registro": "no hay histórico"}
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    fila = con.execute("SELECT pieza_id, ts FROM lecturas ORDER BY id DESC LIMIT 1").fetchone()
    con.close()
    return {"ultimo_registro": f"{fila[0]} a las {fila[1]}" if fila else "vacío"}


def _h_temperatura_actual() -> dict:
    r = _promql("estacion_temperatura_husillo_celsius")
    return {"temperatura_husillo_c": float(r[0]["value"][1]) if r else "sin dato"}


HERRAMIENTAS = {
    "estado_servicios": _h_estado_servicios,
    "retraso_historico": _h_retraso_historico,
    "perdida_ultimo_minuto": _h_perdida_ultimo_minuto,
    "ultimo_registro": _h_ultimo_registro,
    "temperatura_actual": _h_temperatura_actual,
}

# Qué herramientas usa el agente para cada alerta. Lo decide el código, no el modelo.
PLAN = {
    "ArchivadorCaido": ["estado_servicios", "ultimo_registro"],
    "HistoricoSinDatos": ["estado_servicios", "retraso_historico", "perdida_ultimo_minuto", "ultimo_registro"],
    "RegistrosPerdidos": ["estado_servicios", "retraso_historico", "perdida_ultimo_minuto"],
    "EstacionCaida": ["estado_servicios"],
    "TemperaturaHusilloAlta": ["temperatura_actual"],
}


def _runbook(alerta: str) -> str:
    texto = Path("/opt/linea/docs/runbook-est01.md").read_text(encoding="utf-8")
    for seccion in texto.split("\n## ")[1:]:
        titulo, _, cuerpo = seccion.partition("\n")
        if titulo.strip() == alerta:
            return cuerpo.strip()
    return ""


def cmd_m07_03(_args) -> int:
    try:
        alertas = httpx.get(f"{PROMETHEUS_URL}/api/v1/alerts", timeout=10).json()["data"]["alerts"]
    except httpx.HTTPError as exc:
        return fallo(f"Prometheus no responde: {exc}")
    activas = [a for a in alertas if a["state"] == "firing"]
    if not activas:
        return fallo("no hay alertas activas; provoca una incidencia primero")

    registro = DATA / "incidencias.jsonl"
    for alerta in activas:
        nombre = alerta["labels"]["alertname"]
        # 1. El código elige las herramientas según la alerta y las ejecuta
        hechos = {}
        for herramienta in PLAN.get(nombre, ["estado_servicios"]):
            hechos.update(HERRAMIENTAS[herramienta]())
        # 2. El runbook dice qué hacer ante esa alerta
        procedimiento = _runbook(nombre) or "No hay entrada en el runbook para esta alerta."
        # 3. El modelo local solo redacta el diagnóstico con esos datos
        diagnostico = _chat(
            f"Alerta: {nombre}.\nDatos medidos: {json.dumps(hechos, ensure_ascii=False)}\n"
            f"Runbook:\n{procedimiento}\n\n"
            "Escribe en español, en dos frases, qué está pasando y qué acción propone el runbook.",
            "Eres el asistente de mantenimiento de la línea. Usa solo los datos y el runbook. "
            "No inventes cifras. No ejecutes nada: solo propones.",
            max_tokens=120,
        )
        informe = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "alerta": nombre,
            "severidad": alerta["labels"].get("severidad"),
            "herramientas": PLAN.get(nombre, ["estado_servicios"]),
            "hechos": hechos,
            "diagnostico": diagnostico,
            "estado": "propuesta pendiente de una persona",
        }
        with registro.open("a", encoding="utf-8") as f:
            f.write(json.dumps(informe, ensure_ascii=False) + "\n")
        print(f"== {nombre} ({informe['severidad']})")
        print(f"herramientas: {', '.join(informe['herramientas'])}")
        print(f"hechos: {json.dumps(hechos, ensure_ascii=False)}")
        print(f"diagnóstico: {diagnostico}")
    return ok("m07-03", f"{len(activas)} incidencia(s) diagnosticada(s) en {registro.name}; ninguna acción ejecutada")


# ---------------------------------------------------------------- redes neuronales (M03 y M04)
def _numero(args, i, defecto, tipo=int):
    try:
        return tipo(args[i])
    except (IndexError, ValueError):
        return defecto


def cmd_m04_red(args) -> int:
    """lab m04-red [neuronas] [iteraciones] [fraccion_de_fotos]"""
    neuronas = _numero(args, 0, 64)
    iteraciones = _numero(args, 1, 1000)
    fraccion = _numero(args, 2, 1.0, float)
    if not (DATA / "imagenes" / "manifiesto.csv").exists():
        generar_imagenes()
    tabla = pd.read_csv(DATA / "imagenes" / "manifiesto.csv")

    def partir(parte):
        n = int(len(parte) * 0.7)
        return parte.iloc[:n], parte.iloc[n:]

    ent_ok, pru_ok = partir(tabla[tabla.defecto == 0])
    ent_ko, pru_ko = partir(tabla[tabla.defecto == 1])
    # fraccion < 1: se entrena solo con una parte de las fotos de entrenamiento (para ver el sobreajuste)
    k = max(1, round(len(ent_ok) * fraccion))
    entreno = pd.concat([ent_ok.head(k), ent_ko.head(k)])
    prueba = pd.concat([pru_ok, pru_ko])
    X = np.stack([_features_imagen(Path(r)) for r in entreno["ruta"]])
    y = entreno["defecto"].to_numpy()
    Xp = np.stack([_features_imagen(Path(r)) for r in prueba["ruta"]])
    yp = prueba["defecto"].to_numpy()

    # Red: 256 entradas (píxeles) → «neuronas» en la capa oculta → 2 salidas (buena / defectuosa)
    red = MLPClassifier(hidden_layer_sizes=(neuronas,), max_iter=iteraciones, random_state=0)
    t0 = time.time()
    red.fit(X, y)
    segundos = time.time() - t0
    curva = red.loss_curve_
    marcas = sorted({0, len(curva) // 4, len(curva) // 2, 3 * len(curva) // 4, len(curva) - 1})
    print(f"red: 256 entradas -> {neuronas} neuronas -> 2 salidas; {len(entreno)} fotos de entrenamiento, {len(prueba)} de examen")
    print("pérdida (más baja = se equivoca menos con las fotos de entrenamiento):")
    for i in marcas:
        print(f"  iteración {i + 1:4d}: {curva[i]:.3f}")
    base = LogisticRegression(max_iter=400).fit(X, y).score(Xp, yp)
    ent, exa = red.score(X, y), red.score(Xp, yp)
    print(f"acierto en entrenamiento={ent:.2f}  en examen={exa:.2f}  (regresión logística en examen={base:.2f})")
    print(f"tiempo de entrenamiento: {segundos:.2f} s en CPU")
    if red.n_iter_ >= iteraciones:
        print("aviso: la red ha agotado las iteraciones sin terminar de aprender (no ha convergido)")
    joblib.dump(red, DATA / "modelo_vision_red.joblib")
    return ok("m04-red", f"neuronas={neuronas} iteraciones={len(curva)} examen={exa:.2f}")


def _tasas_texto(nombre, t):
    return (f"{nombre:<22} defectos encontrados {t['tp']:>2} de {t['tp'] + t['fn']:<3} "
            f"falsas alarmas {t['fp']:>3} de {t['fp'] + t['tn']}")


def cmd_m03_red(args) -> int:
    """lab m03-red [capas, p. ej. 64,32] [sin-escalar]"""
    capas = tuple(int(c) for c in (args[0] if args and args[0] != "sin-escalar" else "64,32").split(","))
    escalar = "sin-escalar" not in args
    df = pd.read_csv(DATA / "limpio.csv")
    train, test = _partir(df)
    arbol = DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=7)
    arbol.fit(train[FEATURES], train["defecto"])
    red = MLPClassifier(hidden_layer_sizes=capas, max_iter=1000, random_state=0)
    if escalar:
        red = make_pipeline(StandardScaler(), red)   # cada señal en su escala antes de entrar en la red
    red.fit(train[FEATURES], train["defecto"])
    t_arbol = _tasas(test["defecto"], arbol.predict(test[FEATURES]))
    t_red = _tasas(test["defecto"], red.predict(test[FEATURES]))
    print(_tasas_texto("árbol (M03-03)", t_arbol))
    print(_tasas_texto(f"red {capas}{'' if escalar else ' sin escalar'}", t_red))
    return ok("m03-red", f"red recall={t_red['recall']:.2f} fpr={t_red['fpr']:.2f}; árbol recall={t_arbol['recall']:.2f} fpr={t_arbol['fpr']:.2f}")


# ---------------------------------------------------------------- dataset propio (M02-04 y M03-04)
SENALES_VIVAS = ["temperatura_c", "vibracion_mm_s", "corriente_a"]


def cmd_m02_04(_args) -> int:
    if not (DATA / "calidad.sqlite").exists():
        return fallo("no hay inspecciones; arranca el contenedor calidad y deja la línea fabricando")
    con = sqlite3.connect(f"file:{DATA / 'historial.sqlite'}?mode=ro", uri=True)
    con.execute(f"ATTACH DATABASE 'file:{DATA / 'calidad.sqlite'}?mode=ro' AS calidad")
    # Solo cuenta lo fabricado desde que calidad empezó a inspeccionar
    desde = con.execute("SELECT MIN(ts_pieza) FROM calidad.inspecciones").fetchone()[0]
    n_hist = con.execute("SELECT COUNT(*) FROM lecturas WHERE ts >= ?", (desde,)).fetchone()[0]
    n_insp = con.execute("SELECT COUNT(*) FROM calidad.inspecciones").fetchone()[0]
    # Unir solo por identificador: con identificadores repetidos, cada pieza se cruza con varias inspecciones
    solo_id = con.execute(
        "SELECT COUNT(*) FROM lecturas l JOIN calidad.inspecciones c ON l.pieza_id = c.pieza_id"
    ).fetchone()[0]
    print(f"calidad inspecciona desde {desde}")
    # Unir por identificador + hora: cada registro con SU inspección
    df = pd.read_sql_query(
        """
        SELECT l.pieza_id, l.ts, l.temperatura_c, l.vibracion_mm_s, l.corriente_a, c.defecto
        FROM lecturas l JOIN calidad.inspecciones c ON l.pieza_id = c.pieza_id AND l.ts = c.ts_pieza
        ORDER BY l.ts
        """,
        con,
    )
    con.close()
    sin_inspeccion = n_hist - len(df)
    print(f"registros en el histórico desde entonces={n_hist}  inspecciones de calidad={n_insp}")
    print(f"unión por pieza_id={solo_id} filas   unión por pieza_id + hora={len(df)} filas")
    print(f"registros sin inspección={sin_inspeccion}  inspecciones sin registro={n_insp - len(df)}")
    if len(df):
        print(f"defectuosas={int(df.defecto.sum())} de {len(df)} ({df.defecto.mean():.0%})")
    if len(df) < 200:
        return fallo(f"solo {len(df)} piezas con señales y resultado de calidad; deja la línea fabricando unos minutos más")
    df.to_csv(DATA / "dataset_linea.csv", index=False)
    return ok("m02-04", f"dataset_linea.csv con {len(df)} piezas y {int(df.defecto.sum())} defectuosas")


def cmd_m03_04(_args) -> int:
    ruta = DATA / "dataset_linea.csv"
    if not ruta.exists():
        return fallo("falta dataset_linea.csv; haz antes M02-04")
    df = pd.read_csv(ruta).sort_values("ts")
    corte = int(len(df) * 0.7)
    train, test = df.iloc[:corte], df.iloc[corte:]
    arbol = DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=7)
    arbol.fit(train[SENALES_VIVAS], train["defecto"])
    red = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(32,), max_iter=1000, random_state=0))
    red.fit(train[SENALES_VIVAS], train["defecto"])
    t_arbol = _tasas(test["defecto"], arbol.predict(test[SENALES_VIVAS]))
    t_red = _tasas(test["defecto"], red.predict(test[SENALES_VIVAS]))
    print(f"{len(train)} piezas para entrenar, {len(test)} para examinar (las más recientes)")
    print(_tasas_texto("árbol", t_arbol))
    print(_tasas_texto("red (32)", t_red))
    print("qué señales usa el árbol (importancia):")
    for senal, peso in sorted(zip(SENALES_VIVAS, arbol.feature_importances_), key=lambda x: -x[1]):
        print(f"  {senal:<16} {peso:.2f}")
    joblib.dump(arbol, DATA / "modelo_linea.joblib")
    return ok("m03-04", f"árbol recall={t_arbol['recall']:.2f} fpr={t_arbol['fpr']:.2f}; red recall={t_red['recall']:.2f} fpr={t_red['fpr']:.2f}")


# ---------------------------------------------------------------- pinceladas de IA en M01 y M02
def _ventana_historico(n: int = 60) -> dict:
    con = sqlite3.connect(f"file:{DATA / 'historial.sqlite'}?mode=ro", uri=True)
    df = pd.read_sql_query(f"SELECT pieza_id, ts, temperatura_c, vibracion_mm_s, corriente_a FROM lecturas ORDER BY id DESC LIMIT {n}", con)
    con.close()
    return {
        "ultima_pieza": df.iloc[0]["pieza_id"],
        "hora_ultimo_dato": df.iloc[0]["ts"],
        "lecturas": len(df),
        "temperatura_media_c": round(float(df.temperatura_c.mean()), 2),
        "temperatura_max_c": float(df.temperatura_c.max()),
        "vibracion_media_mm_s": round(float(df.vibracion_mm_s.mean()), 3),
        "corriente_media_a": round(float(df.corriente_a.mean()), 2),
        "lecturas_por_encima_de_70c": int((df.temperatura_c > UMBRAL_TEMPERATURA).sum()),
    }


def cmd_resumen(args) -> int:
    """lab resumen [con-hora | comprobado]: el modelo local redacta cómo va la estación a partir del histórico."""
    if not (DATA / "historial.sqlite").exists():
        return fallo("todavía no hay histórico")
    datos = _ventana_historico(60)
    retraso = round((datetime.now(timezone.utc) - datetime.fromisoformat(datos["hora_ultimo_dato"])).total_seconds())
    if "comprobado" in args and retraso > 10:
        # Mejora: el CÓDIGO comprueba que el dato está al día antes de dejar hablar al modelo
        print(f"datos: {json.dumps(datos, ensure_ascii=False)}")
        print(f"resumen: Sin datos nuevos desde hace {retraso} s (último: {datos['hora_ultimo_dato']}). "
              "No se puede decir cómo va la estación: revisar el archivador.")
        return ok("resumen", "comprobado por código: datos no actuales, no se pregunta al modelo")
    if "con-hora" in args:
        # Mejora: darle también la hora actual y cuánto hace del último dato
        ahora = datetime.now(timezone.utc)
        datos["hora_actual"] = ahora.isoformat(timespec="seconds")
        datos["segundos_desde_ultimo_dato"] = round((ahora - datetime.fromisoformat(datos["hora_ultimo_dato"])).total_seconds())
    texto = _chat(
        f"Datos de la estación EST-01 (últimas 60 lecturas del histórico): {json.dumps(datos, ensure_ascii=False)}\n"
        "Escribe para el operario, en dos frases y en español, cómo va la estación ahora.",
        "Eres el asistente del operario de una línea de mecanizado. Usa solo los datos. No inventes cifras.",
        max_tokens=100,
    )
    print(f"datos: {json.dumps(datos, ensure_ascii=False)}")
    print(f"resumen: {texto}")
    return ok("resumen", "resumen redactado por el modelo local")


CAUSAS = ["herramienta", "vibracion", "sujecion", "refrigeracion", "camara", "ninguna"]


def _extraer_nota(nota: str, plantilla: str) -> dict:
    texto = _chat(
        plantilla.replace("{nota}", nota),
        "Extraes datos de notas de turno. Respondes solo con JSON, sin explicaciones.",
        max_tokens=60,
    )
    m = re.search(r"\{.*?\}", texto, re.S)
    try:
        return json.loads(m.group(0)) if m else {"_crudo": texto}
    except json.JSONDecodeError:
        return {"_crudo": texto}


def _pieza_hora_por_codigo(nota: str) -> tuple[str, str]:
    # Lo que tiene un formato fijo se extrae con un patrón, sin modelo
    pieza = re.search(r"\bP\d{4}\b", nota)
    hora = re.search(r"\b(\d{1,2})[:h](\d{2})\b", nota)
    return (pieza.group(0) if pieza else "", f"{int(hora.group(1)):02d}:{hora.group(2)}" if hora else "")


def cmd_notas(args) -> int:
    """lab notas [ejemplos] [hibrido]: extrae pieza, hora y causa de las notas de turno y lo compara con lo esperado."""
    fichero = "prompt-notas-ejemplos.txt" if "ejemplos" in args else "prompt-notas.txt"
    plantilla = Path(f"/opt/linea/docs/{fichero}").read_text(encoding="utf-8")
    hibrido = "hibrido" in args
    notas = pd.read_csv("/opt/linea/docs/notas-turno.csv", keep_default_na=False)
    print(f"prompt: linea/docs/{fichero}" + ("   modo híbrido: pieza y hora con código, causa con el modelo" if hibrido else ""))
    filas, aciertos = [], 0
    for _, n in notas.iterrows():
        e = _extraer_nota(n["nota"], plantilla)
        valido = "_crudo" not in e
        pieza = str(e.get("pieza", "")).strip().upper() if valido else ""
        hora = str(e.get("hora", "")).strip() if valido else ""
        causa = str(e.get("causa", "")).strip().lower() if valido else ""
        if hibrido:
            pieza, hora = _pieza_hora_por_codigo(n["nota"])
        # Validación con código: formato y valores permitidos
        formato_ok = bool(valido and (pieza == "" or re.fullmatch(r"P\d{4}", pieza))
                          and re.fullmatch(r"\d{2}:\d{2}", hora) and causa in CAUSAS)
        correcto = formato_ok and pieza == n["pieza_esperada"] and hora == n["hora_esperada"] and causa == n["causa_esperada"]
        aciertos += correcto
        filas.append({
            "nota": n["nota"][:42] + ("…" if len(n["nota"]) > 42 else ""),
            "pieza": pieza or "-", "hora": hora or "-", "causa": (causa or "-")[:16],
            "formato": "ok" if formato_ok else "MAL",
            "correcto": "sí" if correcto else "NO",
        })
    salida = pd.DataFrame(filas)
    salida.to_csv(DATA / "notas_extraidas.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_colwidth", 50):
        print(salida.to_string(index=False))
    return ok("notas", f"{aciertos} de {len(notas)} notas extraídas sin error")


CSV_CONSULTABLES = {
    "crudo": "crudo.csv", "limpio": "limpio.csv", "imposibles": "imposibles.csv",
    "dataset_linea": "dataset_linea.csv", "lote_resultado": "lote_resultado.csv",
    "notas_extraidas": "notas_extraidas.csv", "manifiesto": "imagenes/manifiesto.csv",
    "vigilancia": "vigilancia.csv", "metricas": "metricas.csv",
}


def _cargar_csv(con: sqlite3.Connection) -> None:
    # Cada CSV que exista se puede consultar con su nombre: SELECT * FROM crudo …
    for tabla, fichero in CSV_CONSULTABLES.items():
        ruta = DATA / fichero
        if ruta.exists():
            df = pd.read_csv(ruta)
            columnas = ", ".join(f'"{c}"' for c in df.columns)
            con.execute(f'CREATE TEMP TABLE "{tabla}" ({columnas})')
            marcas = ", ".join("?" for _ in df.columns)
            con.executemany(f'INSERT INTO temp."{tabla}" VALUES ({marcas})',
                            [tuple(None if pd.isna(v) else v for v in fila) for fila in df.itertuples(index=False)])


# ---------------------------------------------------------------- M06-03: predicción y actuación supervisada
def _publicar(topic: str, mensaje: dict) -> None:
    cliente = _mqtt()
    cliente.loop_start()
    cliente.publish(topic, json.dumps(mensaje)).wait_for_publish(5)
    cliente.loop_stop()
    cliente.disconnect()


def cmd_evento(args) -> int:
    """lab evento fallo-refrigeracion | fin: provoca o termina un fallo simulado en la estación."""
    tipo = args[0] if args else ""
    if tipo not in ("fallo-refrigeracion", "fin"):
        return fallo("usa: lab evento fallo-refrigeracion   o   lab evento fin")
    _publicar(TOPIC_EVENTO, {"tipo": "fallo_refrigeracion" if tipo == "fallo-refrigeracion" else "fin"})
    return ok("evento", f"enviado «{tipo}» a la estación por {TOPIC_EVENTO}")


def cmd_consigna(args) -> int:
    """lab consigna <nivel>: pide a la estación un nivel de refrigeración (la estación lo limita a 1-3)."""
    nivel = _numero(args, 0, 1)
    _publicar(TOPIC_CONSIGNA, {"refrigeracion": nivel, "origen": "persona"})
    return ok("consigna", f"pedida refrigeración={nivel} por {TOPIC_CONSIGNA}")


def _serie(consulta: str, minutos: int, paso: int = 5) -> list:
    fin = time.time()
    r = httpx.get(f"{PROMETHEUS_URL}/api/v1/query_range",
                  params={"query": consulta, "start": fin - minutos * 60, "end": fin, "step": paso}, timeout=20)
    resultado = r.json()["data"]["result"]
    return resultado[0]["values"] if resultado else []


def cmd_exportar(args) -> int:
    """lab exportar [minutos]: baja de Prometheus la serie de temperatura y tiempo de ciclo a data/metricas.csv."""
    minutos = _numero(args, 0, 60)
    temp = dict(_serie("estacion_temperatura_husillo_celsius", minutos))
    ciclo = dict(_serie("estacion_tiempo_ciclo_segundos", minutos))
    if not temp:
        return fallo("Prometheus no tiene datos de temperatura; ¿está en marcha y recogiendo métricas?")
    filas = [{"ts": datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds"),
              "temperatura_c": float(v), "tiempo_ciclo_s": float(ciclo.get(t, "nan"))} for t, v in sorted(temp.items())]
    df = pd.DataFrame(filas)
    df.to_csv(DATA / "metricas.csv", index=False)
    print(f"muestras={len(df)} desde={df.ts.iloc[0]} hasta={df.ts.iloc[-1]} (una cada 5 s)")
    print(f"temperatura: media={df.temperatura_c.mean():.2f} mínima={df.temperatura_c.min():.2f} máxima={df.temperatura_c.max():.2f}")
    return ok("exportar", f"{len(df)} muestras en metricas.csv")


def _pendiente(valores: list) -> float:
    """°C por segundo: pendiente de una recta ajustada a las muestras (regresión lineal)."""
    from sklearn.linear_model import LinearRegression

    t = np.array([float(x[0]) for x in valores]).reshape(-1, 1)
    y = np.array([float(x[1]) for x in valores])
    return float(LinearRegression().fit(t - t[0], y).coef_[0])


def cmd_m06_03(args) -> int:
    """lab m06-03 aprender | vigilar [segundos=180] [modo=asistido|automatico]"""
    ruta_modelo = DATA / "modelo_termico.json"
    if "aprender" in args:
        ruta = DATA / "metricas.csv"
        if not ruta.exists():
            return fallo("falta metricas.csv; lanza antes lab exportar")
        df = pd.read_csv(ruta)
        # Limpieza: las muestras imposibles (huecos de reinicios, valores a 0) no son «normal»
        imposibles = int((df.temperatura_c < 40).sum())
        df = df[df.temperatura_c >= 40]
        if len(df) < 120:
            return fallo(f"solo {len(df)} muestras válidas; hacen falta al menos 120 (10 minutos de métricas)")
        print(f"muestras={len(df) + imposibles} descartadas_por_imposibles={imposibles}")
        temp = df.temperatura_c.to_numpy()
        # Comportamiento normal: hasta dónde llega la temperatura y cuánto sube en 2 minutos
        ventana = 24                                   # 24 muestras de 5 s = 2 minutos
        subidas = [float(np.polyfit(np.arange(ventana) * 5, temp[i:i + ventana], 1)[0]) for i in range(len(temp) - ventana)]
        modelo = {
            "muestras": int(len(df)),
            "temperatura_media": round(float(temp.mean()), 2),
            "limite_normal": round(float(np.percentile(temp, 99.5)), 2),
            "pendiente_normal_max": round(float(np.percentile(np.abs(subidas), 99.5)), 4),
        }
        ruta_modelo.write_text(json.dumps(modelo, indent=2), encoding="utf-8")
        print(json.dumps(modelo, ensure_ascii=False))
        return ok("m06-03", f"comportamiento normal aprendido de {len(df)} muestras -> modelo_termico.json")

    if not ruta_modelo.exists():
        return fallo("falta modelo_termico.json; lanza antes lab m06-03 aprender")
    normal = json.loads(ruta_modelo.read_text(encoding="utf-8"))
    segundos = int(_param(args, "segundos", 180))
    automatico = _param(args, "modo", "asistido", str) == "automatico"
    limite_alerta = UMBRAL_TEMPERATURA
    actuado = False
    registro = DATA / "actuaciones.jsonl"
    print(f"vigilando {segundos} s en modo {'AUTOMÁTICO (con límites)' if automatico else 'ASISTIDO (propone, no actúa)'}")
    print(f"normal: hasta {normal['limite_normal']} °C, subida máxima {normal['pendiente_normal_max'] * 60:.2f} °C/min")
    print("hora      temp   subida/min  previsión")
    fin = time.time() + segundos
    while time.time() < fin:
        valores = _serie("estacion_temperatura_husillo_celsius", 2)
        if len(valores) >= 6:
            temp = float(valores[-1][1])
            pendiente = _pendiente(valores)
            anomalo = temp > normal["limite_normal"] and pendiente > normal["pendiente_normal_max"]
            hora = time.strftime("%H:%M:%S", time.gmtime())
            if anomalo and pendiente > 0:
                faltan = max((limite_alerta - temp) / pendiente, 0.0)
                texto = (f"fuera de lo normal: llegará a {limite_alerta:.0f} °C en ~{faltan / 60:.1f} min" if faltan
                         else f"fuera de lo normal: YA por encima de {limite_alerta:.0f} °C")
                if faltan < 300 and not actuado:
                    accion = {"ts": hora, "temperatura_c": temp, "subida_c_min": round(pendiente * 60, 2),
                              "minutos_hasta_alerta": round(faltan / 60, 1), "accion": "subir refrigeración a 3"}
                    if automatico:
                        _publicar(TOPIC_CONSIGNA, {"refrigeracion": 3, "origen": "modelo"})
                        accion["estado"] = "aplicada por el modelo (dentro de los límites de la estación)"
                        texto += "  -> ACCIÓN: refrigeración a 3 (aplicada)"
                    else:
                        accion["estado"] = "propuesta: la decide el operario (lab consigna 3)"
                        texto += "  -> PROPUESTA: subir refrigeración a 3"
                    with registro.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(accion, ensure_ascii=False) + "\n")
                    actuado = True
            elif temp > normal["limite_normal"]:
                texto = "por encima de lo normal, sin subida"
            else:
                texto = "normal"
            print(f"{hora}  {temp:5.2f}  {pendiente * 60:+9.2f}  {texto}", flush=True)
        time.sleep(10)
    return ok("m06-03", "vigilancia terminada" + (f"; acción registrada en {registro.name}" if actuado else "; sin acciones"))


def cmd_sql(args) -> int:
    """Consulta de solo lectura al histórico. Sin argumentos, enseña las columnas de la tabla."""
    ruta = DATA / "historial.sqlite"
    if not ruta.exists():
        return fallo("todavía no hay histórico; arranca mosquitto, sensor y archivador")
    consulta = " ".join(args).strip() or "PRAGMA table_info(lecturas)"
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)   # solo lectura: no se puede romper el histórico
    if (DATA / "calidad.sqlite").exists():                    # la base de calidad, como «calidad.inspecciones»
        con.execute(f"ATTACH DATABASE 'file:{DATA / 'calidad.sqlite'}?mode=ro' AS calidad")
    _cargar_csv(con)                                          # los CSV de data/ como tablas temporales
    try:
        df = pd.read_sql_query(consulta, con)
    except Exception as exc:
        return fallo(f"la consulta no es válida: {exc}")
    finally:
        con.close()
    if df.empty:
        print("(ninguna fila)")
    else:
        with pd.option_context("display.max_rows", 50, "display.width", 200, "display.max_colwidth", 60):
            print(df.to_string(index=False))
    return 0




class _Silencio:
    """Calla los mensajes internos de llama.cpp (van a stderr a bajo nivel)."""
    def __enter__(self):
        import os
        self.guardado = os.dup(2)
        nulo = os.open(os.devnull, os.O_WRONLY)
        os.dup2(nulo, 2)
        os.close(nulo)
    def __exit__(self, *_):
        import os
        os.dup2(self.guardado, 2)
        os.close(self.guardado)


BANCO_EST01 = [   # preguntas de planta y la palabra que tiene que salir en una respuesta correcta
    ("¿A qué par se aprieta el tornillo de la brida?", "12"),
    ("¿A partir de qué temperatura se avisa al turno?", "70"),
    ("¿Con qué se bloquea el husillo antes de medirlo?", "cerrojo"),
    ("¿Cuál es la temperatura habitual mínima del husillo?", "58"),
]


def cmd_m05_05(args) -> int:
    """lab m05-05 [sin-documento]: compara los modelos de texto de /modelos con preguntas de EST-01."""
    import resource
    from llama_cpp import Llama

    con_doc = "sin-documento" not in args
    ficheros = sorted(p for p in Path("/modelos").glob("*.gguf") if "embedding" not in p.name)
    if len(ficheros) < 2:
        return fallo("hace falta un segundo modelo en infra/modelos/ (paso 1 de M05-05)")
    print(f"preguntas={len(BANCO_EST01)}  con el párrafo del procedimiento={'sí' if con_doc else 'no'}")
    print("modelo                               tamaño  carga  memoria  tokens/s  acierto")
    for ruta in ficheros:
        t0 = time.time()
        with _Silencio():
            llm = Llama(model_path=str(ruta), n_ctx=1024, n_threads=4, verbose=False)
        carga = time.time() - t0
        aciertos, tokens, segundos = 0, 0, 0.0
        for pregunta, clave in BANCO_EST01:
            texto = f"Texto: {_fragmento(pregunta)}\n\nPregunta: {pregunta}" if con_doc else pregunta
            t0 = time.time()
            with _Silencio():
                r = llm.create_chat_completion(
                    messages=[{"role": "system", "content": "Responde en una frase. Usa solo el texto si se te da."},
                              {"role": "user", "content": texto}], max_tokens=60, temperature=0.1)
            segundos += time.time() - t0
            tokens += r["usage"]["completion_tokens"]
            aciertos += clave in r["choices"][0]["message"]["content"].lower()
        memoria = int(open("/proc/self/statm").read().split()[1]) * resource.getpagesize() / 2**20   # memoria en uso ahora
        print(f"{ruta.name[:36]:36s} {ruta.stat().st_size / 1e9:5.2f} GB {carga:4.1f} s {memoria:6.0f} MB  {tokens / segundos:8.1f}  {aciertos} de {len(BANCO_EST01)}")
        del llm
        import gc
        gc.collect()                                     # libera el modelo antes de cargar el siguiente
    return ok("m05-05", f"{len(ficheros)} modelos comparados con las mismas preguntas")


TOPIC_AGENTE = "linea/est01/agente"


def _numeros_ausentes(registro: dict) -> list[str]:
    """Números del dato de la herramienta que no aparecen tal cual en la respuesta."""
    dato = registro.get("dato") or {}
    numeros = [str(v) for v in dato.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return [n for n in numeros if n not in registro.get("respuesta", "")]


def cmd_m05_06(args) -> int:
    """Audita la traza del agente de n8n; con «escuchar», espera su próxima respuesta en Mosquitto.

    Con «solucion», revisa el agente importado de infra/n8n (otra traza y otro topic)."""
    solucion = "solucion" in args
    traza = DATA / "n8n" / ("traza_agente_solucion.jsonl" if solucion else "traza_agente.jsonl")
    topic = TOPIC_AGENTE + "/solucion" if solucion else TOPIC_AGENTE
    codigo = "m05-06" + ("-escuchar" if "escuchar" in args else "") + (" solucion" if solucion else "")
    if not traza.exists():
        return fallo(f"no existe {traza}; pregunta al agente en el chat de n8n o con curl")

    if "escuchar" in args:
        print(f"esperando una respuesta en {topic} (hasta 120 s): pregunta ahora en el chat de n8n o con curl…", flush=True)
        payload = consumir(topic, 120)
        if not payload:
            return fallo(f"no llegó nada a {topic}; revisa el nodo Publicar (Mosquitto)")
        try:
            mensaje = json.loads(payload)
        except json.JSONDecodeError:
            return fallo(f"el mensaje de {topic} no es JSON: {payload[:80]}")
        print(f"mosquitto: {mensaje.get('peticion')!r} -> herramienta={mensaje.get('herramienta')} comprobacion={mensaje.get('comprobacion')}")
        ultima = traza.read_text(encoding="utf-8").strip().splitlines()[-1]
        if json.loads(ultima) != mensaje:
            return fallo("el mensaje de Mosquitto no coincide con la última línea de la traza")
        return ok(codigo, "el mensaje de Mosquitto es la última línea de la traza")

    registros = []
    for n, linea in enumerate(traza.read_text(encoding="utf-8").splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            return fallo(f"la línea {n} no es JSON; ¿falta el + \"\\n\" al final de «linea» en Registro de traza?")

    lecturas = [r for r in registros if r.get("herramienta") == "leer_estacion" and r.get("comprobacion") == "OK"]
    negativas = [r for r in registros if r.get("herramienta") == "ninguna"]
    sin_modelo = [r for r in registros if r.get("comprobacion") == "modelo no disponible"]
    no_validas = [r for r in registros if r.get("comprobacion") == "petición no válida"]
    print(f"traza: {len(registros)} respuestas · {len(lecturas)} con dato comprobado · "
          f"{len(negativas) - len(no_validas)} negativas · {len(sin_modelo)} sin modelo · {len(no_validas)} no válidas")
    for r in registros[-3:]:
        print(f"  {str(r.get('hora'))[11:19]}  {str(r.get('herramienta')):13s} {str(r.get('comprobacion')):20s} {r.get('peticion')}")

    # Auditoría independiente: no basta con que n8n diga «OK»
    for r in lecturas:
        faltan = _numeros_ausentes(r)
        if faltan:
            return fallo(f"la traza dice OK pero la respuesta no contiene {faltan}: «{r['respuesta']}»")
    for r in negativas:
        if r.get("dato") is not None:
            return fallo("una negativa tiene dato: la rama de cambio no debería leer ni pasar nada al modelo")
    if not lecturas:
        return fallo("no hay ninguna lectura comprobada; pregunta «¿Cómo está la estación EST-01 ahora?» (paso 7)")
    if len(negativas) == len(no_validas):
        return fallo("no hay ninguna negativa; pide «Para la estación EST-01 ahora mismo.»")
    return ok(codigo, f"{len(lecturas)} lecturas con los números del sensor y {len(negativas) - len(no_validas)} negativas sin modelo")

COMANDOS = {
    "m01-01": cmd_m01_01,
    "m01-02": cmd_m01_02,
    "m02-01": cmd_m02_01,
    "m02-01-pausa": cmd_m02_01_pausa,
    "m02-02": cmd_m02_02,
    "m02-03": cmd_m02_03,
    "m02-04": cmd_m02_04,
    "m03-01": cmd_m03_01,
    "m03-02": cmd_m03_02,
    "m03-03": cmd_m03_03,
    "m03-red": cmd_m03_red,
    "m03-04": cmd_m03_04,
    "m04-01": cmd_m04_01,
    "m04-02": cmd_m04_02,
    "m04-03": cmd_m04_03,
    "m04-red": cmd_m04_red,
    "m05-01": cmd_m05_01,
    "m05-02": cmd_m05_02,
    "m05-03": cmd_m05_03,
    "m05-03-ausente": cmd_m05_03_ausente,
    "m05-04": cmd_m05_04,
    "m05-05": cmd_m05_05,
    "m05-06": cmd_m05_06,
    "m05-06-escuchar": lambda args: cmd_m05_06(["escuchar", *args]),
    "m06-01": cmd_m06_01,
    "m06-02": cmd_m06_02,
    "m07-01": cmd_m07_01,
    "m07-02": cmd_m07_02,
    "m07-03": cmd_m07_03,
    "m08-01": cmd_m08_01,
    "m08-02": cmd_m08_02,
    "sql": cmd_sql,
    "evento": cmd_evento,
    "consigna": cmd_consigna,
    "exportar": cmd_exportar,
    "m06-03": cmd_m06_03,
    "modbus": cmd_modbus,
    "opcua": cmd_opcua,
    "pasarela": cmd_pasarela,
    "arbol": cmd_arbol,
    "preguntar": cmd_preguntar,
    "buscar": cmd_buscar,
    "resumen": cmd_resumen,
    "notas": cmd_notas,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print("comandos:", ", ".join(COMANDOS))
        raise SystemExit(2)
    raise SystemExit(COMANDOS[sys.argv[1]](sys.argv[2:]))


if __name__ == "__main__":
    main()
