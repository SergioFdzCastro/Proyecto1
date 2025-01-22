from flask import Flask, render_template, request
import pandas as pd
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
from surprise import accuracy

app = Flask(__name__)

# Filtro personalizado: truncatewords
def truncatewords(value, num_words):
    """
    Trunca un texto después de un número específico de palabras.
    """
    words = value.split()
    if len(words) > num_words:
        return ' '.join(words[:num_words]) + '...'
    return value

# Registrar el filtro en Jinja2
app.jinja_env.filters['truncatewords'] = truncatewords

# Cargar el archivo CSV
lectura_csv = pd.read_csv(
    "df_stream_kaggle.csv", 
    usecols=['title', 'description', 'release_year', 'runtime', 'genres', 'production_countries', 'streaming_service', 'imdb_score']
)

# Diccionario de imágenes por plataforma
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
}

# Crear el modelo de SVD
def entrenar_modelo_svd(dataframe):
    reader = Reader(rating_scale=(0, 10))  # Escala de puntuación
    data = Dataset.load_from_df(dataframe[['title', 'streaming_service', 'imdb_score']], reader)
    
    trainset, testset = train_test_split(data, test_size=0.2)
    
    model = SVD()
    model.fit(trainset)
    
    predictions = model.test(testset)
    accuracy.rmse(predictions)
    
    return model

modelo_svd = entrenar_modelo_svd(lectura_csv)

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = pd.DataFrame()
    plataformas_pelicula = []
    mensaje_error = None
    peliculas_por_edad = pd.DataFrame()
    recomendaciones = []

    if request.method == 'POST':
        # Buscar por plataforma
        if 'plataforma' in request.form:
            plataforma = request.form['plataforma'].strip().lower()
            resultado = lectura_csv[lectura_csv['streaming_service'].str.contains(plataforma, case=False, na=False)]
            
            # Verificar si el DataFrame resultado está vacío
            if resultado.empty:
                mensaje_error = f"No se encontraron películas en la plataforma '{plataforma}'."

        # Buscar por título
        if 'titulo' in request.form:
            titulo_pelicula = request.form['titulo'].strip()
            pelicula_encontrada = lectura_csv[lectura_csv['title'].str.contains(titulo_pelicula, case=False, na=False)]
            
            # Verificar si el DataFrame no está vacío
            if not pelicula_encontrada.empty:
                for plataforma in pelicula_encontrada['streaming_service'].unique():
                    plataformas_pelicula.append({
                        'name': plataforma,
                        'image': IMAGENES_EN_PLATAFORMA.get(plataforma, '/static/imagenes/Imagen_por_defecto.png')
                    })
            else:
                mensaje_error = f"No se encontró ninguna película con el título '{titulo_pelicula}'."

        # Buscar por edad
        if 'edad' in request.form:
            try:
                edad = int(request.form['edad'].strip())
                if edad > 0:
                    anio_actual = pd.Timestamp.now().year
                    anios_interes = list(range(anio_actual - edad - 5, anio_actual - edad + 5))
                    peliculas_por_edad = lectura_csv[lectura_csv['release_year'].isin(anios_interes)].sort_values(by='imdb_score', ascending=False).head(10)
                    
                    # Verificar si no hay resultados
                    if peliculas_por_edad.empty:
                        mensaje_error = "No se encontraron películas para los años seleccionados."
                else:
                    mensaje_error = "Por favor, ingresa una edad válida."
            except ValueError:
                mensaje_error = "Por favor, ingresa una edad numérica válida."

        # Generar recomendaciones con SVD
        if 'recomendar' in request.form:
            titulo_base = request.form['recomendar'].strip()
            if titulo_base in lectura_csv['title'].values:
                # Predecir puntuaciones para todas las películas
                predicciones = []
                for pelicula in lectura_csv['title'].unique():
                    pred = modelo_svd.predict(uid=titulo_base, iid=pelicula)
                    predicciones.append((pelicula, pred.est))
                
                # Ordenar por puntuación predicha
                recomendaciones = sorted(predicciones, key=lambda x: x[1], reverse=True)[:10]
                recomendaciones = [
                    {
                        'title': rec[0],
                        'predicted_score': rec[1],
                        'image': IMAGENES_EN_PLATAFORMA.get(
                            lectura_csv.loc[lectura_csv['title'] == rec[0], 'streaming_service'].iloc[0],
                            '/static/imagenes/Imagen_por_defecto.png'
                        ),
                    }
                    for rec in recomendaciones
                ]
            else:
                mensaje_error = f"No se encontraron recomendaciones para '{titulo_base}'."

    return render_template(
        'filmatch.html', 
        resultado=resultado.to_dict(orient='records') if not resultado.empty else None, 
        plataformas_pelicula=plataformas_pelicula, 
        mensaje_error=mensaje_error,
        peliculas_por_edad=peliculas_por_edad.to_dict(orient='records') if not peliculas_por_edad.empty else None,
        recomendaciones=recomendaciones
    )

if __name__ == '__main__':
    app.run(debug=True)
