from flask import Flask, render_template, request
import pandas as pd
import requests
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from surprise import accuracy

app = Flask(__name__)

OMDB_API_KEY = 'e146ab4a'

# Cargar el archivo CSV
lectura_csv = pd.read_csv("df_stream_kaggle.csv", 
                          usecols=['title','description','release_year','runtime','genres','production_countries',
                                   'imdb_score', 'tmdb_score','streaming_service','name','primaryName'])

# Crear un conjunto de calificaciones simuladas basadas en el 'imdb_score'
# Usamos el 'imdb_score' como proxy para las calificaciones de los usuarios
# Supongamos que cada película tiene una calificación por cada usuario
calificaciones_df = pd.DataFrame({
    'userId': [str(i) for i in range(len(lectura_csv))],  # Creando IDs ficticios de usuario
    'title': lectura_csv['title'],  # Títulos de las películas
    'rating': lectura_csv['imdb_score']  # Usamos 'imdb_score' como calificación
})

# Configurar el lector para Surprise
reader = Reader(rating_scale=(1, 10))  # IMDb rating scale is from 1 to 10
dataset = Dataset.load_from_df(calificaciones_df[['userId', 'title', 'rating']], reader)

# Entrenar el modelo SVD
trainset = dataset.build_full_trainset()
svd = SVD()
svd.fit(trainset)

# Función para obtener recomendaciones
def obtener_recomendaciones(user_id, top_n=10):
    """Genera las top_n recomendaciones para un usuario"""
    peliculas = lectura_csv['title'].unique()
    predicciones = []

    for pelicula in peliculas:
        pred = svd.predict(user_id, pelicula)
        predicciones.append((pelicula, pred.est))  # (nombre_pelicula, predicción)

    # Ordenar las recomendaciones por la calificación predicha
    recomendaciones = sorted(predicciones, key=lambda x: x[1], reverse=True)[:top_n]
    return recomendaciones

def normalizar_titulo(titulo):
    """Normaliza el título para ser compatible con OMDb API."""
    return titulo.strip().lower().replace(" ", "+")

def obtener_url_portada(titulo):
    """Obtiene la URL de la portada desde OMDb API."""
    titulo_normalizado = normalizar_titulo(titulo)
    url = f"http://www.omdbapi.com/?t={titulo_normalizado}&apikey={OMDB_API_KEY}"
    respuesta = requests.get(url)

    if respuesta.status_code == 200:
        datos = respuesta.json()
        if datos.get('Response') == 'True':
            return datos.get('Poster')  # Retorna la URL de la portada
    return None  # Devuelve None si no encuentra la portada

# Filtro personalizado para truncar palabras
def truncate_words(text, num_words):
    words = text.split()
    return ' '.join(words[:num_words])

# Registrar el filtro
app.jinja_env.filters['truncatewords'] = truncate_words

IMAGENES_EN_PLATAFORMA = {
    'netflix': '/static/imagenes/netflix.png',
    'amazon': '/static/imagenes/amazon.png',
    'hulu': '/static/imagenes/hulu.png',
    'disney': '/static/imagenes/disney.png',
    'hbo': '/static/imagenes/hbo.png',
    'paramount': '/static/imagenes/paramount.png',
    'crunchyroll': '/static/imagenes/crunchyroll.png',
    'darkmatter': '/static/imagenes/dm.jpg',
    'rakuten': '/static/imagenes/rakuten.png',
    # Añade más plataformas aquí
}

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    plataformas_pelicula = None
    mensaje_error = None
    peliculas_por_edad = None
    recomendaciones = None  # Inicializamos la variable para recomendaciones

    if request.method == 'POST':
        # Manejo de plataformas
        if 'plataforma' in request.form:
            plataformas = request.form.getlist('plataforma')  # Cambié a getlist para obtener múltiples valores
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
                        'poster_url': poster_url or '/static/imagenes/Imagen_por_defecto.jpg'  # Imagen por defecto
                    })
            else:
                mensaje_error = f"No se encontraron películas en las plataformas seleccionadas."

        # Recomendaciones basadas en SVD (ejemplo simple de recomendaciones para un usuario)
        if 'user_id' in request.form:
            user_id = request.form['user_id'].strip()  # Este sería el ID del usuario que se pasa por el formulario
            recomendaciones = obtener_recomendaciones(user_id)

            if recomendaciones:
                recomendaciones_con_imagenes = []
                for titulo, score in recomendaciones:
                    poster_url = obtener_url_portada(titulo)
                    recomendaciones_con_imagenes.append({
                        'title': titulo,
                        'poster_url': poster_url or '/static/imagenes/Imagen_por_defecto.jpg',  # Imagen por defecto
                        'score': score
                    })
                recomendaciones = recomendaciones_con_imagenes
            else:
                mensaje_error = "No se encontraron recomendaciones."

    return render_template('filmatch.html', 
                           resultado=resultado, 
                           plataformas_pelicula=plataformas_pelicula, 
                           mensaje_error=mensaje_error,
                           peliculas_por_edad=peliculas_por_edad,
                           recomendaciones=recomendaciones)  # Pasamos las recomendaciones a la plantilla

if __name__ == '__main__':
    app.run(debug=True)
