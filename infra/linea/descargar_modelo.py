"""Descarga única del modelo generativo a /modelos. Si ya está, no hace nada."""
import sys
import urllib.request

from linea.config import MODELO_PATH, MODELO_URL

MINIMO_BYTES = 400 * 1024 * 1024  # el GGUF pesa ~470 MB; menos es una descarga a medias


def main() -> int:
    if MODELO_PATH.exists() and MODELO_PATH.stat().st_size >= MINIMO_BYTES:
        print(f"modelo: ya está en {MODELO_PATH}", flush=True)
        return 0
    MODELO_PATH.parent.mkdir(parents=True, exist_ok=True)
    parcial = MODELO_PATH.with_suffix(".part")
    print(f"modelo: descargando {MODELO_URL} (~470 MB)", flush=True)
    try:
        urllib.request.urlretrieve(MODELO_URL, parcial)
    except Exception as error:  # sin red, proxy, Hugging Face caído...
        parcial.unlink(missing_ok=True)
        print(f"modelo: no se pudo descargar: {error}", file=sys.stderr, flush=True)
        return 1
    if parcial.stat().st_size < MINIMO_BYTES:
        parcial.unlink(missing_ok=True)
        print("modelo: la descarga llegó incompleta", file=sys.stderr, flush=True)
        return 1
    parcial.rename(MODELO_PATH)
    print(f"modelo: descargado en {MODELO_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
