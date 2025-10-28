from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from modelo.models import db, Animal, Raza, Finca, EstadoReproductivo, UsuarioFinca, CompraAnimales, Potrero, AnimalGrupo, GrupoAnimal, DocumentoGenetico, ServiciosSalud, TipoServicioSalud, Trabajador, ServiciosSexuales, TipoServicioSexual
from sqlalchemy.orm import joinedload
from forms.animal_form import AnimalForm, FiltroAnimalForm
from controlador.controlador_actividad import registrar_actividad
from config import app, allowed_image, allowed_document
from io import BytesIO
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    Image = None
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta

@login_required
def listar_animales():
    """Listar animales, con opción de filtrar por `finca_id` del usuario"""
    # Fincas del usuario
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_ids = [f.id_finca for f in fincas_usuario]

    # Filtro opcional por finca específica
    finca_id = request.args.get('finca_id', type=int)

    if not finca_ids:
        animales = []
    else:
        query = Animal.query.filter(Animal.id_finca.in_(finca_ids))
        if finca_id and finca_id in finca_ids:
            query = query.filter(Animal.id_finca == finca_id)
        animales = query.all()

    return render_template('dueño/gestion_animales.html', animales=animales, fincas=fincas_usuario, finca_id_seleccionada=finca_id)

@login_required
def gestion_produccion():
    """Página para seleccionar finca y separar animales por sexo"""
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_id = request.args.get('finca_id', type=int)
    finca = None
    hembras = []
    machos = []
    if finca_id:
        # Verificar acceso del usuario a la finca seleccionada
        relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
        if not relacion and current_user.tipo_usuario != 3:
            flash('No tienes permisos para ver esta finca', 'danger')
            return redirect(url_for('gestion_produccion_route'))
        finca = Finca.query.get_or_404(finca_id)
        hembras = Animal.query.filter(Animal.id_finca == finca_id, Animal.sexo == 'Hembra').order_by(Animal.nombre_animal.asc()).all()
        machos = Animal.query.filter(Animal.id_finca == finca_id, Animal.sexo == 'Macho').order_by(Animal.nombre_animal.asc()).all()
    return render_template('dueño/gestion_produccion.html', fincas=fincas_usuario, finca=finca, hembras=hembras, machos=machos, finca_id_seleccionada=finca_id)

@login_required
def ver_animales_finca(finca_id):
    """Mostrar información de una finca y los animales presentes solo en esa finca"""
    # Verificar acceso del usuario a la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver esta finca', 'danger')
        return redirect(url_for('mis_fincas'))

    # Obtener finca y animales asociados
    finca = Finca.query.get_or_404(finca_id)
    animales = (Animal.query
                .filter(
                    Animal.id_finca == finca_id,
                    Animal.ubicacion_animal.in_(['en finca', 'en_finca'])
                )
                .all())

    return render_template('dueño/ver_animales_finca.html', finca=finca, animales=animales)

@login_required
def ver_animales_fuera(finca_id):
    """Mostrar información de una finca y los animales registrados como fuera de la finca"""
    # Verificar acceso del usuario a la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver esta finca', 'danger')
        return redirect(url_for('mis_fincas'))

    # Obtener finca y animales fuera de la finca
    finca = Finca.query.get_or_404(finca_id)
    animales = (Animal.query
                .filter(
                    Animal.id_finca == finca_id,
                    Animal.ubicacion_animal == 'fuera de la finca'
                )
                .all())

    return render_template('dueño/ver_animales_fuera_finca.html', finca=finca, animales=animales)

@login_required
def ver_animales_fuera_global():
    """Listar todos los animales registrados como fuera de la finca en las fincas del usuario"""
    # Fincas del usuario
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_ids = [f.id_finca for f in fincas_usuario]

    if not finca_ids:
        animales = []
    else:
        animales = (Animal.query
                    .filter(
                        Animal.id_finca.in_(finca_ids),
                        Animal.ubicacion_animal == 'fuera de la finca'
                    )
                    .all())

    return render_template('dueño/ver_animales_fuera_global.html', animales=animales)

@login_required
def procedimientos_animal(animal_id):
    """Gestionar procedimientos de salud y sexuales para un animal"""
    animal = Animal.query.get_or_404(animal_id)

    # Formularios
    from forms.servicio_salud_form import ServicioSaludForm
    from forms.servicio_sexual_form import ServicioSexualForm
    form_salud = ServicioSaludForm()
    form_sexual = ServicioSexualForm()

    # Choices dinámicos filtrados por la regla explícita aplica_a_sexo
    sexo_animal = (animal.sexo or '').lower()
    salud_macho_only = {
        'Castración'
    }
    salud_hembra_only = {
        'Cesárea',
        'Diagnóstico de Preñez',
        'Control de Mastitis'
    }
    sexual_macho_only = {
        'Evaluación de Fertilidad Toros',
        'Banco de Semen Propio'
    }
    sexual_hembra_only = {
        'Inseminación Artificial Convencional',
        'Transferencia de Embriones Fresh',
        'Sincronización de Celos Hormonal',
        'Diagnóstico de Preñez Temprano',
        'Asistencia en Partos Distócicos',
        'Revisión Postparto Completa',
        'Programa IATF'
    }

    # Determinar si el animal es sexualmente inmaduro
    def es_inmaduro_sexual(an):
        try:
            # Estado reproductivo explícito (ID 15 = Inmaduro)
            if getattr(an, 'id_estado_reprod', None) == 15:
                return True
            if getattr(an, 'estado_reprod', None) and (getattr(an.estado_reprod, 'descripcion', '') or '').lower() == 'inmaduro':
                return True

            # Cálculo por edad y madurez de raza
            raza = Raza.query.get(getattr(an, 'id_raza', None)) if getattr(an, 'id_raza', None) else None
            fecha_nac = getattr(an, 'fecha_nacimiento', None)
            if raza and fecha_nac:
                hoy = datetime.now()
                edad_meses = (hoy.year - fecha_nac.year) * 12 + (hoy.month - fecha_nac.month)
                if sexo_animal == 'macho' and raza.madurez_sexual_machos_meses and edad_meses < raza.madurez_sexual_machos_meses:
                    return True
                if sexo_animal == 'hembra' and raza.madurez_sexual_hembras_meses and edad_meses < raza.madurez_sexual_hembras_meses:
                    return True
        except Exception:
            # En caso de cualquier error, no bloquear por defecto
            return False
        return False

    def filtrar_por_nombre_y_sexo(tipos, sexo, macho_only, hembra_only):
        s = (sexo or '').lower()
        mset = {n.lower() for n in macho_only}
        hset = {n.lower() for n in hembra_only}
        r = []
        for t in tipos:
            aplica = (getattr(t, 'aplica_a_sexo', 'ambos') or 'ambos').lower()
            nombre = (getattr(t, 'nombre_servicio', '') or '').lower()
            if aplica == 'ambos':
                if s == 'macho' and nombre in hset:
                    continue
                if s == 'hembra' and nombre in mset:
                    continue
                r.append(t)
            else:
                if aplica in ['ambos', s]:
                    r.append(t)
        return r

    def aplica_real_por_nombre(t, macho_only, hembra_only):
        aplica = (getattr(t, 'aplica_a_sexo', 'ambos') or 'ambos').lower()
        nombre = (getattr(t, 'nombre_servicio', '') or '').lower()
        if aplica == 'ambos':
            if nombre in {n.lower() for n in macho_only}:
                return 'macho'
            if nombre in {n.lower() for n in hembra_only}:
                return 'hembra'
        return aplica
    if sexo_animal == 'macho':
        tipos_salud_q = TipoServicioSalud.query.filter(TipoServicioSalud.aplica_a_sexo.in_(['ambos', 'macho'])).all()
        tipos_sexual_q = TipoServicioSexual.query.filter(TipoServicioSexual.aplica_a_sexo.in_(['ambos', 'macho'])).all()
        tipos_salud = filtrar_por_nombre_y_sexo(tipos_salud_q, sexo_animal, salud_macho_only, salud_hembra_only)
        tipos_sexual = filtrar_por_nombre_y_sexo(tipos_sexual_q, sexo_animal, sexual_macho_only, sexual_hembra_only)
    elif sexo_animal == 'hembra':
        tipos_salud_q = TipoServicioSalud.query.filter(TipoServicioSalud.aplica_a_sexo.in_(['ambos', 'hembra'])).all()
        tipos_sexual_q = TipoServicioSexual.query.filter(TipoServicioSexual.aplica_a_sexo.in_(['ambos', 'hembra'])).all()
        tipos_salud = filtrar_por_nombre_y_sexo(tipos_salud_q, sexo_animal, salud_macho_only, salud_hembra_only)
        tipos_sexual = filtrar_por_nombre_y_sexo(tipos_sexual_q, sexo_animal, sexual_macho_only, sexual_hembra_only)
    else:
        tipos_salud = TipoServicioSalud.query.all()
        tipos_sexual = TipoServicioSexual.query.all()

    # Filtro adicional por inmadurez sexual: SOLO afecta servicios sexuales
    inmaduro = es_inmaduro_sexual(animal)
    if inmaduro:
        if sexo_animal == 'macho':
            # Macho inmaduro: bloquear servicios sexuales
            tipos_sexual = []
        elif sexo_animal == 'hembra':
            # Hembra inmadura: permitir únicamente "Capacitación en Detección de Celo" en sexual
            tipos_sexual = [t for t in tipos_sexual if (getattr(t, 'nombre_servicio', '') or '').lower() in {'capacitación en detección de celo', 'capacitacion en deteccion de celo'}]

    form_salud.id_tipo_salud.choices = [(t.id_tipo_salud, t.nombre_servicio) for t in tipos_salud]
    # Listar trabajadores del dueño actual con rol veterinario y estado activo
    vets = Trabajador.query.filter(
        Trabajador.id_jefe == current_user.id,
        Trabajador.rol == 'veterinario',
        Trabajador.estado == 'activo'
    ).all()
    form_salud.id_veterinario.choices = [(v.id_trabajador, f"{v.nombre} {v.apellido}") for v in vets]
    form_sexual.id_servicioanimal.choices = [(t.id_servicio, t.nombre_servicio) for t in tipos_sexual]
    form_sexual.id_veterinario.choices = [(v.id_trabajador, f"{v.nombre} {v.apellido}") for v in vets]
    # Construir mapa de duraciones para la UI (id -> días)
    duraciones_salud = {t.id_tipo_salud: int(getattr(t, 'duracion_efecto_dias', 0) or 0) for t in tipos_salud}

    # Procesamiento de altas
    if request.method == 'POST' and request.form.get('form_name') == 'salud':
        if form_salud.validate_on_submit():
            tipo_salud_sel = TipoServicioSalud.query.get(form_salud.id_tipo_salud.data)
            aplica_salud = aplica_real_por_nombre(tipo_salud_sel, salud_macho_only, salud_hembra_only) if tipo_salud_sel else 'ambos'
            # Bloqueo si el tipo de servicio requiere veterinario y el usuario no es veterinario
            try:
                requiere_vet = bool(getattr(tipo_salud_sel, 'requiere_veterinario', False))
            except Exception:
                requiere_vet = False
            # No bloquear por rol del usuario; solo validar profesional cuando el servicio lo requiera
            # Validación adicional: el profesional seleccionado debe ser un trabajador con rol veterinario activo
            vet = Trabajador.query.get(form_salud.id_veterinario.data)
            if requiere_vet and (not vet or vet.rol != 'veterinario' or vet.estado != 'activo'):
                flash('Debe seleccionar un profesional veterinario activo.', 'warning')
                return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
            # Sin bloqueo por inmadurez para servicios de salud
            if sexo_animal == 'macho' and aplica_salud == 'hembra':
                flash('Este servicio de salud aplica solo a hembras.', 'warning')
                return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
            if sexo_animal == 'hembra' and aplica_salud == 'macho':
                flash('Este servicio de salud aplica solo a machos.', 'warning')
                return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
            # Calcular fecha próxima automáticamente si no fue ingresada
            fecha_proximo_val = form_salud.fecha_proximo.data
            try:
                duracion_dias = int(getattr(tipo_salud_sel, 'duracion_efecto_dias', 0) or 0)
            except Exception:
                duracion_dias = 0
            if not fecha_proximo_val and duracion_dias and form_salud.fecha_servicio.data:
                try:
                    fecha_proximo_val = form_salud.fecha_servicio.data + timedelta(days=duracion_dias)
                except Exception:
                    fecha_proximo_val = None
            nuevo = ServiciosSalud(
                id_animal=animal_id,
                id_tipo_salud=form_salud.id_tipo_salud.data,
                id_veterinario=form_salud.id_veterinario.data,
                fecha_servicio=form_salud.fecha_servicio.data,
                fecha_proximo=fecha_proximo_val,
                dosis=form_salud.dosis.data,
                observaciones=form_salud.observaciones.data,
                costo=form_salud.costo.data,
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Servicio de salud registrado', 'success')
            return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
        else:
            # Mostrar errores de validación del formulario de salud
            try:
                errores = []
                for campo, msgs in (form_salud.errors or {}).items():
                    etiqueta = getattr(getattr(form_salud, campo, None), 'label', None)
                    nombre = etiqueta.text if etiqueta else campo
                    for m in msgs:
                        errores.append(f"{nombre}: {m}")
                mensaje = 'No se pudo registrar el servicio de salud. '
                if errores:
                    mensaje += ' ' + '; '.join(errores)
                else:
                    mensaje += 'Revise los campos obligatorios.'
                flash(mensaje, 'warning')
            except Exception:
                flash('No se pudo registrar el servicio de salud. Revise los campos obligatorios.', 'warning')

    if request.method == 'POST' and request.form.get('form_name') == 'sexual':
        if form_sexual.validate_on_submit():
            tipo_sexual_sel = TipoServicioSexual.query.get(form_sexual.id_servicioanimal.data)
            aplica_sexual = aplica_real_por_nombre(tipo_sexual_sel, sexual_macho_only, sexual_hembra_only) if tipo_sexual_sel else 'ambos'
            # Bloqueo por inmadurez sexual
            if inmaduro:
                if sexo_animal == 'macho':
                    flash('Animal inmaduro: en machos no se permiten servicios sexuales.', 'warning')
                    return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
                elif sexo_animal == 'hembra':
                    if not tipo_sexual_sel or (tipo_sexual_sel.nombre_servicio or '').lower() not in {'capacitación en detección de celo', 'capacitacion en deteccion de celo'}:
                        flash('Animal inmaduro: en hembras solo se permite Capacitación en Detección de Celo.', 'warning')
                        return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
            if sexo_animal == 'macho' and aplica_sexual == 'hembra':
                flash('Este servicio sexual aplica solo a hembras.', 'warning')
                return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
            if sexo_animal == 'hembra' and aplica_sexual == 'macho':
                flash('Este servicio sexual aplica solo a machos.', 'warning')
                return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
            nuevo = ServiciosSexuales(
                id_servicioanimal=form_sexual.id_servicioanimal.data,
                id_animal=animal_id,
                id_veterinario=form_sexual.id_veterinario.data,
                fecha_servicio=form_sexual.fecha_servicio.data,
                fecha_proximo=form_sexual.fecha_proximo.data,
                notas_servicio=form_sexual.notas_servicio.data,
                costo_total=form_sexual.costo_total.data,
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Servicio sexual registrado', 'success')
            return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
        else:
            # Mostrar errores de validación del formulario sexual
            try:
                errores = []
                for campo, msgs in (form_sexual.errors or {}).items():
                    etiqueta = getattr(getattr(form_sexual, campo, None), 'label', None)
                    nombre = etiqueta.text if etiqueta else campo
                    for m in msgs:
                        errores.append(f"{nombre}: {m}")
                mensaje = 'No se pudo registrar el servicio sexual. '
                if errores:
                    mensaje += ' ' + '; '.join(errores)
                else:
                    mensaje += 'Revise los campos obligatorios.'
                flash(mensaje, 'warning')
            except Exception:
                flash('No se pudo registrar el servicio sexual. Revise los campos obligatorios.', 'warning')

    servicios_salud = ServiciosSalud.query.filter_by(id_animal=animal_id).order_by(ServiciosSalud.fecha_servicio.desc()).all()
    servicios_sexuales = ServiciosSexuales.query.filter_by(id_animal=animal_id).order_by(ServiciosSexuales.fecha_servicio.desc()).all()

    # Pasar información de filtrado por sexo a la plantilla para mensajes/condicionales
    return render_template(
        'dueño/procedimientos_animal.html',
        animal=animal,
        form_salud=form_salud,
        form_sexual=form_sexual,
        servicios_salud=servicios_salud,
        servicios_sexuales=servicios_sexuales,
        sexo_animal=animal.sexo,
        tipos_salud_count=len(tipos_salud),
        tipos_sexual_count=len(tipos_sexual),
        duraciones_salud=duraciones_salud
    )

@login_required
def historial_procedimientos(animal_id):
    """Ver historial de servicios de salud y sexuales para un animal"""
    animal = Animal.query.get_or_404(animal_id)
    servicios_salud = ServiciosSalud.query.filter_by(id_animal=animal_id).order_by(ServiciosSalud.fecha_servicio.desc()).all()
    servicios_sexuales = ServiciosSexuales.query.filter_by(id_animal=animal_id).order_by(ServiciosSexuales.fecha_servicio.desc()).all()
    return render_template(
        'dueño/historial_procedimientos.html',
        animal=animal,
        servicios_salud=servicios_salud,
        servicios_sexuales=servicios_sexuales
    )

@login_required
def eliminar_servicio_salud(animal_id, servicio_id):
    servicio = ServiciosSalud.query.get_or_404(servicio_id)
    if servicio.id_animal != animal_id:
        flash('El servicio no pertenece al animal indicado.', 'danger')
        return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
    db.session.delete(servicio)
    db.session.commit()
    flash('Servicio de salud eliminado', 'success')
    return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))

@login_required
def eliminar_servicio_sexual(animal_id, servicio_id):
    servicio = ServiciosSexuales.query.get_or_404(servicio_id)
    if servicio.id_animal != animal_id:
        flash('El servicio no pertenece al animal indicado.', 'danger')
        return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))
    db.session.delete(servicio)
    db.session.commit()
    flash('Servicio sexual eliminado', 'success')
    return redirect(url_for('procedimientos_animal_route', animal_id=animal_id))

@login_required
def crear_animal():
    """Crear un nuevo animal"""
    form = AnimalForm()
    
    # Filtrar fincas del usuario actual
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    form.id_finca.choices = [(0, 'Seleccione una finca')] + [(f.id_finca, f.nombre_finca) for f in fincas_usuario]

    # Poblar opciones de potrero según finca seleccionada en POST para evitar "Not a valid choice"
    try:
        if request.method == 'POST':
            finca_sel = request.form.get('id_finca', type=int)
            if finca_sel and finca_sel != 0:
                potreros = Potrero.query.filter(Potrero.id_finca == finca_sel, Potrero.estado != 'descanso').all()
                form.id_potrero.choices = [(0, 'Seleccione un potrero')] + [(p.id_potrero, p.nombre_potrero) for p in potreros]
            else:
                form.id_potrero.choices = [(0, 'Seleccione primero una finca')]
    except Exception:
        # En caso de error, mantener opción por defecto para no bloquear
        form.id_potrero.choices = [(0, 'Seleccione un potrero')]
    
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
        # Validar que el potrero seleccionado pertenezca a la finca y no esté en descanso
        if form.id_potrero.data and form.id_potrero.data != 0:
            potrero_sel = Potrero.query.get(form.id_potrero.data)
            if not potrero_sel or potrero_sel.id_finca != form.id_finca.data or potrero_sel.estado == 'descanso':
                flash('Seleccione un potrero válido de la finca y que esté activo.', 'danger')
                return render_template('dueño/crear_animal.html', form=form)

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
        
        # Manejar foto subida como blob
        foto_bytes = None
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                if allowed_image(file.filename):
                    # Leer bytes directamente y almacenar en BD
                    foto_bytes = file.read()
                else:
                    flash('Formato de imagen no permitido. Use jpg, jpeg, png o gif.', 'danger')
                    return render_template('dueño/crear_animal.html', form=form)

        # Validación: nombre único por dueño (en todas sus fincas)
        try:
            fincas_usuario_ids = [f.id_finca for f in Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()]
        except Exception:
            fincas_usuario_ids = []

        if fincas_usuario_ids:
            duplicado = Animal.query.filter(
                Animal.nombre_animal == form.nombre_animal.data,
                Animal.id_finca.in_(fincas_usuario_ids)
            ).first()
            if duplicado:
                flash('Ya tienes un animal con este nombre en tus fincas.', 'danger')
                return render_template('dueño/crear_animal.html', form=form)

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
            id_estado_reprod=estado_reprod,
            foto_animal=foto_bytes
        )
        
        try:
            db.session.add(nuevo_animal)
            db.session.commit()

            # Si se seleccionó un grupo, crear relación en AnimalGrupo
            try:
                grupo_id = form.id_grupo.data if hasattr(form, 'id_grupo') else 0
                if grupo_id and grupo_id != 0:
                    grupo = GrupoAnimal.query.get(grupo_id)
                    # Validar que el grupo exista y pertenezca a la misma finca
                    if grupo and grupo.id_finca == nuevo_animal.id_finca:
                        # Asegurar unicidad: no permitir que un animal pertenezca a múltiples grupos
                        existe_cualquier = AnimalGrupo.query.filter_by(id_animal=nuevo_animal.id_animal).first()
                        if existe_cualquier:
                            # Si ya pertenece a algún grupo, no crear una nueva relación
                            pass
                        else:
                            existe_rel = AnimalGrupo.query.filter_by(id_animal=nuevo_animal.id_animal, id_grupo=grupo_id).first()
                            if not existe_rel:
                                relacion = AnimalGrupo(id_animal=nuevo_animal.id_animal,
                                                       id_grupo=grupo_id,
                                                       fecha_asignacion=datetime.now().date())
                                db.session.add(relacion)
                                db.session.commit()
            except Exception:
                # No bloquear creación del animal si falla la asignación al grupo
                db.session.rollback()
            
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
            # Redirigir a la tabla de animales de la finca correspondiente
            return redirect(url_for('ver_animales_finca_route', finca_id=nuevo_animal.id_finca))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el animal: {str(e)}', 'danger')
    
    return render_template('dueño/crear_animal.html', form=form)

@login_required
def get_potreros_por_finca():
    finca_id = request.args.get('finca_id', 0, type=int)
    exclude_descanso = request.args.get('exclude_descanso', 0, type=int)
    if finca_id == 0:
        return jsonify([])
    
    query = Potrero.query.filter_by(id_finca=finca_id)
    if exclude_descanso:
        query = query.filter(Potrero.estado != 'descanso')
    potreros = query.all()
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
    # y que estén físicamente en la finca
    # Nota: En algunos datos existentes, "ubicacion_animal" puede estar almacenado como
    # "en_finca" (con guion bajo). Para garantizar que se listen correctamente,
    # aceptamos ambos formatos.
    animales = (Animal.query
                .options(joinedload(Animal.raza))
                .filter(
                    Animal.id_finca == finca_id,
                    (Animal.id_potrero == None) | (Animal.id_potrero == 0),
                    Animal.ubicacion_animal.in_(['en finca', 'en_finca'])
                )
                .order_by(Animal.nombre_animal.asc())
                .all())
    
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
        # Validar capacidad del potrero si está definida
        # Contar animales actualmente asignados
        animales_actuales = Animal.query.filter(Animal.id_potrero == potrero_id).count()
        capacidad = potrero.capacidad_animal or 0
        # Convertir IDs a enteros por seguridad
        ids_a_asignar = [int(a) for a in animales_ids]
        cantidad_nueva = len(ids_a_asignar)
        if capacidad and (animales_actuales + cantidad_nueva) > capacidad:
            cupos = max(0, capacidad - animales_actuales)
            return jsonify({'success': False, 'message': f'Capacidad insuficiente. Cupos disponibles: {cupos}'}), 400

        # Asignar los animales al potrero
        for animal_id in ids_a_asignar:
            animal = Animal.query.get(animal_id)
            if animal and animal.id_finca == potrero.id_finca:
                animal.id_potrero = potrero_id
        
        db.session.commit()
        registrar_actividad(f'Asignó {cantidad_nueva} animales al potrero {potrero.nombre_potrero}')
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
        
        # Validación: nombre único por dueño (en todas sus fincas) excluyendo el propio animal
        try:
            fincas_usuario_ids = [f.id_finca for f in Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()]
        except Exception:
            fincas_usuario_ids = []

        if fincas_usuario_ids:
            duplicado = Animal.query.filter(
                Animal.nombre_animal == form.nombre_animal.data,
                Animal.id_finca.in_(fincas_usuario_ids),
                Animal.id_animal != animal.id_animal
            ).first()
            if duplicado:
                flash('Ya tienes un animal con este nombre en tus fincas.', 'danger')
                return render_template('dueño/editar_animal.html', form=form, animal=animal)

        # Validaciones defensivas adicionales
        if form.id_padre.data and form.id_padre.data != 0 and form.id_padre.data == animal.id_animal:
            flash('Un animal no puede ser su propio padre.', 'danger')
            return render_template('dueño/editar_animal.html', form=form, animal=animal)
        if form.id_madre.data and form.id_madre.data != 0 and form.id_madre.data == animal.id_animal:
            flash('Un animal no puede ser su propia madre.', 'danger')
            return render_template('dueño/editar_animal.html', form=form, animal=animal)

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

        # Manejar reemplazo de foto si se sube (blob)
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename:
                if allowed_image(file.filename):
                    animal.foto_animal = file.read()
                else:
                    flash('Formato de imagen no permitido. Use jpg, jpeg, png o gif.', 'danger')
                    return render_template('dueño/editar_animal.html', form=form, animal=animal)
        
        try:
            db.session.commit()

            # Persistir selección de grupo si se proporcionó
            try:
                grupo_id = form.id_grupo.data if hasattr(form, 'id_grupo') else 0
                if grupo_id and grupo_id != 0:
                    grupo = GrupoAnimal.query.get(grupo_id)
                    if grupo and grupo.id_finca == animal.id_finca:
                        # Evitar múltiples relaciones a distintos grupos
                        relacion_any = AnimalGrupo.query.filter_by(id_animal=animal.id_animal).first()
                        if relacion_any and relacion_any.id_grupo != grupo_id:
                            # Ya pertenece a un grupo distinto, no crear nueva relación
                            flash('El animal ya pertenece a un grupo. Debe quitarlo primero antes de reasignar.', 'warning')
                        else:
                            existe_rel = AnimalGrupo.query.filter_by(id_animal=animal.id_animal, id_grupo=grupo_id).first()
                            if not existe_rel:
                                relacion = AnimalGrupo(id_animal=animal.id_animal,
                                                       id_grupo=grupo_id,
                                                       fecha_asignacion=datetime.now().date())
                                db.session.add(relacion)
                                db.session.commit()
            except Exception:
                db.session.rollback()
            
            # Registrar actividad
            registrar_actividad("Editó", f"Animal: {animal.nombre_animal}")
            
            flash('Animal actualizado exitosamente!', 'success')
            # Redirigir a la tabla de animales de la finca correspondiente
            return redirect(url_for('ver_animales_finca_route', finca_id=animal.id_finca))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el animal: {str(e)}', 'danger')
    
    return render_template('dueño/editar_animal.html', form=form, animal=animal)


@login_required
def api_madurez_sexual_por_raza(raza_id):
    """Devuelve meses de madurez sexual por raza para machos y hembras"""
    raza = Raza.query.get(raza_id)
    if not raza:
        return jsonify({'success': False, 'message': 'Raza no encontrada'}), 404
    return jsonify({
        'success': True,
        'macho': raza.madurez_sexual_machos_meses,
        'hembra': raza.madurez_sexual_hembras_meses
    })

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


# --- Genealogía ---
@login_required
def genealogia_animal(animal_id):
    """Ver genealogía del animal: padres y descendencia."""
    animal = Animal.query.options(joinedload(Animal.raza), joinedload(Animal.padre), joinedload(Animal.madre)).get_or_404(animal_id)

    # Validar acceso del usuario a la finca del animal
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este animal', 'danger')
        return redirect(url_for('gestion_animales'))

    # Padres
    padre = animal.padre
    madre = animal.madre

    # Hijos: combinar crias como padre y como madre, evitando duplicados
    hijos_ids = set()
    hijos = []
    for h in getattr(animal, 'crias_padre', []):
        if h.id_animal not in hijos_ids:
            hijos_ids.add(h.id_animal)
            hijos.append(h)
    for h in getattr(animal, 'crias_madre', []):
        if h.id_animal not in hijos_ids:
            hijos_ids.add(h.id_animal)
            hijos.append(h)

    # Ordenar hijos por nombre para visualización estable
    hijos = sorted(hijos, key=lambda x: (x.nombre_animal or '').lower())

    return render_template('dueño/genealogia_animal.html', animal=animal, padre=padre, madre=madre, hijos=hijos)


# --- Documentos Genéticos ---
@login_required
def documentos_geneticos(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    # Validar pertenencia del usuario a la finca del animal
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este animal', 'danger')
        return redirect(url_for('gestion_animales'))

    documentos = DocumentoGenetico.query.filter_by(id_animal=animal_id).order_by(DocumentoGenetico.id_documento.desc()).all()
    from forms.documento_genetico_form import DocumentoGeneticoForm
    form = DocumentoGeneticoForm()
    tipo_labels = {
        'prueba_adn': 'Análisis ADN',
        'pedigri': 'Pedigrí / Registro genealógico',
        'certificado_raza': 'Certificado de raza'
    }
    return render_template('dueño/documentos_geneticos.html', animal=animal, documentos=documentos, form=form, tipo_labels=tipo_labels)


@login_required
def agregar_documento_genetico(animal_id):
    from forms.documento_genetico_form import DocumentoGeneticoForm
    animal = Animal.query.get_or_404(animal_id)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para modificar este animal', 'danger')
        return redirect(url_for('gestion_animales'))

    form = DocumentoGeneticoForm()
    if request.method == 'POST' and form.validate_on_submit():
        file = request.files.get('archivo')
        if not file or not file.filename:
            flash('Debe seleccionar un archivo', 'danger')
            return render_template('dueño/documentos_geneticos.html', animal=animal, documentos=animal.documentos_geneticos, form=form)

        filename = secure_filename(file.filename)
        if not allowed_document(filename):
            flash('Tipo de archivo no permitido. Use pdf o imagen (png, jpg, jpeg, gif, webp).', 'danger')
            return render_template('dueño/documentos_geneticos.html', animal=animal, documentos=animal.documentos_geneticos, form=form)

        try:
            nuevo = DocumentoGenetico(
                id_animal=animal_id,
                nombre_documento=form.nombre_documento.data or filename,
                tipo_documento=form.tipo_documento.data,
                descripcion=form.descripcion.data,
                fecha_emision=form.fecha_emision.data,
                entidad_emisora=form.entidad_emisora.data,
                archivo=file.read()
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Documento genético agregado correctamente', 'success')
            return redirect(url_for('documentos_geneticos_route', animal_id=animal_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar el documento: {str(e)}', 'danger')

    documentos = DocumentoGenetico.query.filter_by(id_animal=animal_id).order_by(DocumentoGenetico.id_documento.desc()).all()
    return render_template('dueño/documentos_geneticos.html', animal=animal, documentos=documentos, form=form)


@login_required
def ver_documento_genetico(documento_id):
    doc = DocumentoGenetico.query.get_or_404(documento_id)
    animal = Animal.query.get_or_404(doc.id_animal)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este documento', 'danger')
        return redirect(url_for('gestion_animales'))

    # Calcular tipo MIME por nombre y detectar PDF por firma
    mime = _guess_mime_type(doc.nombre_documento or 'archivo')
    try:
        if doc.archivo and doc.archivo[:4] == b'%PDF':
            mime = 'application/pdf'
    except Exception:
        pass

    # Servir inline para abrir en el navegador sin descargar
    resp = app.response_class(doc.archivo, mimetype=mime or 'application/octet-stream')
    resp.headers['Content-Disposition'] = f'inline; filename="{(doc.nombre_documento or 'documento').replace('"','')}"'
    return resp


@login_required
def descargar_documento_genetico(documento_id):
    """Descargar el archivo del documento genético como attachment"""
    doc = DocumentoGenetico.query.get_or_404(documento_id)
    animal = Animal.query.get_or_404(doc.id_animal)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para descargar este documento', 'danger')
        return redirect(url_for('gestion_animales'))

    mime = _guess_mime_type(doc.nombre_documento or 'archivo')
    try:
        if doc.archivo and doc.archivo[:4] == b'%PDF':
            mime = 'application/pdf'
    except Exception:
        pass

    resp = app.response_class(doc.archivo, mimetype=mime or 'application/octet-stream')
    resp.headers['Content-Disposition'] = f'attachment; filename="{(doc.nombre_documento or 'documento').replace('"','')}"'
    return resp


@login_required
def eliminar_documento_genetico(documento_id):
    """Eliminar un documento genético"""
    doc = DocumentoGenetico.query.get_or_404(documento_id)
    animal = Animal.query.get_or_404(doc.id_animal)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para eliminar este documento', 'danger')
        return redirect(url_for('gestion_animales'))

    try:
        db.session.delete(doc)
        db.session.commit()
        flash('Documento eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el documento: {str(e)}', 'danger')

    return redirect(url_for('documentos_geneticos_route', animal_id=animal.id_animal))


@login_required
def editar_documento_genetico(documento_id):
    """Editar metadatos y, opcionalmente, reemplazar el archivo del documento genético."""
    from forms.documento_genetico_form import EditarDocumentoGeneticoForm
    doc = DocumentoGenetico.query.get_or_404(documento_id)
    animal = Animal.query.get_or_404(doc.id_animal)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para editar este documento', 'danger')
        return redirect(url_for('gestion_animales'))

    form = EditarDocumentoGeneticoForm(obj=doc)

    if request.method == 'POST' and form.validate_on_submit():
        try:
            doc.nombre_documento = form.nombre_documento.data or doc.nombre_documento
            doc.tipo_documento = form.tipo_documento.data
            doc.descripcion = form.descripcion.data
            doc.fecha_emision = form.fecha_emision.data
            doc.entidad_emisora = form.entidad_emisora.data

            file = request.files.get('archivo')
            if file and file.filename:
                filename = secure_filename(file.filename)
                if not allowed_document(filename):
                    flash('Tipo de archivo no permitido. Use pdf o imagen (png, jpg, jpeg, gif, webp).', 'danger')
                    return render_template('dueño/editar_documento_genetico.html', animal=animal, documento=doc, form=form)
                doc.archivo = file.read()

            db.session.commit()
            flash('Documento actualizado correctamente', 'success')
            return redirect(url_for('documentos_geneticos_route', animal_id=animal.id_animal))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el documento: {str(e)}', 'danger')

    return render_template('dueño/editar_documento_genetico.html', animal=animal, documento=doc, form=form)


def _guess_mime_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mapping = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'pdf': 'application/pdf'
    }
    return mapping.get(ext, 'application/octet-stream')


def _stream_blob(blob_bytes, mime_type):
    if not blob_bytes:
        return jsonify({'error': 'Archivo no disponible'}), 404
    try:
        return app.response_class(blob_bytes, mimetype=mime_type or 'application/octet-stream')
    except Exception:
        return app.response_class(blob_bytes, mimetype='application/octet-stream')

@login_required
def ver_foto_animal(animal_id):
    """Servir la foto del animal desde la BD"""
    animal = Animal.query.get_or_404(animal_id)

    # Verificar permisos: usuario debe tener acceso a la finca o ser root
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'error': 'No tienes permisos para ver esta imagen'}), 403

    if not animal.foto_animal:
        return jsonify({'error': 'Imagen no disponible'}), 404

    # Detectar tipo de imagen para el mimetype
    mime = 'image/jpeg'
    if Image:
        try:
            img = Image.open(BytesIO(animal.foto_animal))
            fmt = (img.format or '').upper()
            if fmt == 'PNG':
                mime = 'image/png'
            elif fmt == 'GIF':
                mime = 'image/gif'
            elif fmt == 'WEBP':
                mime = 'image/webp'
        except Exception:
            pass

    return app.response_class(animal.foto_animal, mimetype=mime)

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
    """Devuelve animales filtrados por sexo con filtros opcionales.
    Filtros soportados vía query string:
      - finca_id: limitar a una finca específica (verificando acceso del usuario)
      - raza_id: limitar por raza
      - fecha_nacimiento_max: incluir animales nacidos en o antes de esta fecha (YYYY-MM-DD)
    """
    # Fincas accesibles por el usuario
    fincas_usuario = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_ids_usuario = [f.id_finca for f in fincas_usuario]

    # Leer filtros
    finca_id = request.args.get('finca_id', type=int)
    raza_id = request.args.get('raza_id', type=int)
    fecha_max_str = request.args.get('fecha_nacimiento_max', type=str)

    # Construir consulta base por sexo
    query = Animal.query.filter(Animal.sexo == sexo)

    # Filtro por fincas accesibles
    if finca_id:
        # Verificar acceso a la finca específica
        tiene_acceso = (current_user.tipo_usuario == 3) or (finca_id in finca_ids_usuario)
        if not tiene_acceso:
            return jsonify({'error': 'No tienes permisos para acceder a esta finca'}), 403
        query = query.filter(Animal.id_finca == finca_id)
    else:
        # Limitar a las fincas del usuario si no se especifica una
        if finca_ids_usuario:
            query = query.filter(Animal.id_finca.in_(finca_ids_usuario))
        else:
            return jsonify([])

    # Filtro por raza
    if raza_id:
        query = query.filter(Animal.id_raza == raza_id)

    # Filtro por fecha de nacimiento máxima
    if fecha_max_str:
        try:
            from datetime import datetime
            fecha_max = datetime.strptime(fecha_max_str, '%Y-%m-%d').date()
            query = query.filter(Animal.fecha_nacimiento <= fecha_max)
        except Exception:
            # Si la fecha no es válida, ignorar el filtro
            pass

    animales = query.all()

    animales_json = [{
        'id': animal.id_animal,
        'nombre': animal.nombre_animal,
        'finca': animal.finca.nombre_finca if animal.finca else 'Sin finca'
    } for animal in animales]

    return jsonify(animales_json)