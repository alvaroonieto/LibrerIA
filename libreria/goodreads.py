"""
Personalización con la exportación de Goodreads.

Goodreads no tiene API pública, pero cualquier usuario puede descargar su biblioteca:
    goodreads.com → My Books → Import and export → Export Library  →  CSV

Qué hacemos con ese CSV (todo en memoria, NO se guarda nada):
  1. Buscamos sus libros en nuestro catálogo (por ISBN o por título).
  2. Con los que puntuó con 4-5 estrellas creamos su "perfil lector"
     (la media de sus embeddings).
  3. El motor mezcla ese perfil con lo que escribe y no le recomienda
     libros que ya ha leído.
"""

import re
import unicodedata

import numpy as np
import pandas as pd

COLUMNAS_NECESARIAS = {"Title", "Author", "My Rating", "Exclusive Shelf"}


# --------------------------------------------------
# LEER EL CSV
# --------------------------------------------------

def leer_export(archivo):
    """archivo: ruta o fichero subido en Streamlit."""
    df = pd.read_csv(archivo, dtype=str).fillna("")
    faltan = COLUMNAS_NECESARIAS - set(df.columns)
    if faltan:
        raise ValueError(
            "Este CSV no parece una exportación de Goodreads. Faltan columnas: "
            + ", ".join(sorted(faltan))
        )
    # Goodreads escribe los ISBN así: ="9780439023481"
    for columna in ["ISBN", "ISBN13"]:
        if columna in df.columns:
            df[columna] = df[columna].str.replace(r'[="\s-]', "", regex=True)
    df["My Rating"] = pd.to_numeric(df["My Rating"], errors="coerce").fillna(0).astype(int)
    return df


# --------------------------------------------------
# EMPAREJAR CON EL CATÁLOGO
# --------------------------------------------------

def _normalizar_titulo(titulo):
    titulo = re.sub(r"\(.*?\)", "", str(titulo))          # "(Harry Potter, #1)"
    titulo = titulo.split(":")[0]                          # quitar subtítulo
    titulo = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", titulo.lower()).strip()


def _apellido(autor):
    partes = str(autor).split()
    return partes[-1].lower() if partes else ""


def emparejar(df_goodreads, catalogo):
    """Devuelve una lista con el índice del catálogo (o None) de cada libro de Goodreads."""

    por_isbn = {isbn: i for i, isbn in enumerate(catalogo["isbn13"].fillna("")) if isbn}
    por_titulo = {}
    for i, titulo in enumerate(catalogo["title"]):
        por_titulo.setdefault(_normalizar_titulo(titulo), []).append(i)

    indices = []
    for _, fila in df_goodreads.iterrows():
        isbn = fila.get("ISBN13", "")
        if isbn in por_isbn:
            indices.append(por_isbn[isbn])
            continue
        candidatos = por_titulo.get(_normalizar_titulo(fila["Title"]), [])
        apellido = _apellido(fila["Author"])
        elegido = None
        for i in candidatos:
            if apellido and apellido in str(catalogo.at[i, "authors"]).lower():
                elegido = i
                break
        indices.append(elegido)
    return indices


# --------------------------------------------------
# CREAR EL PERFIL
# --------------------------------------------------

def crear_perfil(archivo, catalogo, embeddings):

    df = leer_export(archivo)
    df["indice"] = emparejar(df, catalogo)
    en_catalogo = df[df["indice"].notna()].copy()
    en_catalogo["indice"] = en_catalogo["indice"].astype(int)

    # Leídos = estantería "read" / "currently-reading" o con nota
    leidos = en_catalogo[
        en_catalogo["Exclusive Shelf"].isin(["read", "currently-reading"])
        | (en_catalogo["My Rating"] > 0)
    ]

    # Gustados = 4 o 5 estrellas (5 cuenta el doble)
    gustados = leidos[leidos["My Rating"] >= 4]
    pesos = gustados["My Rating"].map({5: 2.0, 4: 1.0})

    # Si no puntuó nada, usamos los leídos sin nota (no los de 1-3 estrellas)
    if gustados.empty:
        gustados = leidos[leidos["My Rating"] == 0]
        pesos = pd.Series(1.0, index=gustados.index)

    vector = None
    if not gustados.empty:
        vector = np.average(embeddings[gustados["indice"].to_numpy()], axis=0, weights=pesos.to_numpy())
        vector = (vector / np.linalg.norm(vector)).astype(np.float32)

    return {
        "vector": vector,
        "leidos": set(leidos["indice"]),
        "total": len(df),
        "en_catalogo": len(en_catalogo),
        "gustados": gustados["Title"].tolist(),
    }
