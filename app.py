from dotenv import load_dotenv
load_dotenv()  # Cargar variables de entorno

from flask import render_template, request, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from forms.login_form import LoginForm
from config import app, db
from modelo.models import Usuario, Finca, Animal, Reporte, ActividadReciente  # Agregar ActividadReciente aquí
from controlador.controlador_actividad import obtener_actividades_recientes  # Importar la función
from datetime import datetime  # Añadir esta importación

# Importar las funciones después de definir las rutas para evitar la importación circular
@app.route('/')
def pagina_inicio():
    return render_template('pages/inicio.html')

# Definir las rutas primero
@app.route('/dashboard/root')
def dashboard_root():
    # Obtener estadísticas desde la base de datos
    total_usuarios = Usuario.query.count()
    total_fincas = Finca.query.count()
    total_ganado = Animal.query.count()
    total_reportes = Reporte.query.count()
    
    # Obtener actividades recientes
    actividades_recientes = obtener_actividades_recientes(5)  # Obtener las 5 actividades más recientes
    
    return render_template('root/dashboard_root.html', 
                          total_usuarios=total_usuarios,
                          total_fincas=total_fincas,
                          total_ganado=total_ganado,
                          total_reportes=total_reportes,
                          actividades_recientes=actividades_recientes)  # Pasar actividades a la plantilla

@app.route('/dashboard/dueno')
def dashboard_dueno():
    return render_template('dueño/dashboard_dueno.html')

@app.route('/dashboard/trabajador')
def dashboard_trabajador():
    return render_template('trabajador-veternario/dashboard_trabajador.html')

# Ahora importar las funciones de autenticación
# Agregar después de la importación de controlador_autenticacion
from controlador.controlador_autenticacion import ruta_login, ruta_logout, requiere_rol, ruta_registro, configurar_google_oauth, google_login

# Configurar Google OAuth
google_blueprint = configurar_google_oauth(app)

# Agregar la ruta de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    return ruta_registro()

# Y aplicar los decoradores después de importar
@app.route('/login', methods=['GET', 'POST'])
def login():
    return ruta_login()

@app.route('/logout')
def logout():
    return ruta_logout()

# Añadir ruta para el login con Google
@app.route('/login/google')
def login_google():
    return google_login()

# Importar el formulario de finca
from forms.finca_form import FincaForm

@app.route('/finca/crear', methods=['GET', 'POST'])
def crear_finca():
    form = FincaForm()
    if form.validate_on_submit():
        # Crear una nueva finca
        nueva_finca = Finca(
            nombre_finca=form.nombre_finca.data,
            localizacion=form.localizacion.data,
            correo=form.correo.data,
            telefono=form.telefono.data,
            nombreEncargado=form.nombreEncargado.data,
            pais=form.pais.data,
            departamento=form.departamento.data,
            ciudad=form.ciudad.data
        )
        
        # Guardar la finca en la base de datos
        db.session.add(nueva_finca)
        
        # Asociar la finca al usuario actual
        usuario_actual = Usuario.query.get(session['usuario_id'])
        usuario_actual.fincas.append(nueva_finca)
        
        db.session.commit()
        
        # Registrar actividad
        nueva_actividad = ActividadReciente(
            tipo_actividad="Creación de Finca",
            descripcion=f"Se creó la finca {nueva_finca.nombre_finca}",
            fecha=datetime.now(),
            id_usuario=session['usuario_id']
        )
        db.session.add(nueva_actividad)
        db.session.commit()
        
        flash('Finca creada exitosamente!', 'success')
        return redirect(url_for('dashboard_dueno'))
    
    return render_template('dueño/crear_finca.html', form=form)

# Aplicar el decorador de rol a la nueva ruta
crear_finca = requiere_rol(2)(crear_finca)  # Solo accesible para roles 2 (dueño) y 3 (admin)

# Aplicar los decoradores de rol a las rutas ya definidas
dashboard_root = requiere_rol(3)(dashboard_root)  # Solo accesible para rol 3 (root)
dashboard_dueno = requiere_rol(2)(dashboard_dueno)  # Accesible para roles 2 y 3
dashboard_trabajador = requiere_rol(1)(dashboard_trabajador)  # Accesible para roles 1, 2 y 3

if __name__ == '__main__':
    app.run(debug=True)
    

