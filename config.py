from flask import Flask
from flask import g
import time
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect  # Añadir esta importación
import os
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
from cachelib import SimpleCache

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

# Cacheo básico de estáticos (ajustable por entorno)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = int(os.getenv('STATIC_MAX_AGE', '86400'))  # 1 día
app.config['USE_X_SENDFILE'] = False

"""
Configuración de la base de datos (MySQL)
- No se modifica .env; se respeta DATABASE_URI existente
- Se agrega configuración de pool para reconexión y timeouts, ayudando a mitigar
  errores como WinError 10053 / conexiones abortadas.
"""
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI',
    'mysql+pymysql://usuario:contraseña@localhost/nombre_base_datos'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Opciones del engine para conexiones más resilientes en MySQL
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,     # verifica conexiones antes de usarlas
    'pool_recycle': 280,       # recicla conexiones para evitar cierre por servidor
    'pool_timeout': 60,        # tiempo de espera al obtener conexión del pool
    'connect_args': {
        'charset': 'utf8mb4',
        'connect_timeout': 20,
        'read_timeout': 60,
        'write_timeout': 60,
    },
}

# Log seguro del destino de la BD (sin credenciales)
try:
    _uri = app.config['SQLALCHEMY_DATABASE_URI']
    _url = make_url(_uri)
    print(
        f"Usando BD -> driver={_url.drivername}, host={_url.host}, port={_url.port}, database={_url.database}"
    )
except Exception:
    pass

# Configuración de Google OAuth
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Caché en memoria para respuestas rápidas de consultas frecuentes
cache = SimpleCache(default_timeout=60)

def cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        return None

def cache_set(key, value, timeout=None):
    try:
        cache.set(key, value, timeout or 60)
    except Exception:
        pass

def cache_cached(key, producer, timeout=None):
    val = cache_get(key)
    if val is not None:
        return val
    val = producer()
    cache_set(key, val, timeout or 60)
    return val

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

# Añadir encabezados de caché seguros para respuestas HTML y estáticos
def add_server_timing_header(response):
    try:
        total_ms = (time.perf_counter() - getattr(g, 'request_start', time.perf_counter())) * 1000.0
        parts = getattr(g, 'server_timing', [])[:]
        parts.insert(0, f"app;dur={total_ms:.1f}")
        response.headers['Server-Timing'] = ', '.join(parts)
    except Exception:
        pass
    return response

def add_cache_headers(response):
    ctype = response.headers.get('Content-Type', '')
    # No cachear páginas HTML autenticadas; cachear estáticos y JSON ligeros
    if 'text/html' in ctype:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    elif any(x in ctype for x in ['text/css', 'application/javascript', 'image/', 'font/', 'application/font']):
        # permitir cache del navegador para assets
        response.headers.setdefault('Cache-Control', f'public, max-age={app.config.get("SEND_FILE_MAX_AGE_DEFAULT", 86400)}')
    return response

@app.before_request
def _server_timing_begin():
    try:
        g.request_start = time.perf_counter()
        g.server_timing = []
    except Exception:
        pass

@app.after_request
def _apply_headers(response):
    response = add_server_timing_header(response)
    response = add_cache_headers(response)
    return response

def add_server_timing(name: str, dur_ms: float):
    try:
        if not hasattr(g, 'server_timing'):
            g.server_timing = []
        g.server_timing.append(f"{name};dur={dur_ms:.1f}")
    except Exception:
        pass

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

# Filtro Jinja para formatear moneda en estilo es-CO (puntos miles, coma decimal)
@app.template_filter('currency_es')
def currency_es(value):
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            value = float(value)
        else:
            value = float(value)
    except Exception:
        return value
    s = f"{value:,.2f}"
    # Cambiar separadores: ',' miles -> '.'; '.' decimales -> ','
    return s.replace(',', '_').replace('.', ',').replace('_', '.')