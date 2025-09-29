from dotenv import load_dotenv
load_dotenv()  # Cargar variables de entorno

from flask import render_template, request, session, flash, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from forms.login_form import LoginForm
from flask_login import login_required, current_user, logout_user  # Añadir logout_user
from config import app, db
from modelo.models import Usuario, Finca, Animal, Reporte, ActividadReciente, UsuarioFinca, Potrero, RotacionPotrero, GrupoAnimal  # Agregar RotacionPotrero y GrupoAnimal
from controlador.controlador_actividad import obtener_actividades_recientes  # Importar la función
from datetime import datetime  # Añadir esta importación

# Crear todas las tablas en la base de datos
with app.app_context():
    db.create_all()
    print("Tablas creadas correctamente en la base de datos")

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

# En la ruta del dashboard:
@app.route('/dashboard/dueno')
@login_required
def dashboard_dueno():
    # Obtener el usuario actual
    usuario_actual = Usuario.query.get(current_user.id)
    
    # Contar las fincas del usuario actual
    total_fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).count()
    
    # Contar los animales en las fincas del usuario
    total_animales = Animal.query.join(Finca).join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).count()
    
    # Definir total_produccion (ajusta esto según tu modelo de datos)
    total_produccion = 0  # Inicializar con un valor predeterminado o calcular según tus necesidades
    
    # Definir total_trabajadores (ajusta esto según tu modelo de datos)
    total_trabajadores = 0  # Inicializar con un valor predeterminado o calcular según tus necesidades
    
    # Obtener actividades recientes del usuario
    actividades_recientes = ActividadReciente.query.filter_by(usuario_id=current_user.id).order_by(ActividadReciente.fecha.desc()).limit(5).all()
    
    # Añadir la fecha y hora actual
    now = datetime.now()
    
    return render_template('dueño/dashboard_dueno.html', 
                           total_fincas=total_fincas,
                           total_animales=total_animales,
                           total_produccion=total_produccion,
                           total_trabajadores=total_trabajadores,
                           now=now)

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
            accion="Creación de Finca",  # Usar 'accion' en lugar de 'tipo_actividad'
            elemento=f"Finca: {nueva_finca.nombre_finca}",  # Usar 'elemento' en lugar de 'descripcion'
            fecha=datetime.now(),
            usuario_id=session['usuario_id']  # Usar 'usuario_id' en lugar de 'id_usuario'
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
        return redirect(url_for('dashboard_dueno'))
    
    try:
        # Primero eliminar los grupos de animales asociados a esta finca
        from modelo.models import GrupoAnimal
        grupos = GrupoAnimal.query.filter_by(id_finca=finca_id).all()
        for grupo in grupos:
            db.session.delete(grupo)
        
        # Luego eliminar la finca
        db.session.delete(finca)
        db.session.commit()
        flash(f'Finca {finca.nombre_finca} eliminada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la finca: {str(e)}', 'danger')
    
    return redirect(url_for('mis_fincas'))  # Añadir esta línea

# Después de la ruta mis_fincas

# Importar el formulario de potrero
from forms.potrero_form import PotreroForm

@app.route('/finca/gestionar/<int:finca_id>')
@login_required
def gestionar_finca(finca_id):
    # Verificar que el usuario actual tiene acceso a esta finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
        flash('No tienes permisos para gestionar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    # Obtener la finca
    finca = Finca.query.get_or_404(finca_id)
    
    # Obtener los potreros de la finca (si existen)
    try:
        potreros = Potrero.query.filter_by(id_finca=finca_id).all()
    except Exception as e:
        # Si hay un error al consultar los potreros, mostrar un mensaje y continuar con lista vacía
        flash(f'No se pudieron cargar los potreros: {str(e)}', 'warning')
        potreros = []
    
    # Obtener las rotaciones de potreros de la finca
    rotaciones = []
    try:
        # Obtener IDs de los potreros de esta finca
        potrero_ids = [p.id_potrero for p in potreros]
        if potrero_ids:  # Solo consultar si hay potreros
            # Obtener rotaciones para estos potreros
            rotaciones = RotacionPotrero.query.filter(RotacionPotrero.id_potrero.in_(potrero_ids)).all()
    except Exception as e:
        flash(f'No se pudieron cargar las rotaciones: {str(e)}', 'warning')
    
    return render_template('dueño/gestionarfinca.html', finca=finca, potreros=potreros, rotaciones=rotaciones)

# Ruta para crear un nuevo potrero
@app.route('/finca/<int:finca_id>/potrero/crear', methods=['GET', 'POST'])
@login_required
def crear_potrero(finca_id):
    # Verificar que el usuario actual tiene acceso a esta finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
        flash('No tienes permisos para gestionar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    form = PotreroForm()
    if form.validate_on_submit():
        # Crear un nuevo potrero
        nuevo_potrero = Potrero(
            nombre_potrero=form.nombre_potrero.data,
            id_finca=finca_id,
            extension=form.extension.data,
            capacidad_animal=form.capacidad_animal.data,
            tipo_pasto=form.tipo_pasto.data,
            estado=form.estado.data,
            fecha_ultima_rotacion=form.fecha_ultima_rotacion.data,
            notas=form.notas.data
        )
        
        # Guardar el potrero en la base de datos
        db.session.add(nuevo_potrero)
        db.session.commit()
        
        # Registrar actividad
        nueva_actividad = ActividadReciente(
            usuario_id=current_user.id,
            accion="Creación de Potrero",
            elemento=f"Potrero: {nuevo_potrero.nombre_potrero}",
            fecha=datetime.now()
        )
        db.session.add(nueva_actividad)
        db.session.commit()
        
        flash('Potrero creado exitosamente!', 'success')
        return redirect(url_for('gestionar_finca', finca_id=finca_id))
    
    # Obtener la finca
    finca = Finca.query.get_or_404(finca_id)
    
    return render_template('dueño/crear_potrero.html', form=form, finca=finca)

# Ruta para editar un potrero
@app.route('/potrero/<int:potrero_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_potrero(potrero_id):
    potrero = Potrero.query.get_or_404(potrero_id)
    
    # Verificar que el usuario actual tiene acceso a la finca del potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
        flash('No tienes permisos para editar este potrero', 'danger')
        return redirect(url_for('mis_fincas'))
    
    form = PotreroForm(obj=potrero)
    if form.validate_on_submit():
        # Actualizar los datos del potrero
        potrero.nombre_potrero = form.nombre_potrero.data
        potrero.extension = form.extension.data
        potrero.capacidad_animal = form.capacidad_animal.data
        potrero.tipo_pasto = form.tipo_pasto.data
        potrero.estado = form.estado.data
        potrero.notas = form.notas.data
        
        db.session.commit()
        
        flash('Potrero actualizado exitosamente!', 'success')
        return redirect(url_for('gestionar_finca', finca_id=potrero.id_finca))
    
    return render_template('dueño/editar_potrero.html', form=form, potrero=potrero)

# Ruta para eliminar un potrero
@app.route('/potrero/<int:potrero_id>/eliminar', methods=['POST'])
@login_required
def eliminar_potrero(potrero_id):
    potrero = Potrero.query.get_or_404(potrero_id)
    
    # Verificar que el usuario actual tiene acceso a la finca del potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
        flash('No tienes permisos para eliminar este potrero', 'danger')
        return redirect(url_for('mis_fincas'))
    
    finca_id = potrero.id_finca
    
    try:
        db.session.delete(potrero)
        db.session.commit()
        flash(f'Potrero {potrero.nombre_potrero} eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el potrero: {str(e)}', 'danger')
    
    return redirect(url_for('gestionar_finca', finca_id=finca_id))

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

@app.route('/obtener-fincas-usuario')
@login_required
def obtener_fincas_usuario():
    # Consulta directa para obtener las fincas del usuario actual
    fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    
    # Convertir a formato JSON
    fincas_json = [{
        'id': finca.id_finca,
        'nombre': finca.nombre_finca
    } for finca in fincas]
    
    return jsonify(fincas_json)
    
@app.route('/guardar-potrero', methods=['POST'])
@login_required
def guardar_potrero():
    try:
        # Obtener datos del formulario
        data = request.json
        
        # Validar que todos los campos requeridos estén presentes
        campos_requeridos = ['nombrePotrero', 'fincaPotrero', 'areaPotrero', 'estadoPotrero']
        for campo in campos_requeridos:
            if campo not in data or not data[campo]:
                return jsonify({'success': False, 'message': f'El campo {campo} es requerido'}), 400
        
        # Crear un nuevo potrero
        nuevo_potrero = Potrero(
            nombre_potrero=data['nombrePotrero'],
            id_finca=data['fincaPotrero'],
            extension=data['areaPotrero'],
            capacidad_animal=data['capacidadPotrero'],
            tipo_pasto=data['tipoPasto'],
            estado=data['estadoPotrero'],
            notas=data['notasPotrero']
        )
        
        # Si hay fecha de última rotación
        if data.get('ultimoUso'):
            nuevo_potrero.fecha_ultima_rotacion = datetime.strptime(data['ultimoUso'], '%Y-%m-%d')
        
        # Validar datos
        if not nuevo_potrero.nombre_potrero or len(nuevo_potrero.nombre_potrero) < 2 or len(nuevo_potrero.nombre_potrero) > 50:
            return jsonify({'success': False, 'message': 'El nombre del potrero debe tener entre 2 y 50 caracteres'}), 400
            
        if not nuevo_potrero.extension or nuevo_potrero.extension < 0.1:
            return jsonify({'success': False, 'message': 'La extensión debe ser mayor a 0.1 hectáreas'}), 400
            
        if nuevo_potrero.capacidad_animal is not None and nuevo_potrero.capacidad_animal < 1:
            return jsonify({'success': False, 'message': 'La capacidad debe ser al menos 1 animal'}), 400
            
        if nuevo_potrero.tipo_pasto and len(nuevo_potrero.tipo_pasto) > 50:
            return jsonify({'success': False, 'message': 'El tipo de pasto no debe exceder los 50 caracteres'}), 400
            
        if nuevo_potrero.estado not in ['activo', 'descanso', 'mantenimiento']:
            return jsonify({'success': False, 'message': 'Estado no válido'}), 400
            
        if nuevo_potrero.notas and len(nuevo_potrero.notas) > 500:
            return jsonify({'success': False, 'message': 'Las notas no deben exceder los 500 caracteres'}), 400
        
        # Guardar en la base de datos
        db.session.add(nuevo_potrero)
        db.session.commit()
        
        # Registrar actividad
        nueva_actividad = ActividadReciente(
            usuario_id=current_user.id,
            accion="Creación de Potrero",
            elemento=f"Potrero: {nuevo_potrero.nombre_potrero}",
            fecha=datetime.now()
        )
        db.session.add(nueva_actividad)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Potrero guardado exitosamente', 'id': nuevo_potrero.id_potrero}), 200
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Error de validación al guardar potrero: {str(e)}")
        return jsonify({'success': False, 'message': f'Error de validación: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al guardar potrero: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al guardar el potrero: {str(e)}'}), 500

@app.route('/guardar-rotacion', methods=['POST'])
@login_required
def guardar_rotacion():
    try:
        # Obtener datos del formulario
        data = request.json
        
        # Validar que todos los campos requeridos estén presentes
        campos_requeridos = ['potrero_id', 'grupo_animal_id', 'fecha_inicio', 'tipo_uso']
        for campo in campos_requeridos:
            if campo not in data or not data[campo]:
                return jsonify({'success': False, 'message': f'El campo {campo} es requerido'}), 400
        
        # Verificar que el potrero existe y pertenece a una finca del usuario
        potrero = Potrero.query.get_or_404(data['potrero_id'])
        relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
        if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
            return jsonify({'success': False, 'message': 'No tienes permisos para gestionar este potrero'}), 403
        
        # Verificar que el grupo animal existe y pertenece a la misma finca
        grupo_animal = GrupoAnimal.query.get_or_404(data['grupo_animal_id'])
        if grupo_animal.id_finca != potrero.id_finca:
            return jsonify({'success': False, 'message': 'El grupo animal no pertenece a la misma finca que el potrero'}), 400
        
        # Crear una nueva rotación
        nueva_rotacion = RotacionPotrero(
            id_potrero=data['potrero_id'],
            id_grupo_animal=data['grupo_animal_id'],
            fecha_inicio=datetime.strptime(data['fecha_inicio'], '%Y-%m-%d'),
            tipo_uso=data['tipo_uso'],
            observaciones=data.get('observaciones')
        )
        
        # Si hay fecha de fin
        if data.get('fecha_fin'):
            nueva_rotacion.fecha_fin = datetime.strptime(data['fecha_fin'], '%Y-%m-%d')
        
        # Guardar en la base de datos
        db.session.add(nueva_rotacion)
        
        # Actualizar la fecha de último uso del potrero
        potrero.fecha_ultimo_uso = nueva_rotacion.fecha_inicio
        
        db.session.commit()
        
        # Registrar actividad
        nueva_actividad = ActividadReciente(
            usuario_id=current_user.id,
            accion="Rotación de Potrero",
            elemento=f"Potrero: {potrero.nombre_potrero} - Grupo: {grupo_animal.nombre_grupo}",
            fecha=datetime.now()
        )
        db.session.add(nueva_actividad)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Rotación guardada exitosamente'}), 200
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"Error de validación al guardar rotación: {str(e)}")
        return jsonify({'success': False, 'message': f'Error de validación: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al guardar rotación: {str(e)}")
        return jsonify({'success': False, 'message': f'Error al guardar la rotación: {str(e)}'}), 500

# Eliminada: Ruta /guardar-potrero que procesaba el formulario modal mediante AJAX
@app.route('/finca/<int:finca_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_finca(finca_id):
    # Obtener la finca existente
    finca = Finca.query.get_or_404(finca_id)
    
    # Verificar que el usuario actual es dueño de la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:  # Permitir al admin también
        flash('No tienes permisos para editar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    # Crear el formulario y prellenarlo con los datos existentes
    form = FincaForm(obj=finca)
    
    if form.validate_on_submit():
        # Actualizar los datos de la finca
        form.populate_obj(finca)
        
        try:
            db.session.commit()
            
            # Registrar actividad
            nueva_actividad = ActividadReciente(
                accion="Edición de Finca",
                elemento=f"Finca: {finca.nombre_finca}",
                fecha=datetime.now(),
                usuario_id=current_user.id
            )
            db.session.add(nueva_actividad)
            db.session.commit()
            
            flash('Finca actualizada exitosamente!', 'success')
            return redirect(url_for('mis_fincas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la finca: {str(e)}', 'danger')
    
    return render_template('dueño/editar_finca.html', form=form, finca=finca)

# Aplicar el decorador de rol
editar_finca = requiere_rol(2)(editar_finca)  # Solo accesible para roles 2 (dueño) y 3 (admin)

# Eliminada: Ruta /guardar-potrero que procesaba el formulario modal mediante AJAX
if __name__ == '__main__':
    app.run(debug=True)
    

