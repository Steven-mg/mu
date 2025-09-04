import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template, redirect, url_for, flash, session, request
from forms.login_form import LoginForm
from modelo.models import Usuario
import bcrypt  # Importar bcrypt
from config import db, app  # Importar app desde config
from flask_dance.contrib.google import make_google_blueprint, google
from flask_login import login_user, current_user, logout_user, login_required
from controlador.controlador_actividad import registrar_actividad  # Importar la función

# Configuración del blueprint de Google OAuth
def configurar_google_oauth(app):
    blueprint = make_google_blueprint(
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        scope=['profile', 'email'],
        redirect_url='http://127.0.0.1:5000/login/google/authorized',
        # Usar offline=True para solicitar acceso offline
        offline=True
    )
    app.register_blueprint(blueprint, url_prefix='/login')
    return blueprint

# Función para manejar el login con Google
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    
    resp = google.get('/oauth2/v2/userinfo')
    if resp.ok:
        google_info = resp.json()
        email = google_info['email']
        
        # Buscar si el usuario ya existe
        usuario = Usuario.query.filter_by(correo=email).first()
        
        if not usuario:
            # En la función google_login (línea 35-40)
            # Crear nuevo usuario
            nik_name = email.split('@')[0]  # Usar parte del email como nik_name
            # Verificar si el nik_name ya existe
            usuario_existente = Usuario.query.filter_by(nik_name=nik_name).first()
            if usuario_existente:
                # Añadir un número al final si ya existe
                import random
                nik_name = f"{nik_name}{random.randint(1, 9999)}"
                
            usuario = Usuario(
                nik_name=nik_name,
                correo=email,
                contraseña=None,  # No se necesita contraseña para OAuth
                tipo_usuario=2,  # Nivel 2: Dueño de finca por defecto
                direccion=None,
                telefono=None,
                pais=None,
                departamento=None,
                ciudad=None
            )
            db.session.add(usuario)
            db.session.commit()
        
        # Iniciar sesión
        session['usuario_id'] = usuario.id
        session['tipo_usuario'] = usuario.tipo_usuario
        session['nombre_usuario'] = usuario.nombre_usuario
        
        flash('Has iniciado sesión con Google correctamente', 'success')
        
        # Redireccionar según el tipo de usuario
        if usuario.tipo_usuario == 3:  # Root/Super admin
            return redirect(url_for('dashboard_root'))
        elif usuario.tipo_usuario == 2:  # Dueño de finca
            return redirect(url_for('dashboard_dueno'))
        elif usuario.tipo_usuario == 1:  # Veterinario/Trabajador
            return redirect(url_for('dashboard_trabajador'))
    
    flash('Error al iniciar sesión con Google', 'error')
    return redirect(url_for('login'))

# Función para manejar la ruta de inicio de sesión
def ruta_login():
    # Si el usuario ya está autenticado, redirigir según su rol
    if 'usuario_id' in session:
        if session['tipo_usuario'] == 3:  # Root/Super admin
            return redirect(url_for('dashboard_root'))
        elif session['tipo_usuario'] == 2:  # Dueño de finca
            return redirect(url_for('dashboard_dueno'))
        elif session['tipo_usuario'] == 1:  # Veterinario/Trabajador
            return redirect(url_for('dashboard_trabajador'))
    
    form = LoginForm()
    # En la función ruta_login()
    if form.validate_on_submit():
        # Buscar usuario en la base de datos por nik_name o correo
        usuario = Usuario.query.filter_by(nik_name=form.nik_name.data).first()
        
        # Si no se encuentra por nik_name, buscar por correo
        if not usuario:
            usuario = Usuario.query.filter_by(correo=form.nik_name.data).first()
        
        # Verificar si el usuario existe y la contraseña es correcta
        if usuario and usuario.contraseña and bcrypt.checkpw(form.contraseña.data.encode('utf-8'), usuario.contraseña.encode('utf-8')):
            # Guardar información del usuario en la sesión
            # En la función google_login
            # Iniciar sesión
            session['usuario_id'] = usuario.id
            session['tipo_usuario'] = usuario.tipo_usuario
            session['nik_name'] = usuario.nik_name  # Cambiar nombre_usuario por nik_name
            
            flash('Has iniciado sesión correctamente', 'success')
            
            # Redireccionar según el tipo de usuario
            if usuario.tipo_usuario == 3:  # Root/Super admin
                return redirect(url_for('dashboard_root'))
            elif usuario.tipo_usuario == 2:  # Dueño de finca
                return redirect(url_for('dashboard_dueno'))
            elif usuario.tipo_usuario == 1:  # Veterinario/Trabajador
                return redirect(url_for('dashboard_trabajador'))
        else:
            flash('Error al iniciar sesión. Verifica tu nombre de usuario/correo y contraseña', 'danger')
    
    return render_template('login.html', form=form)

# Función para manejar la ruta de cierre de sesión
def ruta_logout():
    # Eliminar datos de la sesión
    session.pop('usuario_id', None)
    session.pop('tipo_usuario', None)
    session.pop('nombre_usuario', None)
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('pagina_inicio'))

# Función auxiliar para verificar roles
def requiere_rol(rol_minimo):
    def decorador(f):
        def funcion_decorada(*args, **kwargs):
            # Verificar si el usuario está en sesión
            if 'usuario_id' not in session:
                flash('Debes iniciar sesión para acceder', 'error')
                return redirect(url_for('login'))
            
            # Verificar si el usuario tiene el rol requerido
            if session['tipo_usuario'] < rol_minimo:
                flash('No tienes permisos para acceder a esta página', 'error')
                return redirect(url_for('pagina_inicio'))
                
            return f(*args, **kwargs)
        
        # Preservar el nombre y los atributos de la función original
        funcion_decorada.__name__ = f.__name__
        funcion_decorada.__module__ = f.__module__
        funcion_decorada.__doc__ = f.__doc__
        
        return funcion_decorada
    return decorador

# Agregar al inicio del archivo, en las importaciones
from forms.registro_form import RegistroForm

# Agregar esta nueva función al archivo
def ruta_registro():
    form = RegistroForm()
    if form.validate_on_submit():
        # Crear hash de la contraseña solo si se proporciona
        hashed_password = None
        if form.contraseña.data:
            hashed_password = bcrypt.hashpw(form.contraseña.data.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nik_name=form.nik_name.data,
            nombres=form.nombres.data if form.nombres.data else None,
            apellidos=form.apellidos.data if form.apellidos.data else None,
            correo=form.correo.data,
            contraseña=hashed_password,  # Puede ser None
            tipo_usuario=2,  # Nivel 2: Dueño de finca
            direccion=form.direccion.data if form.direccion.data else None,
            telefono=form.telefono.data if form.telefono.data else None,
            pais=form.pais.data if form.pais.data else None,
            departamento=form.departamento.data if form.departamento.data else None,
            ciudad=form.ciudad.data if form.ciudad.data else None
        )
        
        # Guardar en la base de datos
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        # Registrar actividad de registro
        registrar_actividad("Registró", f"Usuario: {nuevo_usuario.nik_name}")
        flash('¡Registro exitoso! Ahora puedes iniciar sesión', 'success')
        return redirect(url_for('login'))
    
    return render_template('registro.html', form=form)