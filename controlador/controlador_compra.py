from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from config import app, db, allowed_document, registrar_actividad
from modelo.models import Animal, CompraAnimales, Finca, UsuarioFinca
from forms.compra_form import CompraAnimalForm
from datetime import date
from werkzeug.utils import secure_filename
import os
import time

@app.route('/animales_comprados')
@login_required
def listar_animales_comprados():
    # Fincas del usuario
    fincas_usuario = (Finca.query
                      .join(UsuarioFinca)
                      .filter(UsuarioFinca.usuario_id == current_user.id)
                      .all())

    selected_finca_id = request.args.get('finca_id', type=int)

    # Animales comprados, opcionalmente filtrados por finca
    query = Animal.query.filter_by(origen='comprado')
    if selected_finca_id:
        query = query.filter(Animal.id_finca == selected_finca_id)
    animales_comprados = query.all()

    return render_template(
        'dueño/animales_comprados.html',
        animales=animales_comprados,
        fincas=fincas_usuario,
        selected_finca_id=selected_finca_id
    )

@app.route('/editar_compra/<int:id_animal>', methods=['GET', 'POST'])
@login_required
def editar_compra(id_animal):
    # Obtener el animal
    animal = Animal.query.get_or_404(id_animal)
    
    # Verificar que el animal tenga origen "comprado"
    if animal.origen != 'comprado':
        flash('Este animal no tiene origen de compra', 'danger')
        return redirect(url_for('listar_animales_comprados'))
    
    # Obtener o crear el registro de compra
    compra = CompraAnimales.query.filter_by(id_animal=id_animal).first()
    if not compra:
        compra = CompraAnimales(
            id_animal=id_animal,
            fecha_compra=date.today(),
            precio_compra=0
        )
        db.session.add(compra)
        db.session.commit()
    
    # Crear el formulario
    form = CompraAnimalForm(obj=compra)
    
    if form.validate_on_submit():
        # Actualizar campos básicos
        form.populate_obj(compra)

        # Normalizar precio con formatos locales (puntos miles, coma decimal)
        raw_precio = request.form.get('precio_compra', '')
        if raw_precio:
            try:
                normalized_precio = float(raw_precio.replace('.', '').replace(',', '.'))
                compra.precio_compra = normalized_precio
            except ValueError:
                flash('Precio inválido. Usa solo números, puntos y comas.', 'danger')
                return render_template('dueño/editar_compra.html', form=form, animal=animal, compra=compra)

        # Manejar archivo de documento de compra (imagen o PDF)
        file = request.files.get('documento_compra')
        if file and file.filename:
            filename = secure_filename(file.filename)
            if not allowed_document(filename):
                flash('Tipo de archivo no permitido. Usa pdf o imagen (png, jpg, jpeg, gif, webp).', 'danger')
                return render_template('dueño/editar_compra.html', form=form, animal=animal, compra=compra)

            # Directorio de subida dentro de static/uploads/compras
            upload_dir = os.path.join(app.static_folder, 'uploads', 'compras')
            try:
                os.makedirs(upload_dir, exist_ok=True)
            except Exception:
                pass

            # Nombre único, corto para caber en String(50)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'dat'
            unique_name = f"{id_animal}_{int(time.time())}.{ext}"
            file_path = os.path.join(upload_dir, unique_name)
            file.save(file_path)

            # Guardar ruta relativa para uso con url_for('static', ...)
            compra.documento_compra = os.path.join('uploads', 'compras', unique_name).replace('\\', '/')

        db.session.commit()
        registrar_actividad(current_user.id, 'Actualizó', f'Datos de compra del animal: {animal.nombre_animal}')
        flash('Datos de compra actualizados correctamente', 'success')
        return redirect(url_for('listar_animales_comprados'))
    
    return render_template('dueño/editar_compra.html', form=form, animal=animal, compra=compra)