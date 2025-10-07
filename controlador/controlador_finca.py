import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from modelo.models import Finca, UsuarioFinca, Potrero, RotacionPotrero, GrupoAnimal
from forms.finca_form import FincaForm
from forms.potrero_form import PotreroForm
from config import db
from datetime import datetime
from controlador.controlador_actividad import registrar_actividad

@login_required
def crear_finca():
    """Crear una nueva finca"""
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
        
        try:
            # Guardar la finca en la base de datos
            db.session.add(nueva_finca)
            db.session.flush()  # Para obtener el ID de la finca
            
            # Crear la relación usuario-finca explícitamente
            relacion_usuario_finca = UsuarioFinca(
                usuario_id=current_user.id,
                finca_id=nueva_finca.id_finca
            )
            db.session.add(relacion_usuario_finca)
            
            # Registrar actividad
            registrar_actividad(
                accion="Creó",
                elemento=f"Finca: {nueva_finca.nombre_finca}"
            )
            
            db.session.commit()
            flash('Finca creada exitosamente!', 'success')
            return redirect(url_for('gestionar_finca_route', finca_id=nueva_finca.id_finca))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la finca: {str(e)}', 'danger')
    
    return render_template('dueño/crear_finca.html', form=form)

@login_required
def editar_finca(finca_id):
    """Editar una finca existente"""
    # Obtener la finca existente
    finca = Finca.query.get_or_404(finca_id)
    
    # Verificar que el usuario actual es dueño de la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para editar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    # Crear formulario con datos existentes
    form = FincaForm(obj=finca)
    
    if form.validate_on_submit():
        try:
            # Actualizar los datos de la finca
            form.populate_obj(finca)
            
            # Registrar actividad
            registrar_actividad(
                accion="Editó",
                elemento=f"Finca: {finca.nombre_finca}"
            )
            
            db.session.commit()
            flash('Finca actualizada exitosamente!', 'success')
            return redirect(url_for('mis_fincas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la finca: {str(e)}', 'danger')
    
    return render_template('dueño/editar_finca.html', form=form, finca=finca)

@login_required
def eliminar_finca(finca_id):
    """Eliminar una finca"""
    finca = Finca.query.get_or_404(finca_id)
    
    # Verificar que el usuario actual es dueño de la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para eliminar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    nombre_finca = finca.nombre_finca
    
    try:
        # Primero eliminar los grupos de animales asociados a esta finca
        grupos = GrupoAnimal.query.filter_by(id_finca=finca_id).all()
        for grupo in grupos:
            db.session.delete(grupo)
        
        # Luego eliminar la finca (CASCADE se encarga del resto)
        db.session.delete(finca)
        
        # Registrar actividad
        registrar_actividad(
            accion="Eliminó",
            elemento=f"Finca: {nombre_finca}"
        )
        
        db.session.commit()
        flash(f'Finca {nombre_finca} eliminada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la finca: {str(e)}', 'danger')
    
    return redirect(url_for('mis_fincas'))

@login_required
def listar_fincas():
    """Listar todas las fincas del usuario"""
    # Obtener las fincas del usuario actual
    fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    
    # Debug info
    print(f"Usuario actual: {current_user.id}")
    print(f"Número de fincas encontradas: {len(fincas)}")
    for finca in fincas:
        print(f"Finca ID: {finca.id_finca}, Nombre: {finca.nombre_finca}")
    
    return render_template('dueño/mis_fincas.html', fincas=fincas)

@login_required
def gestionar_finca(finca_id):
    """Gestionar una finca específica (potreros, rotaciones, etc.)"""
    # Verificar que el usuario actual tiene acceso a esta finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para gestionar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    # Obtener la finca
    finca = Finca.query.get_or_404(finca_id)
    
    # Obtener los potreros de la finca (si existen)
    potreros = Potrero.query.filter_by(id_finca=finca_id).all()
    
    # Obtener las rotaciones de potreros de la finca
    # Obtener IDs de los potreros de esta finca
    potrero_ids = [p.id_potrero for p in potreros]
    
    if potrero_ids:
        rotaciones = RotacionPotrero.query.filter(RotacionPotrero.id_potrero.in_(potrero_ids)).all()
    else:
        rotaciones = []
    
    return render_template('dueño/gestionarfinca.html', finca=finca, potreros=potreros, rotaciones=rotaciones)

@login_required
def obtener_fincas_usuario():
    """API endpoint para obtener las fincas del usuario actual"""
    # Consulta directa para obtener las fincas del usuario actual
    fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    
    # Convertir a JSON
    fincas_json = [{
        'id': finca.id_finca,
        'nombre': finca.nombre_finca
    } for finca in fincas]
    
    return jsonify(fincas_json)

@login_required
def ver_finca(finca_id):
    """Ver detalles de una finca específica"""
    # Verificar que el usuario actual tiene acceso a esta finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    # Obtener la finca
    finca = Finca.query.get_or_404(finca_id)
    
    # Obtener estadísticas de la finca
    total_potreros = Potrero.query.filter_by(id_finca=finca_id).count()
    total_animales = len([animal for animal in finca.animales])
    
    return render_template('dueño/ver_finca.html', 
                         finca=finca, 
                         total_potreros=total_potreros, 
                         total_animales=total_animales)

@login_required
def crear_potrero(finca_id):
    """Crear un nuevo potrero para una finca específica"""
    # Verificar que el usuario actual tiene acceso a esta finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para crear potreros en esta finca', 'danger')
        return redirect(url_for('mis_fincas'))
    
    # Obtener la finca
    finca = Finca.query.get_or_404(finca_id)
    
    form = PotreroForm()
    
    if form.validate_on_submit():
        try:
            # Crear nuevo potrero
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
            
            db.session.add(nuevo_potrero)
            db.session.commit()
            
            # Registrar actividad
            registrar_actividad("Creó", f"Potrero: {nuevo_potrero.nombre_potrero}")
            
            flash(f'Potrero "{nuevo_potrero.nombre_potrero}" creado exitosamente', 'success')
            return redirect(url_for('gestionar_finca_route', finca_id=finca_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el potrero: {str(e)}', 'danger')
    
    return render_template('dueño/crear_potrero.html', form=form, finca=finca)

@login_required
def editar_potrero(potrero_id):
    """Editar un potrero existente"""
    potrero = Potrero.query.get_or_404(potrero_id)
    
    # Verificar que el usuario actual tiene acceso a la finca de este potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para editar este potrero', 'danger')
        return redirect(url_for('mis_fincas'))
    
    form = PotreroForm(obj=potrero)
    
    if form.validate_on_submit():
        try:
            # Actualizar potrero
            form.populate_obj(potrero)
            potrero.fecha_modificacion = datetime.now()
            
            db.session.commit()
            
            # Registrar actividad
            registrar_actividad("Editó", f"Potrero: {potrero.nombre_potrero}")
            
            flash(f'Potrero "{potrero.nombre_potrero}" actualizado exitosamente', 'success')
            return redirect(url_for('gestionar_finca_route', finca_id=potrero.id_finca))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el potrero: {str(e)}', 'danger')
    
    return render_template('dueño/editar_potrero.html', form=form, potrero=potrero)

@login_required
def eliminar_potrero(potrero_id):
    """Eliminar un potrero existente"""
    potrero = Potrero.query.get_or_404(potrero_id)
    
    # Verificar que el usuario actual tiene acceso a la finca de este potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para eliminar este potrero', 'danger')
        return redirect(url_for('mis_fincas'))
    
    try:
        finca_id = potrero.id_finca
        nombre_potrero = potrero.nombre_potrero
        
        # Eliminar potrero
        db.session.delete(potrero)
        db.session.commit()
        
        # Registrar actividad
        registrar_actividad("Eliminó", f"Potrero: {nombre_potrero}")
        
        flash(f'Potrero "{nombre_potrero}" eliminado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el potrero: {str(e)}', 'danger')
    
    return redirect(url_for('gestionar_finca_route', finca_id=finca_id))