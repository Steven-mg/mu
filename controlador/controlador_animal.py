import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from modelo.models import Animal, Raza, Finca, EstadoReproductivo, UsuarioFinca
from forms.animal_form import AnimalForm
from config import db
from datetime import datetime
from controlador.controlador_actividad import registrar_actividad

@login_required
def listar_animales():
    """Listar todos los animales de las fincas del usuario"""
    # Obtener las fincas del usuario actual
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_ids = [f.id_finca for f in fincas_usuario]
    
    # Obtener animales de las fincas del usuario
    if finca_ids:
        animales = Animal.query.filter(Animal.id_finca.in_(finca_ids)).all()
    else:
        animales = []
    
    return render_template('dueño/gestion_animales.html', animales=animales, fincas=fincas_usuario)

@login_required
def crear_animal():
    """Crear un nuevo animal"""
    form = AnimalForm()
    
    # Filtrar fincas del usuario actual
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    form.id_finca.choices = [(0, 'Seleccione una finca')] + [(f.id_finca, f.nombre_finca) for f in fincas_usuario]
    
    if form.validate_on_submit():
        # Crear nuevo animal
        nuevo_animal = Animal(
            nombre_animal=form.nombre_animal.data,
            id_raza=form.id_raza.data if form.id_raza.data != 0 else None,
            fecha_nacimiento=form.fecha_nacimiento.data,
            sexo=form.sexo.data,
            id_finca=form.id_finca.data,
            id_padre=form.id_padre.data if form.id_padre.data != 0 else None,
            id_madre=form.id_madre.data if form.id_madre.data != 0 else None,
            ubicacion_animal=form.ubicacion_animal.data,
            origen=form.origen.data,
            id_estado_reprod=form.id_estado_reprod.data if form.id_estado_reprod.data != 0 else None
        )
        
        try:
            db.session.add(nuevo_animal)
            db.session.commit()
            
            # Registrar actividad
            registrar_actividad("Creó", f"Animal: {nuevo_animal.nombre_animal}")
            
            flash('Animal creado exitosamente!', 'success')
            return redirect(url_for('gestion_animales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el animal: {str(e)}', 'danger')
    
    return render_template('dueño/crear_animal.html', form=form)

@login_required
def editar_animal(animal_id):
    """Editar un animal existente"""
    animal = Animal.query.get_or_404(animal_id)
    
    # Verificar que el usuario tiene acceso a la finca del animal
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para editar este animal', 'danger')
        return redirect(url_for('gestion_animales'))
    
    form = AnimalForm(obj=animal)
    
    # Filtrar fincas del usuario actual
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    form.id_finca.choices = [(0, 'Seleccione una finca')] + [(f.id_finca, f.nombre_finca) for f in fincas_usuario]
    
    if form.validate_on_submit():
        # Actualizar datos del animal
        animal.nombre_animal = form.nombre_animal.data
        animal.id_raza = form.id_raza.data if form.id_raza.data != 0 else None
        animal.fecha_nacimiento = form.fecha_nacimiento.data
        animal.sexo = form.sexo.data
        animal.id_finca = form.id_finca.data
        animal.id_padre = form.id_padre.data if form.id_padre.data != 0 else None
        animal.id_madre = form.id_madre.data if form.id_madre.data != 0 else None
        animal.ubicacion_animal = form.ubicacion_animal.data
        animal.origen = form.origen.data
        animal.id_estado_reprod = form.id_estado_reprod.data if form.id_estado_reprod.data != 0 else None
        
        try:
            db.session.commit()
            
            # Registrar actividad
            registrar_actividad("Editó", f"Animal: {animal.nombre_animal}")
            
            flash('Animal actualizado exitosamente!', 'success')
            return redirect(url_for('gestion_animales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el animal: {str(e)}', 'danger')
    
    return render_template('dueño/editar_animal.html', form=form, animal=animal)

@login_required
def eliminar_animal(animal_id):
    """Eliminar un animal"""
    animal = Animal.query.get_or_404(animal_id)
    
    # Verificar que el usuario tiene acceso a la finca del animal
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para eliminar este animal', 'danger')
        return redirect(url_for('gestion_animales'))
    
    nombre_animal = animal.nombre_animal
    
    try:
        db.session.delete(animal)
        db.session.commit()
        
        # Registrar actividad
        registrar_actividad("Eliminó", f"Animal: {nombre_animal}")
        
        flash(f'Animal {nombre_animal} eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el animal: {str(e)}', 'danger')
    
    return redirect(url_for('gestion_animales'))

@login_required
def ver_animal(animal_id):
    """Ver detalles de un animal"""
    animal = Animal.query.get_or_404(animal_id)
    
    # Verificar que el usuario tiene acceso a la finca del animal
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este animal', 'danger')
        return redirect(url_for('gestion_animales'))
    
    return render_template('dueño/ver_animal.html', animal=animal)

@login_required
def obtener_animales_por_finca(finca_id):
    """API endpoint para obtener animales de una finca específica"""
    # Verificar que el usuario tiene acceso a la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'error': 'No tienes permisos para acceder a esta finca'}), 403
    
    animales = Animal.query.filter_by(id_finca=finca_id).all()
    animales_json = [{
        'id': animal.id_animal,
        'nombre': animal.nombre_animal,
        'sexo': animal.sexo,
        'raza': animal.raza.nombre_raza if animal.raza else 'Sin raza',
        'fecha_nacimiento': animal.fecha_nacimiento.strftime('%Y-%m-%d') if animal.fecha_nacimiento else None,
        'ubicacion': animal.ubicacion_animal
    } for animal in animales]
    
    return jsonify(animales_json)

@login_required
def obtener_animales_por_sexo(sexo):
    """API endpoint para obtener animales por sexo (para padre/madre)"""
    # Obtener las fincas del usuario actual
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_ids = [f.id_finca for f in fincas_usuario]
    
    if finca_ids:
        animales = Animal.query.filter(Animal.id_finca.in_(finca_ids), Animal.sexo == sexo).all()
    else:
        animales = []
    
    animales_json = [{
        'id': animal.id_animal,
        'nombre': animal.nombre_animal,
        'finca': animal.finca.nombre_finca if animal.finca else 'Sin finca'
    } for animal in animales]
    
    return jsonify(animales_json)