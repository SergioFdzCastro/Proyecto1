from flask import Flask, render_template, request
import pandas as pd
import requests
from surprise import SVD, Dataset, Reader

app = Flask(__name__)

OMDB_API_KEY = 'e146ab4a'

# Cargar el archivo CSV
lectura_csv = pd.read_csv("df_stream_kaggle.csv", 
                          usecols=['title','description','release_year','runtime','genres','production_countries',
                                   'imdb_score', 'tmdb_score','streaming_service','name','primaryName'])

# Crear un conjunto de calificaciones simuladas
calificaciones_df = pd.DataFrame({
    'userId': [str(i) for i in range(len(lectura_csv))],  
    'title': lectura_csv['title'],
    'rating': lectura_csv['imdb_score']
})

# Configurar el lector para Surprise
reader = Reader(rating_scale=(1, 10))
dataset = Dataset.load_from_df(calificaciones_df[['userId', 'title', 'rating']], reader)

# Entrenar el modelo SVD
trainset = dataset.build_full_trainset()
svd = SVD()
svd.fit(trainset)

def obtener_recomendaciones(user_id, top_n=10):
    """Genera las top_n recomendaciones para un usuario"""
    peliculas = lectura_csv['title'].unique()
    predicciones = []

    for pelicula in peliculas:
        pred = svd.predict(user_id, pelicula)
        predicciones.append((pelicula, pred.est))

    recomendaciones = sorted(predicciones, key=lambda x: x[1], reverse=True)[:top_n]
    return recomendaciones

def normalizar_titulo(titulo):
    return titulo.strip().lower().replace(" ", "+")

def obtener_url_portada(titulo):
    """Obtiene la URL de la portada desde OMDb API."""
    titulo_normalizado = normalizar_titulo(titulo)
    url = f"http://www.omdbapi.com/?t={titulo_normalizado}&apikey={OMDB_API_KEY}"
    respuesta = requests.get(url)

    if respuesta.status_code == 200:
        datos = respuesta.json()
        if datos.get('Response') == 'True':
            return datos.get('Poster')
    return None

def truncate_words(text, num_words):
    """Truncar la descripción de una película."""
    words = text.split()
    return ' '.join(words[:num_words])

# Registrar el filtro de truncado
app.jinja_env.filters['truncatewords'] = truncate_words

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    resultado_pelicula = None
    mensaje_error = None
    recomendaciones = None

    if request.method == 'POST':
        # Búsqueda por título
        if 'titulo' in request.form:
            titulo = request.form['titulo'].strip()
            peliculas_encontradas = lectura_csv[lectura_csv['title'].str.contains(titulo, case=False, na=False)]

            if not peliculas_encontradas.empty:
                resultado_pelicula = []
                for _, fila in peliculas_encontradas.iterrows():
                    titulo = fila['title']
                    poster_url = obtener_url_portada(titulo)
                    resultado_pelicula.append({
                        'title': fila['title'],
                        'description': fila['description'],
                        'release_year': fila['release_year'],
                        'streaming_service': fila['streaming_service'],
                        'poster_url': poster_url or '/static/imagenes/Imagen_por_defecto.jpg'
                    })
            else:
                mensaje_error = "No se encontraron películas con ese título."

        # Búsqueda por plataforma
        if 'plataforma' in request.form:
            plataformas = request.form.getlist('plataforma')
            peliculas_en_plataforma = pd.DataFrame()

            for plataforma in plataformas:
                plataforma_normalizada = plataforma.strip().title()
                peliculas_en_plataforma = pd.concat([peliculas_en_plataforma, 
                                                     lectura_csv[lectura_csv['streaming_service'].str.contains(plataforma_normalizada, case=False, na=False)]], 
                                                     ignore_index=True)
            
            if not peliculas_en_plataforma.empty:
                orden_peliculas = peliculas_en_plataforma.sort_values(by='imdb_score', ascending=False)
                resultado = []

                for _, fila in orden_peliculas.head(10).iterrows():
                    titulo = fila['title']
                    poster_url = obtener_url_portada(titulo)
                    resultado.append({
                        'title': fila['title'],
                        'description': fila['description'],
                        'genres': fila['genres'],
                        'release_year': fila['release_year'],
                        'runtime': fila['runtime'],
                        'imdb_score': fila['imdb_score'],
                        'poster_url': poster_url or '/static/imagenes/Imagen_por_defecto.jpg'
                    })
            else:
                mensaje_error = f"No se encontraron películas en las plataformas seleccionadas."

        # Recomendaciones basadas en SVD
        if 'user_id' in request.form:
            user_id = request.form['user_id'].strip()
            recomendaciones = obtener_recomendaciones(user_id)

            if recomendaciones:
                recomendaciones_con_imagenes = []
                for titulo, score in recomendaciones:
                    poster_url = obtener_url_portada(titulo)
                    fila_pelicula = lectura_csv[lectura_csv['title'] == titulo].iloc[0]
                    plataforma = fila_pelicula['streaming_service']
                    genero = fila_pelicula['genres']
                    recomendaciones_con_imagenes.append({
                        'title': titulo,
                        'poster_url': poster_url or '/static/imagenes/Imagen_por_defecto.jpg',
                        'score': score,
                        'platform': plataforma,
                        'genres': genero
                    })
                recomendaciones = recomendaciones_con_imagenes
            else:
                mensaje_error = "No se encontraron recomendaciones."

    return render_template('filmatch.html', 
                           resultado=resultado, 
                           resultado_pelicula=resultado_pelicula, 
                           mensaje_error=mensaje_error,
                           recomendaciones=recomendaciones)

if __name__ == '__main__':
    app.run(debug=True)
