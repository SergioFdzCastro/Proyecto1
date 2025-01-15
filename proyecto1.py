import numpy as np
import pandas as pd

lectura_csv = pd.read_csv("MoviesOnStreamingPlatforms.csv", 
                            usecols=['Title', 'Valoracion', 'Age', 'Netflix', 'Hulu', 'Prime Video', 'Disney+'])

# Preguntar al usuario qué plataforma le gusta
while True:
    pregunta_plataforma = input("¿Cuál es tu plataforma favorita? (Netflix, Hulu, Prime Video, Disney+): ").strip().title()

    # Verificamos que la plataforma exista
    plataformas_csv = ['Netflix', 'Hulu', 'Prime Video', 'Disney+']
    if pregunta_plataforma not in plataformas_csv:
        print("Plataforma no válida. Por favor, escoja entre estas 4: Netflix, Hulu, Prime Video, Disney+.")
    else:
        # Filtro las películas disponibles en la plataforma que hemos seleccionado
        peliculas_en_plataforma = lectura_csv[lectura_csv[pregunta_plataforma] == 1]

        # Ordenar las películas por valoración en orden descendente
        orden_peliculas = peliculas_en_plataforma.sort_values(by='Valoracion', ascending=False)

        # Las 10 películas mejor valoradas
        top_10_peliculas = orden_peliculas.head(10)

        print(f"\nLas 10 películas más valoradas en {pregunta_plataforma} son:\n")
        print(top_10_peliculas[['Title', 'Valoracion']])
        
        # Preguntar por el título de una película
        while True:
            titulo_pelicula = input("\n¿Quieres saber en qué plataforma está una película? Ingresa el título (o 'salir' para terminar): ").strip()

            if titulo_pelicula.lower() == 'salir':
                print("¡Hasta luego!")
                break

            # Buscar la película
            pelicula_encontrada = lectura_csv[lectura_csv['Title'].str.contains(titulo_pelicula, case=False, na=False)]

            if not pelicula_encontrada.empty:
                # Mostrar la plataforma en la que se encuentra la película
                plataformas_disponibles = []
                for plataforma in plataformas_csv:
                    if pelicula_encontrada[plataforma].any():
                        plataformas_disponibles.append(plataforma)
                
                print(f"La película '{titulo_pelicula}' se encuentra en las siguientes plataformas: {', '.join(plataformas_disponibles)}.")
            else:
                print("No se encontró ninguna película con ese título. Intenta de nuevo.")

        break
