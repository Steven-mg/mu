from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from modelo.models import db, Animal, Raza, Finca, EstadoReproductivo, UsuarioFinca, CompraAnimales, Potrero
from sqlalchemy.orm import joinedload
from forms.animal_form import AnimalForm, FiltroAnimalForm
from config import registrar_actividad
from datetime import datetime

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
    
    # Verificar si el animal es inmaduro según su edad y la madurez sexual de su raza
    if request.method == 'POST' and form.id_raza.data and form.fecha_nacimiento.data and form.sexo.data:
        raza = Raza.query.get(form.id_raza.data)
        if raza:
            # Calcular la edad en meses
            hoy = datetime.now()
            fecha_nac = form.fecha_nacimiento.data
            edad_meses = (hoy.year - fecha_nac.year) * 12 + (hoy.month - fecha_nac.month)
            
            # Verificar si es inmaduro según el sexo
            es_inmaduro = False
            if form.sexo.data == 'Macho' and raza.madurez_sexual_machos_meses and edad_meses < raza.madurez_sexual_machos_meses:
                es_inmaduro = True
            elif form.sexo.data == 'Hembra' and raza.madurez_sexual_hembras_meses and edad_meses < raza.madurez_sexual_hembras_meses:
                es_inmaduro = True
            
            # Si es inmaduro, forzar la selección de estado "Inmaduro" (ID 15)
            if es_inmaduro:
                # Modificar las opciones del formulario para solo permitir "Inmaduro"
                estado_inmaduro = EstadoReproductivo.query.get(15)  # ID 15 corresponde a "Inmaduro"
                if estado_inmaduro:
                    form.id_estado_reprod.choices = [(15, 'Inmaduro')]
                    form.id_estado_reprod.data = 15
    
    if form.validate_on_submit():
        # Verificar si el animal es inmaduro según su edad y la madurez sexual de su raza
        estado_reprod = form.id_estado_reprod.data if form.id_estado_reprod.data != 0 else None
        
        # Si se seleccionó una raza y hay fecha de nacimiento
        if form.id_raza.data != 0 and form.fecha_nacimiento.data:
            raza = Raza.query.get(form.id_raza.data)
            if raza:
                # Calcular la edad en meses
                hoy = datetime.now()
                fecha_nac = form.fecha_nacimiento.data
                edad_meses = (hoy.year - fecha_nac.year) * 12 + (hoy.month - fecha_nac.month)
                
                # Verificar si es inmaduro según el sexo
                if form.sexo.data == 'Macho' and raza.madurez_sexual_machos_meses and edad_meses < raza.madurez_sexual_machos_meses:
                    # ID 15 corresponde a "Inmaduro" en la tabla estado_reproductivo
                    estado_reprod = 15
                elif form.sexo.data == 'Hembra' and raza.madurez_sexual_hembras_meses and edad_meses < raza.madurez_sexual_hembras_meses:
                    # ID 15 corresponde a "Inmaduro" en la tabla estado_reproductivo
                    estado_reprod = 15
        
        # Crear nuevo animal
        nuevo_animal = Animal(
            nombre_animal=form.nombre_animal.data,
            id_raza=form.id_raza.data if form.id_raza.data != 0 else None,
            fecha_nacimiento=form.fecha_nacimiento.data,
            sexo=form.sexo.data,
            id_finca=form.id_finca.data,
            id_potrero=form.id_potrero.data if form.id_potrero.data != 0 else None,
            id_padre=form.id_padre.data if form.id_padre.data != 0 else None,
            id_madre=form.id_madre.data if form.id_madre.data != 0 else None,
            ubicacion_animal=form.ubicacion_animal.data,
            origen=form.origen.data,
            id_estado_reprod=estado_reprod
        )
        
        try:
            db.session.add(nuevo_animal)
            db.session.commit()
            
            # Si el origen es "comprado", registrar la compra automáticamente
            if form.origen.data == 'comprado':
                nueva_compra = CompraAnimales(
                    id_animal=nuevo_animal.id_animal,
                    fecha_compra=datetime.now().date(),
                    precio_compra=0,  # Valor por defecto, se puede actualizar después
                    fecha_registro=datetime.now()
                )
                db.session.add(nueva_compra)
                db.session.commit()
                flash('Se ha registrado automáticamente la compra del animal. Por favor, actualice los detalles de la compra más tarde.', 'info')
            
            # Registrar actividad
            registrar_actividad("Creó", f"Animal: {nuevo_animal.nombre_animal}")
            
            flash('Animal creado exitosamente!', 'success')
            return redirect(url_for('gestion_animales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el animal: {str(e)}', 'danger')
    
    return render_template('dueño/crear_animal.html', form=form)

@login_required
def get_potreros_por_finca():
    finca_id = request.args.get('finca_id', 0, type=int)
    if finca_id == 0:
        return jsonify([])
    
    potreros = Potrero.query.filter_by(id_finca=finca_id).all()
    return jsonify([(p.id_potrero, p.nombre_potrero) for p in potreros])

@login_required
def get_animales_disponibles():
    """Obtener animales sin potrero asignado de una finca específica"""
    finca_id = request.args.get('finca_id', 0, type=int)
    if finca_id == 0:
        return jsonify([])
    
    # Verificar que el usuario tenga acceso a esta finca
    finca_usuario = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not finca_usuario:
        return jsonify([])
    
    # Obtener animales sin potrero asignado (id_potrero es NULL) o con valor 0
    animales = Animal.query.options(joinedload(Animal.raza)).filter(
        Animal.id_finca == finca_id,
        (Animal.id_potrero == None) | (Animal.id_potrero == 0)
    ).all()
    
    # Convertir a formato JSON
    resultado = []
    for animal in animales:
        resultado.append({
            'id_animal': animal.id_animal,
            'nombre_animal': animal.nombre_animal,
            'sexo': animal.sexo,
            'raza': {'nombre_raza': animal.raza.nombre_raza} if animal.raza else None
        })
    
    return jsonify(resultado)

@login_required
def get_animales_potrero():
    """Obtener animales asignados a un potrero específico"""
    potrero_id = request.args.get('potrero_id', 0, type=int)
    if potrero_id == 0:
        return jsonify([])
    
    # Obtener el potrero para verificar la finca
    potrero = Potrero.query.get(potrero_id)
    if not potrero:
        return jsonify([])
    
    # Verificar que el usuario tenga acceso a la finca del potrero
    finca_usuario = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not finca_usuario:
        return jsonify([])
    
    # Obtener animales del potrero
    animales = Animal.query.options(joinedload(Animal.raza)).filter(
        Animal.id_potrero == potrero_id
    ).all()
    
    # Convertir a formato JSON
    resultado = []
    for animal in animales:
        resultado.append({
            'id_animal': animal.id_animal,
            'nombre_animal': animal.nombre_animal,
            'sexo': animal.sexo,
            'fecha_nacimiento': animal.fecha_nacimiento.strftime('%Y-%m-%d'),
            'raza': {'nombre_raza': animal.raza.nombre_raza} if animal.raza else None
        })
    
    return jsonify(resultado)

@login_required
def asignar_animales_potrero():
    """Asignar animales a un potrero específico"""
    data = request.json
    potrero_id = data.get('potrero_id')
    animales_ids = data.get('animales_ids', [])
    
    if not potrero_id or not animales_ids:
        return jsonify({'success': False, 'message': 'Datos incompletos'})
    
    # Obtener el potrero para verificar su estado
    potrero = Potrero.query.get(potrero_id)
    if not potrero:
        return jsonify({'success': False, 'message': 'Potrero no encontrado'})
    
    # Verificar que el potrero esté activo
    if potrero.estado != 'activo':
        return jsonify({'success': False, 'message': 'No se pueden asignar animales a un potrero que no está activo'})
    
    # Verificar que el usuario tenga acceso a la finca del potrero
    finca_usuario = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not finca_usuario:
        return jsonify({'success': False, 'message': 'No tienes permiso para modificar este potrero'})
    
    try:
        # Asignar los animales al potrero
        for animal_id in animales_ids:
            animal = Animal.query.get(animal_id)
            if animal and animal.id_finca == potrero.id_finca:
                animal.id_potrero = potrero_id
        
        db.session.commit()
        registrar_actividad(f'Asignó {len(animales_ids)} animales al potrero {potrero.nombre_potrero}')
        return jsonify({'success': True, 'message': 'Animales asignados correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al asignar animales: {str(e)}'})

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
        # Verificar si el animal es inmaduro según su edad y la madurez sexual de su raza
        estado_reprod = form.id_estado_reprod.data if form.id_estado_reprod.data != 0 else None
        
        # Si se seleccionó una raza y hay fecha de nacimiento
        if form.id_raza.data != 0 and form.fecha_nacimiento.data:
            raza = Raza.query.get(form.id_raza.data)
            if raza:
                # Calcular la edad en meses
                hoy = datetime.now()
                fecha_nac = form.fecha_nacimiento.data
                edad_meses = (hoy.year - fecha_nac.year) * 12 + (hoy.month - fecha_nac.month)
                
                # Verificar si es inmaduro según el sexo
                if form.sexo.data == 'Macho' and raza.madurez_sexual_machos_meses and edad_meses < raza.madurez_sexual_machos_meses:
                    # ID 15 corresponde a "Inmaduro" en la tabla estado_reproductivo
                    estado_reprod = 15
                elif form.sexo.data == 'Hembra' and raza.madurez_sexual_hembras_meses and edad_meses < raza.madurez_sexual_hembras_meses:
                    # ID 15 corresponde a "Inmaduro" en la tabla estado_reproductivo
                    estado_reprod = 15
        
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
        animal.id_estado_reprod = estado_reprod
        
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