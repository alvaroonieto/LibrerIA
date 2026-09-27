"""
Motor de recomendación.

Solo recomienda libros que están en el catálogo (data/books_clean.csv).
Ordena por similitud entre la consulta y la descripción de cada libro.
"""

import numpy as np
import pandas as pd

from libreria import config


# --------------------------------------------------
# CARGA (una sola vez; luego se reutiliza)
# --------------------------------------------------

_cache = {}


def cargar_catalogo():
    if "catalogo" not in _cache:
        if not config.CSV_LIMPIO.exists() or not config.EMBEDDINGS.exists():
            raise FileNotFoundError(
                "Faltan los datos procesados. Ejecuta primero:  python preparar_datos.py"
            )
        df = pd.read_csv(config.CSV_LIMPIO, dtype={"isbn13": str})
        embeddings = np.load(config.EMBEDDINGS).astype(np.float32)
        if len(df) != len(embeddings):
            raise ValueError(
                f"El catálogo tiene {len(df)} libros pero hay {len(embeddings)} embeddings. "
                "Vuelve a ejecutar:  python preparar_datos.py"
            )
        for columna in ["subtitle", "authors", "categories", "thumbnail", "description"]:
            df[columna] = df[columna].fillna("")
        _cache["catalogo"] = (df, embeddings)
    return _cache["catalogo"]


def cargar_modelo():
    if "modelo" not in _cache:
        from sentence_transformers import SentenceTransformer
        _cache["modelo"] = SentenceTransformer(config.MODELO_EMBEDDINGS)
    return _cache["modelo"]


def codificar(textos):
    """Texto(s) → vector(es) normalizados, comparables con los del catálogo."""
    modelo = cargar_modelo()
    return modelo.encode(textos, normalize_embeddings=True).astype(np.float32)


# --------------------------------------------------
# RECOMENDACIÓN
# --------------------------------------------------

def recomendar_libros(
    consulta="",
    cantidad=config.RESULTADOS_POR_DEFECTO,
    max_paginas=None,
    min_paginas=None,
    min_rating=None,
    excluir=None,
    perfil=None,
):
    """
    consulta  : texto libre ("novela negra en Escocia")
    excluir   : lista de cosas que el usuario NO quiere (["romance"])
    perfil    : resultado de goodreads.crear_perfil(), o None
    """

    df, embeddings = cargar_catalogo()

    # ---------- 1. Filtros duros ----------
    mascara = np.ones(len(df), dtype=bool)

    if max_paginas is not None:
        mascara &= (df["num_pages"] <= max_paginas).to_numpy()
    if min_paginas is not None:
        mascara &= (df["num_pages"] >= min_paginas).to_numpy()
    if min_rating is not None:
        mascara &= (df["average_rating"] >= min_rating).to_numpy()
    if "stock" in df.columns:  # catálogo real de librería/biblioteca
        mascara &= (df["stock"].fillna(0) > 0).to_numpy()
    if perfil is not None and perfil["leidos"]:
        mascara[list(perfil["leidos"])] = False  # no recomendar lo que ya ha leído

    if not mascara.any():
        return []

    # ---------- 2. Puntuación ----------
    consulta = (consulta or "").strip()
    vector_perfil = perfil["vector"] if perfil is not None else None

    if consulta:
        puntuacion = embeddings @ codificar(consulta)
        if vector_perfil is not None:
            puntuacion = (1 - config.PESO_PERFIL) * puntuacion + config.PESO_PERFIL * (embeddings @ vector_perfil)
    elif vector_perfil is not None:
        puntuacion = embeddings @ vector_perfil
    else:
        # Sin consulta ni perfil: los mejor valorados y más leídos
        rating = df["average_rating"].fillna(0).to_numpy()
        votos = np.log1p(df["ratings_count"].fillna(0).to_numpy())
        puntuacion = (rating / 5) * (votos / max(votos.max(), 1))

    # ---------- 3. Penalizar lo que NO quiere ----------
    for termino in excluir or []:
        parecido = embeddings @ codificar(termino)
        # Solo penaliza a los libros que se parecen MÁS de lo normal a ese término
        exceso = np.clip(parecido - np.median(parecido), 0, None)
        puntuacion = puntuacion - config.PESO_EXCLUSION * exceso

    # ---------- 4. Los mejores ----------
    puntuacion = np.where(mascara, puntuacion, -np.inf)
    cantidad = min(cantidad, int(mascara.sum()))
    mejores = np.argpartition(-puntuacion, cantidad - 1)[:cantidad]
    mejores = mejores[np.argsort(-puntuacion[mejores])]

    resultados = []
    for i in mejores:
        libro = df.iloc[i]
        resultados.append({
            "indice": int(i),
            "isbn13": libro["isbn13"],
            "titulo": libro["title"],
            "subtitulo": libro["subtitle"],
            "autor": libro["authors"],
            "categoria": libro["categories"],
            "descripcion": libro["description"],
            "paginas": None if pd.isna(libro["num_pages"]) else int(libro["num_pages"]),
            "rating": None if pd.isna(libro["average_rating"]) else float(libro["average_rating"]),
            "anio": None if pd.isna(libro["published_year"]) else int(libro["published_year"]),
            "portada": libro["thumbnail"],
            "seccion": libro["seccion"] if "seccion" in df.columns else None,
            "puntuacion": float(puntuacion[i]),
        })
    return resultados
