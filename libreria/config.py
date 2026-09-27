"""
Configuración central de LibrerIA.
Si quieres cambiar algo (modelo, rutas, umbrales), cámbialo AQUÍ y solo aquí.
"""

from pathlib import Path

# --------------------------------------------------
# RUTAS
# --------------------------------------------------

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_DATOS = RAIZ / "data"

CSV_ORIGINAL = CARPETA_DATOS / "books.csv"             # catálogo en bruto (lo pones tú)
CSV_LIMPIO = CARPETA_DATOS / "books_clean.csv"         # lo genera preparar_datos.py
EMBEDDINGS = CARPETA_DATOS / "book_embeddings.npy"     # lo genera preparar_datos.py

# --------------------------------------------------
# MODELO DE EMBEDDINGS
# --------------------------------------------------
# Multilingüe: una consulta en español encuentra libros descritos en inglés.
# Si lo cambias, tienes que volver a ejecutar preparar_datos.py.

MODELO_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"

# --------------------------------------------------
# DICTADO POR VOZ (faster-whisper)
# --------------------------------------------------
# "tiny" (~75 MB, más rápido, se equivoca más) · "base" (~150 MB) · "small" (~480 MB, mejor)

MODELO_VOZ = "base"

# --------------------------------------------------
# OLLAMA (OPCIONAL)
# --------------------------------------------------
# LibrerIA funciona sin Ollama. Solo se usa desde la terminal:
#   python consola.py --ollama

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODELO = "qwen3:1.7b"
OLLAMA_TIMEOUT = 60  # segundos

# --------------------------------------------------
# PALABRAS VAGAS → NÚMEROS
# --------------------------------------------------
# "algo corto" no dice cuántas páginas. Estos son los valores que usamos.

PAGINAS_CORTO = 250      # "corto", "cortito", "ligero", "rápido de leer"
PAGINAS_LARGO = 500      # "tocho", "largo"
PAGINAS_NO_LARGO = 400   # "que no sea un tocho", "no muy largo"
RATING_BIEN_VALORADO = 4.0

# --------------------------------------------------
# RECOMENDACIÓN
# --------------------------------------------------

RESULTADOS_POR_DEFECTO = 5

# Peso del perfil de Goodreads frente a la consulta escrita (0 a 1).
PESO_PERFIL = 0.3

# Cuánto se penaliza un libro que se parece a lo que el usuario NO quiere.
PESO_EXCLUSION = 0.6
