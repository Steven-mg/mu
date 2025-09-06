from dotenv import load_dotenv
load_dotenv()  # Cargar variables de entorno

from flask import render_template, request, session, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from forms.login_form import LoginForm
from flask_login import login_required, current_user, logout_user  # Añadir logout_user
from config import app, db
from modelo.models import Usuario, Finca, Animal, Reporte, ActividadReciente, UsuarioFinca  # Agregar UsuarioFinca aquí
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
@login_required
def dashboard_dueno():
    # Obtener el usuario actual
    usuario_actual = Usuario.query.get(current_user.id)
    
    # Contar las fincas del usuario actual
    # Contar las fincas del usuario actual
    total_fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).count()
    
    # Contar los animales en las fincas del usuario
    total_animales = Animal.query.join(Finca).join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).count()
    
    # Obtener actividades recientes del usuario
    actividades_recientes = ActividadReciente.query.filter_by(usuario_id=current_user.id).order_by(ActividadReciente.fecha.desc()).limit(5).all()
    
    return render_template('dueño/dashboard_dueno.html', 
                      total_fincas=total_fincas,
                      total_animales=total_animales,
                      actividades_recientes=actividades_recientes)

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

# Ruta para eliminar un usuario (solo accesible para el administrador root)
@app.route('/admin/eliminar-usuario/<int:usuario_id>', methods=['POST'])
@login_required
def eliminar_usuario(usuario_id):
    # Verificar que el usuario actual es administrador (tipo_usuario = 3)
    if current_user.tipo_usuario != 3:
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # No permitir eliminar al superadmin
    if usuario.tipo_usuario == 3:
        flash('No se puede eliminar al administrador del sistema', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario {usuario.nik_name} eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

# Ruta para que un usuario elimine su propia cuenta
@app.route('/mi-cuenta/eliminar', methods=['POST'])
@login_required
def eliminar_mi_cuenta():
    try:
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        flash('Tu cuenta ha sido eliminada correctamente', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar tu cuenta: {str(e)}', 'danger')
        return redirect(url_for('mi_cuenta'))

# Ruta para eliminar una finca (solo accesible para el dueño de la finca)
@app.route('/finca/<int:finca_id>/eliminar', methods=['POST'])
@login_required
def eliminar_finca(finca_id):
    finca = Finca.query.get_or_404(finca_id)
    
    # Verificar que el usuario actual es dueño de la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
        flash('No tienes permisos para eliminar esta finca', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(finca)
        db.session.commit()
        flash(f'Finca {finca.nombre_finca} eliminada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la finca: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/mis-fincas')
@login_required
def mis_fincas():
    # Obtener las fincas del usuario actual
    usuario_actual = Usuario.query.get(current_user.id)
    
    # Consulta directa para obtener las fincas del usuario
    fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    
    # Depuración
    print(f"Usuario ID: {current_user.id}, Nombre: {current_user.nik_name}")
    print(f"Número de fincas encontradas: {len(fincas)}")
    for finca in fincas:
        print(f"Finca ID: {finca.id_finca}, Nombre: {finca.nombre_finca}")
    
    return render_template('dueño/mis_fincas.html', fincas=fincas)

if __name__ == '__main__':
    app.run(debug=True)
    

