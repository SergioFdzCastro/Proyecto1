from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import requests
from surprise import SVD, Dataset, Reader
import secrets  # Importamos el módulo para generar la clave secreta

app = Flask(__name__)

# Establecemos la clave secreta para la sesión
app.secret_key = secrets.token_hex(16)  # Genera una clave secreta aleatoria

app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\Sergio\Desktop\Proyecto1\data\usuarios.db'

db = SQLAlchemy(app)

# API Key de OMDb
OMDB_API_KEY = 'e146ab4a'

# Modelo para la base de datos de usuarios
class usuarios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    favoritos = db.Column(db.Text, nullable=True)  # Películas marcadas como favoritas (JSON)

# Cargar el archivo CSV de películas
lectura_csv = pd.read_csv("df_stream_kaggle.csv", 
                          usecols=['title', 'description', 'release_year', 'runtime', 
                                   'genres', 'production_countries', 'imdb_score', 
                                   'tmdb_score', 'streaming_service'])

# Calcular la calificación promedio de 'imdb_score' y 'tmdb_score'
lectura_csv['average_rating'] = lectura_csv[['imdb_score', 'tmdb_score']].mean(axis=1)

# Crear un dataset de calificaciones para usar con Surprise
# Usamos un único 'userId' para simular calificaciones por un solo usuario
calificaciones_df = pd.DataFrame({
    'userId': [1] * len(lectura_csv),  # Usamos el mismo 'userId' (1) para todas las películas
    'title': lectura_csv['title'],
    'rating': lectura_csv['average_rating']  # Usamos la calificación promedio
})

# Configuración de Surprise para crear el modelo
reader = Reader(rating_scale=(1, 10))  # Ajuste del rango de calificaciones
dataset = Dataset.load_from_df(calificaciones_df[['userId', 'title', 'rating']], reader)
trainset = dataset.build_full_trainset()
svd = SVD()
svd.fit(trainset)

# Función para obtener recomendaciones
def obtener_recomendaciones(user_id, top_n=10):
    peliculas = lectura_csv['title'].unique()  # Obtener los títulos únicos de las películas
    predicciones = [(pelicula, svd.predict(user_id, pelicula).est) for pelicula in peliculas]
    return sorted(predicciones, key=lambda x: x[1], reverse=True)[:top_n]

# Función para normalizar título de película para consulta a OMDB API
def normalizar_titulo(titulo):
    return titulo.strip().lower().replace(" ", "+")

# Función para obtener la URL de la portada de la película
def obtener_url_portada(titulo):
    titulo_normalizado = normalizar_titulo(titulo)
    url = f"http://www.omdbapi.com/?t={titulo_normalizado}&apikey={OMDB_API_KEY}"
    respuesta = requests.get(url)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        if datos.get('Response') == 'True':
            return datos.get('Poster')
    return None

# Rutas principales
@app.route('/')
def home():
    if 'id' in session:  # Usamos 'id' en vez de 'user_id'
        usuario = usuarios.query.get(session['id'])  # Buscamos al usuario por id
        return render_template('index.html', username=usuario.username)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = usuarios.query.filter_by(username=username).first()
        if usuario and check_password_hash(usuario.password, password):
            session['id'] = usuario.id  # Guardamos el id del usuario en la sesión
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='sha256')
        nuevo_usuario = usuarios(username=username, password=hashed_password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('id', None)  # Eliminamos el id de la sesión
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('login'))

@app.route('/buscar', methods=['POST'])
def buscar():
    titulo = request.form['titulo']
    peliculas = lectura_csv[lectura_csv['title'].str.contains(titulo, case=False, na=False)]
    resultados = [{
        'title': fila['title'],
        'description': fila['description'],
        'poster_url': obtener_url_portada(fila['title']) or '/static/imagenes/Imagen_por_defecto.jpg'
    } for _, fila in peliculas.iterrows()]
    return render_template('resultados.html', resultados=resultados)

@app.route('/recomendar')
def recomendar():
    if 'id' not in session:
        flash('Por favor, inicia sesión para obtener recomendaciones.', 'warning')
        return redirect(url_for('login'))
    usuario = usuarios.query.get(session['id'])  # Consultamos al usuario por su id
    recomendaciones = obtener_recomendaciones(str(usuario.id))
    resultados = [{
        'title': titulo,
        'score': score,
        'poster_url': obtener_url_portada(titulo) or '/static/imagenes/Imagen_por_defecto.jpg'
    } for titulo, score in recomendaciones]
    return render_template('recomendaciones.html', recomendaciones=resultados)

@app.route('/favoritos', methods=['GET', 'POST'])
def favoritos():
    if 'id' not in session:
        flash('Por favor, inicia sesión para gestionar favoritos.', 'warning')
        return redirect(url_for('login'))
    usuario = usuarios.query.get(session['id'])  # Consultamos al usuario por su id
    if request.method == 'POST':
        pelicula = request.form['pelicula']
        favoritos = [] if not usuario.favoritos else eval(usuario.favoritos)
        if pelicula not in favoritos:
            favoritos.append(pelicula)
            usuario.favoritos = str(favoritos)
            db.session.commit()
    favoritos = [] if not usuario.favoritos else eval(usuario.favoritos)
    return render_template('favoritos.html', favoritos=favoritos)

if __name__ == '__main__':
    app.run(debug=True)
