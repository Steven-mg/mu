from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from config import app, db, registrar_actividad
from modelo.models import Animal, CompraAnimales
from forms.compra_form import CompraAnimalForm
from datetime import date

@app.route('/animales_comprados')
@login_required
def listar_animales_comprados():
    # Obtener todos los animales con origen "comprado"
    animales_comprados = Animal.query.filter_by(origen='comprado').all()
    return render_template('dueño/animales_comprados.html', animales=animales_comprados)

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
        form.populate_obj(compra)
        db.session.commit()
        registrar_actividad(current_user.id, 'Actualizó', f'Datos de compra del animal: {animal.nombre_animal}')
        flash('Datos de compra actualizados correctamente', 'success')
        return redirect(url_for('listar_animales_comprados'))
    
    return render_template('dueño/editar_compra.html', form=form, animal=animal)