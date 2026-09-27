"""
Personalización: nombre de la asistente, textos, colores, imágenes y pictogramas.

Todo se cambia en la carpeta  personalizacion/  sin tocar el código:
  - personalizacion/marca.json      → textos (por idioma), pictogramas y colores
  - personalizacion/imagenes/       → lia.png, logo.png, fondo.png, cabecera.png
  - personalizacion/pictogramas/    → <id>.png para cada pictograma
"""

import base64
import json
import mimetypes

from libreria import config

CARPETA = config.RAIZ / "personalizacion"
CARPETA_IMAGENES = CARPETA / "imagenes"
CARPETA_PICTOGRAMAS = CARPETA / "pictogramas"
EXTENSIONES = [".png", ".jpg", ".jpeg", ".webp", ".svg"]

POR_DEFECTO = {
    "asistente": "Lía",
    "libreria": "Tu librería",
    "idioma_por_defecto": "es",
    "idiomas": ["es"],
    "textos": {
        "es": {
            "titulo": "Pregúntale a Lía",
            "subtitulo": "Cuéntale qué te apetece leer y buscará entre los libros que tenemos aquí.",
            "saludo": "¡Hola! Soy Lía. ¿Qué te apetece leer?",
            "placeholder": "Escribe aquí lo que te apetece leer…",
            "aviso_librero": "¿Prefieres hablar con una persona? Acércate al mostrador.",
            "sugerencias": [],
        }
    },
    "pictogramas": [],
    "colores": {
        "fondo": "#FBF6EC",
        "tarjeta": "#FFFDF8",
        "texto": "#3B2F2A",
        "texto_suave": "#7A6A5F",
        "acento": "#B5573A",
        "suave": "#F1E4CF",
    },
    "opacidad_fondo": 0.88,
    "url_publica": "",
}


def cargar_marca():
    marca = json.loads(json.dumps(POR_DEFECTO))  # copia
    ruta = CARPETA / "marca.json"
    if ruta.exists():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        colores = datos.pop("colores", {})
        marca.update(datos)
        marca["colores"].update(colores)
    return marca


def textos_marca(marca, idioma):
    """Textos de la librería en ese idioma (si falta alguno, los del idioma por defecto)."""
    base = marca["textos"].get(marca["idioma_por_defecto"]) or next(iter(marca["textos"].values()))
    return {**base, **marca["textos"].get(idioma, {})}


def _buscar(carpeta, nombre):
    for extension in EXTENSIONES:
        ruta = carpeta / f"{nombre}{extension}"
        if ruta.exists():
            return ruta
    return None


def buscar_imagen(nombre):
    """Ruta de personalizacion/imagenes/<nombre>.(png|jpg|...) o None."""
    return _buscar(CARPETA_IMAGENES, nombre)


def _data_uri(ruta):
    if ruta is None:
        return None
    tipo = "image/svg+xml" if ruta.suffix == ".svg" else (mimetypes.guess_type(ruta.name)[0] or "image/png")
    return f"data:{tipo};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


def imagen_data_uri(nombre):
    """La imagen incrustada como texto (data URI) para usarla en HTML/CSS."""
    return _data_uri(buscar_imagen(nombre))


def pictograma_data_uri(identificador):
    return _data_uri(_buscar(CARPETA_PICTOGRAMAS, identificador))
