from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import requests
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuración básica
app.secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\Sergio\Desktop\Proyecto1\data\usuarios.db'
db = SQLAlchemy(app)

# API Key de OMDb
OMDB_API_KEY = 'e146ab4a'

# Modelo para la base de datos de usuarios
class usuarios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    favoritos = db.Column(db.Text, nullable=True)  # Películas favoritas almacenadas como una lista
    busquedas_recientes = db.Column(db.Text, nullable=True)  # Búsquedas del usuario almacenadas como una lista

# Leer archivo CSV de películas
lectura_csv = pd.read_csv("filmatch.csv", 
                          usecols=['title', 'description', 'release_year', 'runtime', 
                                   'genres', 'production_countries', 'score', 'streaming_service'], 
                          encoding='ISO-8859-1')

# Normalizamos la columna de plataformas en el CSV
lectura_csv['streaming_service'] = lectura_csv['streaming_service'].str.lower().str.strip()

# Función para normalizar título para consulta a OMDb
def normalizar_titulo(titulo):
    return titulo.strip().lower().replace(" ", "+")

# Obtener URL de portada de película desde OMDb
def obtener_url_portada(titulo):
    titulo_normalizado = normalizar_titulo(titulo)
    url = f"http://www.omdbapi.com/?t={titulo_normalizado}&apikey={OMDB_API_KEY}"
    respuesta = requests.get(url)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        if datos.get('Response') == 'True':
            return datos.get('Poster')
    return None

# Filtro de plantilla para recortar texto
@app.template_filter('truncatewords')
def truncatewords_filter(text, num_words):
    if not text:
        return ''
    words = text.split()
    return ' '.join(words[:num_words])

# Rutas principales
@app.route('/')
def home():
    if 'id' in session:
        usuario = usuarios.query.get(session['id'])
        return render_template('filmatch.html', username=usuario.username)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = usuarios.query.filter_by(username=username).first()
        if usuario and check_password_hash(usuario.password, password):
            session['id'] = usuario.id
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        nuevo_usuario = usuarios(username=username, password=hashed_password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('id', None)
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('login'))

@app.route('/filmatch', methods=['GET', 'POST'])
def filmatch():
    resultado_pelicula = None
    mensaje_error = None
    recomendaciones = None

    if request.method == 'POST':
        if 'titulo' in request.form:
            # Búsqueda por título
            titulo = request.form['titulo']
            if 'id' in session:
                usuario = usuarios.query.get(session['id'])
                busquedas = usuario.busquedas_recientes.split(",") if usuario.busquedas_recientes else []
                if titulo not in busquedas:
                    busquedas.append(titulo)
                usuario.busquedas_recientes = ",".join(busquedas)
                db.session.commit()

            peliculas = lectura_csv[lectura_csv['title'].str.contains(titulo, case=False, na=False)]
            if not peliculas.empty:
                resultado_pelicula = [({
                    'title': fila['title'],
                    'description': fila['description'],
                    'poster_url': obtener_url_portada(fila['title']) or '/static/imagenes/Imagen_por_defecto.jpg',
                    'release_year': fila['release_year'],
                    'streaming_service': fila['streaming_service']
                }) for _, fila in peliculas.iterrows()]
            else:
                mensaje_error = 'No se encontraron películas con ese título.' 

        elif 'genero' in request.form and 'plataforma_favorita' in request.form:
            # Recomendaciones personalizadas basadas en género y plataforma
            genero = request.form['genero']
            plataforma_favorita = request.form['plataforma_favorita']
            recomendaciones = obtener_recomendaciones_por_preferencias(genero, plataforma_favorita)
                
    return render_template('filmatch.html', 
                           resultado_pelicula=resultado_pelicula, 
                           mensaje_error=mensaje_error, 
                           recomendaciones=recomendaciones)

# Función para obtener recomendaciones basadas en las respuestas a las preguntas
def obtener_recomendaciones_por_preferencias(genero, plataforma_favorita, top_n=10):
    # Filtrar las películas por género y plataforma
    peliculas_filtradas = lectura_csv[lectura_csv['genres'].str.contains(genero, case=False, na=False) &
                                      lectura_csv['streaming_service'].str.contains(plataforma_favorita, case=False, na=False)]
    
    # Si no se encuentran películas que coincidan, devolver un mensaje
    if peliculas_filtradas.empty:
        return "No se encontraron películas que coincidan con tus preferencias."
    
    recomendaciones = [(fila['title'], fila['score']) for _, fila in peliculas_filtradas.iterrows()]
    recomendaciones = sorted(recomendaciones, key=lambda x: x[1], reverse=True)
    return recomendaciones[:top_n]

if __name__ == '__main__':
    app.run(debug=True)
