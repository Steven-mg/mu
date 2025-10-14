import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from modelo.models import Usuario, Trabajador
from config import db
from werkzeug.security import generate_password_hash
from controlador.controlador_actividad import registrar_actividad

@login_required
def listar_usuarios():
    """Listar todos los usuarios del sistema (solo para admin)"""
    if current_user.tipo_usuario != 3:
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('dashboard_root'))
    
    usuarios = Usuario.query.all()
    
    # Contar usuarios por tipo
    total_usuarios = len(usuarios)
    usuarios_admin = len([u for u in usuarios if u.tipo_usuario == 3])
    usuarios_dueno = len([u for u in usuarios if u.tipo_usuario == 2])
    usuarios_trabajador = len([u for u in usuarios if u.tipo_usuario == 1])
    
    estadisticas = {
        'total': total_usuarios,
        'admin': usuarios_admin,
        'dueno': usuarios_dueno,
        'trabajador': usuarios_trabajador
    }
    
    return render_template('root/gestion_usuarios.html', usuarios=usuarios, estadisticas=estadisticas)

@login_required
def crear_usuario():
    """Crear un nuevo usuario (solo para admin)"""
    if current_user.tipo_usuario != 3:
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('dashboard_root'))
    
    if request.method == 'POST':
        # Obtener datos del formulario
        nik_name = request.form.get('nik_name')
        nombres = request.form.get('nombres')
        apellidos = request.form.get('apellidos')
        correo = request.form.get('correo')
        contraseña = request.form.get('contraseña')
        tipo_usuario = int(request.form.get('tipo_usuario'))
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        pais = request.form.get('pais')
        departamento = request.form.get('departamento')
        ciudad = request.form.get('ciudad')
        
        # Validar que no exista el usuario
        usuario_existente = Usuario.query.filter(
            (Usuario.nik_name == nik_name) | (Usuario.correo == correo)
        ).first()
        
        if usuario_existente:
            flash('Ya existe un usuario con ese nombre de usuario o correo', 'danger')
            return render_template('root/crear_usuario.html')
        
        # Crear hash de la contraseña solo si no está vacía
        if contraseña and contraseña.strip():
            hashed_password = generate_password_hash(contraseña)
        else:
            flash('La contraseña es requerida', 'danger')
            return render_template('root/crear_usuario.html')
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            nik_name=nik_name,
            nombres=nombres,
            apellidos=apellidos,
            correo=correo,
            contraseña=hashed_password,
            tipo_usuario=tipo_usuario,
            direccion=direccion,
            telefono=telefono,
            pais=pais,
            departamento=departamento,
            ciudad=ciudad
        )
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            # Registrar actividad
            registrar_actividad("Creó", f"Usuario: {nuevo_usuario.nik_name}")
            
            flash('Usuario creado exitosamente!', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el usuario: {str(e)}', 'danger')
    
    return render_template('root/crear_usuario.html')

@login_required
def editar_usuario(usuario_id):
    """Editar un usuario existente (solo para admin)"""
    if current_user.tipo_usuario != 3:
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('dashboard_root'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    if request.method == 'POST':
        print(f"DEBUG: Procesando POST para usuario {usuario_id}")
        print(f"DEBUG: Datos del formulario: {request.form}")
        
        # Validar que los campos requeridos estén presentes
        if not request.form.get('nik_name') or not request.form.get('correo'):
            flash('Los campos Nombre de Usuario y Correo Electrónico son obligatorios', 'danger')
            return render_template('root/editar_usuario.html', usuario=usuario)
        
        # Validar tipo_usuario
        tipo_usuario_str = request.form.get('tipo_usuario')
        if not tipo_usuario_str:
            flash('Debe seleccionar un tipo de usuario', 'danger')
            return render_template('root/editar_usuario.html', usuario=usuario)
        
        try:
            tipo_usuario = int(tipo_usuario_str)
        except ValueError:
            flash('Tipo de usuario inválido', 'danger')
            return render_template('root/editar_usuario.html', usuario=usuario)
        
        # Obtener datos del formulario
        usuario.nik_name = request.form.get('nik_name')
        usuario.nombres = request.form.get('nombres')
        usuario.apellidos = request.form.get('apellidos')
        usuario.correo = request.form.get('correo')
        usuario.tipo_usuario = tipo_usuario
        usuario.direccion = request.form.get('direccion')
        usuario.telefono = request.form.get('telefono')
        usuario.pais = request.form.get('pais')
        usuario.departamento = request.form.get('departamento')
        usuario.ciudad = request.form.get('ciudad')
        
        # Si se proporciona nueva contraseña, actualizarla
        nueva_contraseña = request.form.get('contraseña')
        if nueva_contraseña and nueva_contraseña.strip():
            usuario.contraseña = generate_password_hash(nueva_contraseña)
        
        try:
            db.session.commit()
            print(f"DEBUG: Usuario actualizado exitosamente, redirigiendo...")
            
            # Registrar actividad
            registrar_actividad("Editó", f"Usuario: {usuario.nik_name}")
            
            flash('Usuario actualizado exitosamente!', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            print(f"DEBUG: Error al actualizar usuario: {str(e)}")
            db.session.rollback()
            flash(f'Error al actualizar el usuario: {str(e)}', 'danger')
    
    return render_template('root/editar_usuario.html', usuario=usuario)

@login_required
def eliminar_usuario_controlador(usuario_id):
    """Eliminar un usuario (solo para admin)"""
    if current_user.tipo_usuario != 3:
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('dashboard_root'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # No permitir eliminar al superadmin
    if usuario.tipo_usuario == 3:
        flash('No se puede eliminar al administrador del sistema', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    nombre_usuario = usuario.nik_name
    
    try:
        # Si es un trabajador/veterinario, limpiar tabla legacy 'trabajador' basada en nickname
        if usuario.tipo_usuario == 1:
            try:
                Trabajador.query.filter_by(usuario=usuario.nik_name).delete()
            except Exception:
                pass
        db.session.delete(usuario)
        db.session.commit()
        
        # Registrar actividad
        registrar_actividad("Eliminó", f"Usuario: {nombre_usuario}")
        
        flash(f'Usuario {nombre_usuario} eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))