"""
Versión por terminal (para probar rápido sin interfaz).

    python consola.py
    python consola.py --goodreads ejemplos/goodreads_ejemplo.csv
    python consola.py --ollama
"""

import argparse

from libreria import goodreads, motor
from libreria.interprete import interpretar_consulta, resumen


def main():
    parser = argparse.ArgumentParser(description="LibrerIA por terminal")
    parser.add_argument("--goodreads", help="Ruta a tu CSV exportado de Goodreads")
    parser.add_argument("--ollama", action="store_true", help="Usar Ollama (opcional)")
    args = parser.parse_args()

    print("Cargando LibrerIA...")
    catalogo, embeddings = motor.cargar_catalogo()
    motor.cargar_modelo()

    perfil = None
    if args.goodreads:
        perfil = goodreads.crear_perfil(args.goodreads, catalogo, embeddings)
        print(f"Goodreads: {perfil['en_catalogo']} de {perfil['total']} libros están en el catálogo.")
        if perfil["vector"] is None:
            print("Ninguno de tus favoritos está en el catálogo: no personalizo.")
            perfil = None

    while True:
        texto = input("\n¿Qué te apetece leer? (Enter vacío para salir): ").strip()
        if not texto and not perfil:
            break

        pref = interpretar_consulta(texto, usar_ollama=args.ollama)
        if resumen(pref):
            print("He entendido:", resumen(pref))

        resultados = motor.recomendar_libros(
            consulta=pref["consulta_semantica"],
            max_paginas=pref["max_paginas"],
            min_paginas=pref["min_paginas"],
            min_rating=pref["min_rating"],
            excluir=pref["excluir"],
            perfil=perfil,
        )

        if not resultados:
            print("No hay libros que cumplan todo eso.")
        for n, libro in enumerate(resultados, 1):
            print(f"\n{n}. {libro['titulo']} — {libro['autor']}")
            print(f"   {libro['categoria']} · {libro['paginas']} págs · ⭐ {libro['rating']}")

        if not texto:
            break


if __name__ == "__main__":
    main()
