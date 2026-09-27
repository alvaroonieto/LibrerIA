"""
PASO 1 — Ejecutar UNA vez (o cada vez que cambie el catálogo).

    python preparar_datos.py

Hace dos cosas:
  1. Limpia data/books.csv  → data/books_clean.csv
  2. Calcula los embeddings → data/book_embeddings.npy

La primera vez descarga el modelo (~470 MB), tarda unos minutos.
"""

import numpy as np
import pandas as pd

from libreria import config


def limpiar_catalogo():

    print(f"Leyendo {config.CSV_ORIGINAL} ...")
    df = pd.read_csv(config.CSV_ORIGINAL, dtype={"isbn13": str, "isbn10": str})
    print(f"  Libros en bruto: {len(df)}")

    # Sin descripción no podemos entender de qué va el libro
    df = df.dropna(subset=["description", "title"])
    df = df[df["description"].str.len() >= 40]

    # Mismo título y autor = mismo libro (ediciones repetidas)
    df = df.drop_duplicates(subset=["title", "authors"])

    # 0 páginas es un dato erróneo → lo tratamos como desconocido
    df["num_pages"] = df["num_pages"].replace(0, np.nan)

    # Rellenar huecos de texto
    for columna in ["subtitle", "authors", "categories", "thumbnail"]:
        if columna in df.columns:
            df[columna] = df[columna].fillna("")

    df["authors"] = df["authors"].str.replace(";", ", ")
    df["thumbnail"] = df["thumbnail"].str.replace("http://", "https://", regex=False)

    # Texto que se convierte en embedding: todo lo que describe el libro
    df["book_text"] = (
        df["title"] + ". " +
        df["subtitle"] + ". " +
        "Autor: " + df["authors"] + ". " +
        "Categoría: " + df["categories"] + ". " +
        df["description"]
    )

    columnas = [
        "isbn13", "title", "subtitle", "authors", "categories", "description",
        "published_year", "average_rating", "num_pages", "ratings_count",
        "thumbnail", "book_text",
    ]
    # Columnas opcionales para cuando uséis el catálogo de una librería/biblioteca
    for opcional in ["stock", "seccion"]:
        if opcional in df.columns:
            columnas.append(opcional)

    df = df[columnas].reset_index(drop=True)
    df.to_csv(config.CSV_LIMPIO, index=False)

    print(f"  Libros útiles: {len(df)}  →  guardado en {config.CSV_LIMPIO}")
    return df


def generar_embeddings(df):

    from sentence_transformers import SentenceTransformer

    print(f"\nCargando modelo {config.MODELO_EMBEDDINGS} ...")
    modelo = SentenceTransformer(config.MODELO_EMBEDDINGS)

    print("Calculando embeddings (puede tardar unos minutos) ...")
    embeddings = modelo.encode(
        df["book_text"].tolist(),
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,  # así la similitud coseno es un simple producto
    ).astype(np.float32)

    np.save(config.EMBEDDINGS, embeddings)
    print(f"  Embeddings: {embeddings.shape}  →  guardado en {config.EMBEDDINGS}")


if __name__ == "__main__":
    catalogo = limpiar_catalogo()
    generar_embeddings(catalogo)
    print("\nListo. Ahora ejecuta:  streamlit run app.py")
