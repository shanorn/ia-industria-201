"""Constrúyelo tú (M02-03): tu propia limpieza de datos.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m02_03_mi_limpieza.py
"""
import pandas as pd

# --- Decisiones tuyas (las cambiarás en los pasos finales) -------------------
IMPOSIBLE = 9999            # valor que da el sensor cuando está clavado
DECIMAS_DESDE = 150         # por encima de esto, la temperatura viene en décimas de grado
HUECOS = "excluir"          # "excluir" = quitar la pieza; "media" = rellenar con la media

# --- PASO 1: leer el crudo (ya está hecho) -----------------------------------
crudo = pd.read_csv("/data/crudo.csv")        # en tu equipo: infra/data/crudo.csv
print(f"crudo: {len(crudo)} filas, columnas {list(crudo.columns)}")

# --- PASO 2: contar los problemas ----------------------------------------------
# (pega aquí el bloque del paso 2)
t = crudo["temperatura_c"]
huecos = int(t.isna().sum())
imposibles = int((t >= IMPOSIBLE).sum())
en_decimas = int(((t > DECIMAS_DESDE) & (t < IMPOSIBLE)).sum())
repetidas = int(crudo["pieza_id"].duplicated().sum())
print(f"huecos={huecos} imposibles={imposibles} en_decimas={en_decimas} repetidas={repetidas}")

# --- PASO 3: apartar los valores imposibles ------------------------------------
# (pega aquí el bloque del paso 3)
trabajo = crudo.copy()
apartadas = trabajo[trabajo["temperatura_c"] >= IMPOSIBLE]
trabajo.loc[trabajo["temperatura_c"] >= IMPOSIBLE, "temperatura_c"] = None
print(f"apartadas por sensor clavado: {list(apartadas['pieza_id'])}")

# --- PASO 4: corregir las unidades ---------------------------------------------
# (pega aquí el bloque del paso 4)
en_decimas = trabajo["temperatura_c"] > DECIMAS_DESDE
trabajo.loc[en_decimas, "temperatura_c"] = trabajo.loc[en_decimas, "temperatura_c"] / 10
print(f"corregidas de décimas a grados: {int(en_decimas.sum())}; máxima ahora={trabajo['temperatura_c'].max():.2f} °C")

# --- PASO 5: decidir qué hacer con los huecos ----------------------------------
# (pega aquí el bloque del paso 5)
sin_dato = trabajo["temperatura_c"].isna()
if HUECOS == "media":
    media = round(trabajo["temperatura_c"].mean(), 2)
    trabajo["temperatura_c"] = trabajo["temperatura_c"].fillna(media)
    print(f"huecos rellenados con la media {media} °C: {int(sin_dato.sum())}")
else:
    trabajo = trabajo[~sin_dato]
    print(f"piezas excluidas por no tener temperatura: {int(sin_dato.sum())}")
limpio = trabajo.drop_duplicates("pieza_id")
limpio.to_csv("/data/mi_limpio.csv", index=False)
print(f"mi_limpio.csv: {len(limpio)} piezas")

# --- PASO 6: comprobar contra el limpio del comando ----------------------------
# (pega aquí el bloque del paso 6)
del_comando = pd.read_csv("/data/limpio.csv")
mismas_piezas = set(limpio["pieza_id"]) == set(del_comando["pieza_id"])
union = limpio.merge(del_comando, on="pieza_id", suffixes=("_mio", "_comando"))
diferentes = int((union["temperatura_c_mio"].round(2) != union["temperatura_c_comando"].round(2)).sum())
print(f"mismas piezas que el comando: {mismas_piezas}  temperaturas distintas: {diferentes}")