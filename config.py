from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect  # Añadir esta importación
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave-secreta-predeterminada')
# Asegurar que CSRF solo aplique a métodos que modifican estado
app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']

# Inicializar protección CSRF
csrf = CSRFProtect(app)  # Añadir esta línea

# Configuración de la sesión para que expire al cerrar el navegador
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos de inactividad (opcional)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'mysql+pymysql://usuario:contraseña@localhost/nombre_base_datos')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Google OAuth
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Configuración de Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from modelo.models import Usuario
    return Usuario.query.get(int(user_id))

def registrar_actividad(usuario_id, accion, elemento):
    from modelo.models import ActividadReciente
    from datetime import datetime
    
    nueva_actividad = ActividadReciente(
        usuario_id=usuario_id,
        accion=accion,
        elemento=elemento,
        fecha=datetime.now()
    )
    
    db.session.add(nueva_actividad)
    db.session.commit()

"""
Soporte de archivos
"""
# Extensiones permitidas para subida de imágenes
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Extensiones permitidas para documentos genéticos
ALLOWED_DOC_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "webp"}

def allowed_image(filename: str) -> bool:
    """Verifica si el nombre de archivo tiene una extensión de imagen permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_document(filename: str) -> bool:
    """Verifica si el nombre de archivo tiene una extensión de documento genético permitida."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXTENSIONS