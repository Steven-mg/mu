from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from modelo.models import db, Animal, Raza, Finca, EstadoReproductivo, UsuarioFinca, CompraAnimales, Potrero, AnimalGrupo, GrupoAnimal, DocumentoGenetico, ServiciosSalud, TipoServicioSalud, Trabajador, ServiciosSexuales, TipoServicioSexual, Productos, ProductosAnimal, RegistroPeso, CicloReproductivo, EstadoSalud, HistorialEstadoSalud, HistorialEstadoReproductivo
from sqlalchemy.orm import joinedload
from sqlalchemy import func
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
from datetime import datetime, timedelta, date
import unicodedata

def _normalize(text: str) -> str:
    """Normaliza texto a minúsculas sin acentos para comparaciones robustas."""
    try:
        s = unicodedata.normalize('NFD', (text or ''))
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.lower()
    except Exception:
        return (text or '').lower()

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
def gestion_produccion_finca(finca_id):
    """Vista dedicada de producción por finca con filtros de sexo, madurez y raza"""
    # Verificar acceso del usuario a la finca seleccionada
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver esta finca', 'danger')
        return redirect(url_for('gestion_produccion_route'))

    finca = Finca.query.get_or_404(finca_id)

    # Parámetros de filtro
    sexo = request.args.get('sexo')  # 'Hembra' | 'Macho' | None
    maduros = request.args.get('maduros', default='0')  # '0' | '1'
    raza_id = request.args.get('raza_id', type=int)

    # Razas disponibles en la finca
    try:
        razas = (db.session.query(Raza)
                 .join(Animal, Raza.id_raza == Animal.id_raza)
                 .filter(Animal.id_finca == finca_id)
                 .distinct()
                 .order_by(Raza.nombre_raza.asc())
                 .all())
    except Exception:
        razas = []

    # Consulta de animales con filtros
    query = Animal.query.filter(Animal.id_finca == finca_id)
    if sexo in ('Hembra', 'Macho'):
        query = query.filter(Animal.sexo == sexo)
    if raza_id:
        query = query.filter(Animal.id_raza == raza_id)

    animales = query.order_by(Animal.nombre_animal.asc()).all()

    # Productos disponibles y clasificación
    try:
        productos_consumibles = Productos.query.order_by(Productos.nombre_producto.asc()).all()
    except Exception:
        productos_consumibles = []

    try:
        tipos_sexuales = TipoServicioSexual.query.order_by(TipoServicioSexual.nombre_servicio.asc()).all()
    except Exception:
        tipos_sexuales = []

    def _filtra_sexuales_por_sexo(items, sexo_sel):
        s = (sexo_sel or '').strip().lower()
        if s == 'hembra':
            return [t for t in items if (getattr(t, 'aplica_a_sexo', 'ambos') or 'ambos').lower() in ['ambos', 'hembra']]
        if s == 'macho':
            return [t for t in items if (getattr(t, 'aplica_a_sexo', 'ambos') or 'ambos').lower() in ['ambos', 'macho']]
        return items

    productos_sexuales = _filtra_sexuales_por_sexo(tipos_sexuales, sexo)

    # Determinar madurez sexual por raza
    def _es_maduro(a: Animal) -> bool:
        try:
            fn = a.fecha_nacimiento
            hoy = date.today()
            meses = (hoy.year - fn.year) * 12 + (hoy.month - fn.month)
            if hoy.day < fn.day:
                meses -= 1
        except Exception:
            return False

        try:
            umbral = None
            if a.raza:
                if a.sexo == 'Hembra':
                    umbral = a.raza.madurez_sexual_hembras_meses
                else:
                    umbral = a.raza.madurez_sexual_machos_meses
            if umbral is None:
                umbral = 12
        except Exception:
            umbral = 12
        return meses >= int(umbral)

    if str(maduros) == '1':
        animales = [a for a in animales if _es_maduro(a)]

    hembras = [a for a in animales if a.sexo == 'Hembra']
    machos = [a for a in animales if a.sexo == 'Macho']

    return render_template(
        'dueño/produccion_finca.html',
        finca=finca,
        hembras=hembras,
        machos=machos,
        razas=razas,
        sexo_selected=sexo if sexo in ('Hembra', 'Macho') else 'todos',
        maduros_selected=1 if str(maduros) == '1' else 0,
        raza_selected=raza_id,
        productos_consumibles=productos_consumibles,
        productos_sexuales=productos_sexuales,
    )

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

    # Razas presentes en la finca (para filtro en la UI)
    try:
        razas = (db.session.query(Raza)
                 .join(Animal, Raza.id_raza == Animal.id_raza)
                 .filter(Animal.id_finca == finca_id)
                 .distinct()
                 .order_by(Raza.nombre_raza.asc())
                 .all())
    except Exception:
        razas = []

    return render_template('dueño/ver_animales_finca.html', finca=finca, animales=animales, razas=razas)

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
def consumo_animal(animal_id):
    """Registrar productos para un animal: pestañas Sexuales y Consumibles."""
    animal = Animal.query.get_or_404(animal_id)

    from forms.consumo_form import ConsumoProductoForm
    # Form para consumibles (carne, leche, estiércol, animal vivo)
    form_consumo = ConsumoProductoForm()
    # Form para productos sexuales (semen, embriones)
    form_sexualprod = ConsumoProductoForm()

    sexo = (animal.sexo or '').lower()

    # Helpers de contexto: madurez y lactancia
    def _es_maduro_local(a: Animal) -> bool:
        # Calcular edad en meses y comparar con umbral de la raza
        try:
            fn = a.fecha_nacimiento
            hoy = date.today()
            meses = (hoy.year - fn.year) * 12 + (hoy.month - fn.month)
            if hoy.day < fn.day:
                meses -= 1
        except Exception:
            return False

        try:
            umbral = None
            if a.raza:
                umbral = a.raza.madurez_sexual_hembras_meses if a.sexo == 'Hembra' else a.raza.madurez_sexual_machos_meses
            if umbral is None:
                umbral = 12
        except Exception:
            umbral = 12
        return meses >= int(umbral)

    def _esta_lactando(a: Animal) -> bool:
        # Ciclo activo en lactancia o estado reproductivo lactancia
        try:
            activo = next((cr for cr in a.ciclos_reproductivos if not cr.fecha_fin), None)
            if activo and (activo.tipo_ciclo or '').lower() == 'lactancia':
                return True
        except Exception:
            pass
        desc = (getattr(a.estado_reproductivo, 'descripcion', '') or '').lower()
        return desc == 'lactancia'

    # Filtro por contexto (sexo + estado) según nombre del producto
    def permitido_por_contexto(nombre: str) -> bool:
        n = _normalize(nombre)
        if 'semen' in n:
            # Solo macho maduro
            return sexo == 'macho' and _es_maduro_local(animal)
        if 'embrion' in n:
            # Solo hembra madura
            return sexo == 'hembra' and _es_maduro_local(animal)
        if 'leche' in n:
            # Solo hembra en lactancia
            return sexo == 'hembra' and _esta_lactando(animal)
        return True

    try:
        todos = Productos.query.order_by(Productos.nombre_producto.asc()).all()
    except Exception:
        todos = []

    # Helpers de detección por nombre con sinónimos
    def es_sexual(nombre: str) -> bool:
        n = _normalize(nombre)
        # Cubrir semen/embrion y sinónimos frecuentes (pajuela/pajilla, embri*)
        return any(k in n for k in ['semen', 'embrion', 'embri', 'pajuela', 'pajilla'])

    def es_consumible(nombre: str) -> bool:
        n = _normalize(nombre)
        # Productos de consumo habituales
        return any(k in n for k in ['carne', 'leche', 'estiercol', 'animal'])

    # División por categorías usando los helpers
    consumibles = [p for p in todos if es_consumible(p.nombre_producto)]
    sexuales = [p for p in todos if es_sexual(p.nombre_producto)]

    # Aplicar filtros por contexto
    consumibles = [p for p in consumibles if permitido_por_contexto(p.nombre_producto)]
    sexuales = [p for p in sexuales if permitido_por_contexto(p.nombre_producto)]

    # Asignar choices básicos (solo para validación); el select se renderiza manual para agregar data-tipo
    form_consumo.id_producto.choices = [(p.id_producto, p.nombre_producto) for p in consumibles]
    form_sexualprod.id_producto.choices = [(p.id_producto, p.nombre_producto) for p in sexuales]

    # Procesamiento de POST
    if request.method == 'POST':
        form_name = request.form.get('form_name')
        if form_name == 'consumible':
            if form_consumo.validate_on_submit():
                # Validación adicional por contexto
                prod = Productos.query.get(form_consumo.id_producto.data)
                # Validar que sea consumible y que aplique al contexto
                if not prod or not es_consumible(getattr(prod, 'nombre_producto', '')) or not permitido_por_contexto(getattr(prod, 'nombre_producto', '')):
                    flash('Este producto no aplica al sexo/estado del animal.', 'warning')
                    return redirect(url_for('animal_consumo_route', animal_id=animal_id))

                nuevo = ProductosAnimal(
                    id_producto=form_consumo.id_producto.data,
                    id_animal=animal_id,
                    cantidad=form_consumo.cantidad.data,
                    fecha=form_consumo.fecha.data,
                    notas_produccion=form_consumo.notas_produccion.data,
                )
                db.session.add(nuevo)
                db.session.commit()
                flash('Producto consumible registrado', 'success')
                return redirect(url_for('animal_consumo_route', animal_id=animal_id))
            else:
                flash('Revise los campos para registrar el consumible.', 'warning')
        elif form_name == 'sexual_producto':
            if form_sexualprod.validate_on_submit():
                # Validación adicional por contexto
                prod = Productos.query.get(form_sexualprod.id_producto.data)
                # Validar que sea sexual y que aplique al contexto
                if not prod or not es_sexual(getattr(prod, 'nombre_producto', '')) or not permitido_por_contexto(getattr(prod, 'nombre_producto', '')):
                    flash('Este producto sexual no aplica al sexo/estado del animal.', 'warning')
                    return redirect(url_for('animal_consumo_route', animal_id=animal_id))

                nuevo = ProductosAnimal(
                    id_producto=form_sexualprod.id_producto.data,
                    id_animal=animal_id,
                    cantidad=form_sexualprod.cantidad.data,
                    fecha=form_sexualprod.fecha.data,
                    notas_produccion=form_sexualprod.notas_produccion.data,
                )
                db.session.add(nuevo)
                db.session.commit()
                flash('Producto sexual registrado', 'success')
                return redirect(url_for('animal_consumo_route', animal_id=animal_id))
            else:
                flash('Revise los campos para registrar el producto sexual.', 'warning')

    return render_template(
        'dueño/animal_consumo.html',
        animal=animal,
        form_consumo=form_consumo,
        form_sexualprod=form_sexualprod,
        productos_consumibles=consumibles,
        productos_sexuales=sexuales,
    )

@login_required
def biologicos_animal(animal_id):
    """Registrar biológicos (servicios sexuales, semen, embriones) para un animal"""
    animal = Animal.query.get_or_404(animal_id)

    from forms.servicio_sexual_form import ServicioSexualForm
    from forms.consumo_form import ConsumoProductoForm
    form_sexual = ServicioSexualForm()
    form_semen = ServicioSexualForm()
    form_embrion = ServicioSexualForm()
    form_producto = ConsumoProductoForm()

    sexo_animal = (animal.sexo or '').lower()

    # Listar trabajadores del dueño actual con rol veterinario y estado activo
    vets = Trabajador.query.filter(
        Trabajador.id_jefe == current_user.id,
        Trabajador.rol == 'veterinario',
        Trabajador.estado == 'activo'
    ).all()
    vet_choices = [(v.id_trabajador, f"{v.nombre} {v.apellido}") for v in vets]
    form_sexual.id_veterinario.choices = vet_choices
    form_semen.id_veterinario.choices = vet_choices
    form_embrion.id_veterinario.choices = vet_choices

    # Construir choices de productos biológicos (Semen / Embriones) con sinónimos
    try:
        _todos = Productos.query.order_by(Productos.nombre_producto.asc()).all()
        def _es_sexual(nombre: str) -> bool:
            n = _normalize(nombre)
            return any(k in n for k in ['semen', 'embrion', 'embri', 'pajuela', 'pajilla'])
        productos_bio = [p for p in _todos if _es_sexual(p.nombre_producto)]
    except Exception:
        productos_bio = []
    form_producto.id_producto.choices = [(p.id_producto, p.nombre_producto) for p in productos_bio]

    # Helpers de filtrado por sexo y nombre
    def filtrar_por_nombre_y_sexo(tipos, sexo):
        s = (sexo or '').lower()
        if s == 'macho':
            return [t for t in tipos if (getattr(t, 'aplica_a_sexo', 'ambos') or 'ambos').lower() in ['ambos', 'macho']]
        if s == 'hembra':
            return [t for t in tipos if (getattr(t, 'aplica_a_sexo', 'ambos') or 'ambos').lower() in ['ambos', 'hembra']]
        return tipos

    def es_inmaduro_sexual(an):
        try:
            if getattr(an, 'id_estado_reprod', None) == 15:
                return True
            if getattr(an, 'estado_reprod', None) and (getattr(an.estado_reprod, 'descripcion', '') or '').lower() == 'inmaduro':
                return True
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
            return False
        return False

    inmaduro = es_inmaduro_sexual(animal)

    # Construir grupos de tipos
    tipos = TipoServicioSexual.query.all()
    tipos_sexual_general = filtrar_por_nombre_y_sexo([t for t in tipos if 'semen' not in (t.nombre_servicio or '').lower() and 'embri' not in (t.nombre_servicio or '').lower()], sexo_animal)
    tipos_semen = filtrar_por_nombre_y_sexo([t for t in tipos if 'semen' in (t.nombre_servicio or '').lower()], sexo_animal)
    tipos_embrion = filtrar_por_nombre_y_sexo([t for t in tipos if 'embri' in (t.nombre_servicio or '').lower()], sexo_animal)

    form_sexual.id_servicioanimal.choices = [(t.id_servicio, t.nombre_servicio) for t in tipos_sexual_general]
    form_semen.id_servicioanimal.choices = [(t.id_servicio, t.nombre_servicio) for t in tipos_semen]
    form_embrion.id_servicioanimal.choices = [(t.id_servicio, t.nombre_servicio) for t in tipos_embrion]

    # Procesamiento de POST por pestaña
    if request.method == 'POST':
        form_name = request.form.get('form_name')
        target_form = None
        if form_name == 'sexual':
            target_form = form_sexual
        elif form_name == 'semen':
            target_form = form_semen
        elif form_name == 'embrion':
            target_form = form_embrion
        elif form_name == 'biologico_producto':
            # Guardar en productos_animal
            if form_producto.validate_on_submit():
                nuevo = ProductosAnimal(
                    id_producto=form_producto.id_producto.data,
                    id_animal=animal_id,
                    cantidad=form_producto.cantidad.data,
                    fecha=form_producto.fecha.data,
                    notas_produccion=form_producto.notas_produccion.data,
                )
                db.session.add(nuevo)
                db.session.commit()
                flash('Producto biológico guardado', 'success')
                return redirect(url_for('animal_biologicos_route', animal_id=animal_id))
            else:
                flash('Revise los campos para registrar el producto biológico.', 'warning')

        if target_form and target_form.validate_on_submit():
            tipo_sexual_sel = TipoServicioSexual.query.get(target_form.id_servicioanimal.data)
            aplica = (getattr(tipo_sexual_sel, 'aplica_a_sexo', 'ambos') or 'ambos').lower() if tipo_sexual_sel else 'ambos'
            if inmaduro:
                flash('Animal inmaduro: revise que el servicio sea acorde a la edad/raza.', 'warning')
            if sexo_animal == 'macho' and aplica == 'hembra':
                flash('Este servicio aplica solo a hembras.', 'warning')
                return redirect(url_for('animal_biologicos_route', animal_id=animal_id))
            if sexo_animal == 'hembra' and aplica == 'macho':
                flash('Este servicio aplica solo a machos.', 'warning')
                return redirect(url_for('animal_biologicos_route', animal_id=animal_id))
            nuevo = ServiciosSexuales(
                id_servicioanimal=target_form.id_servicioanimal.data,
                id_animal=animal_id,
                id_veterinario=target_form.id_veterinario.data,
                fecha_servicio=target_form.fecha_servicio.data,
                fecha_proximo=target_form.fecha_proximo.data,
                notas_servicio=target_form.notas_servicio.data,
                costo_total=target_form.costo_total.data,
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Servicio biológico registrado', 'success')
            return redirect(url_for('animal_biologicos_route', animal_id=animal_id))
        elif target_form:
            flash('Revise los campos del formulario seleccionado.', 'warning')

    return render_template(
        'dueño/animal_biologicos.html',
        animal=animal,
        form_sexual=form_sexual,
        form_semen=form_semen,
        form_embrion=form_embrion,
        form_producto=form_producto,
        inmaduro=inmaduro,
        sexo_animal=animal.sexo,
    )

@login_required
def ver_produccion_animal(animal_id):
    """Listar registros de ProductosAnimal para un animal específico, con filtro y métricas."""
    animal = Animal.query.get_or_404(animal_id)

    # Selector de producto
    producto_id = request.args.get('producto_id', type=int)
    try:
        productos_disponibles = (
            db.session.query(Productos)
            .join(ProductosAnimal, Productos.id_producto == ProductosAnimal.id_producto)
            .filter(ProductosAnimal.id_animal == animal_id)
            .distinct()
            .order_by(Productos.nombre_producto.asc())
            .all()
        )
    except Exception:
        productos_disponibles = []

    # Producciones con filtro
    base_q = (
        ProductosAnimal.query
        .options(joinedload(ProductosAnimal.producto))
        .filter(ProductosAnimal.id_animal == animal_id)
    )
    if producto_id:
        base_q = base_q.filter(ProductosAnimal.id_producto == producto_id)
    producciones = base_q.order_by(ProductosAnimal.fecha.desc()).all()

    # Métricas para leche por día: agregación por fecha
    def _es_leche(nombre: str) -> bool:
        n = (nombre or '').lower()
        return 'leche' in n

    # Obtener todas las producciones del animal para detectar leche
    todas_prods = (
        ProductosAnimal.query.options(joinedload(ProductosAnimal.producto))
        .filter(ProductosAnimal.id_animal == animal_id)
        .order_by(ProductosAnimal.fecha.asc())
        .all()
    )

    from collections import defaultdict
    leche_por_dia = defaultdict(float)
    for p in todas_prods:
        if p.producto and _es_leche(p.producto.nombre_producto) and p.fecha:
            try:
                key = p.fecha.strftime('%Y-%m-%d')
            except Exception:
                key = str(p.fecha)
            leche_por_dia[key] += float(p.cantidad or 0)

    # Ordenar por fecha
    labels_leche = sorted(leche_por_dia.keys())
    values_leche = [round(leche_por_dia[d], 2) for d in labels_leche]

    # Umbrales por raza
    umbral_min = None
    umbral_norm = None
    try:
        if animal.raza:
            umbral_min = float(animal.raza.produccion_leche_dia_min or 0)
            umbral_norm = float(animal.raza.produccion_leche_dia_max or 0)
    except Exception:
        umbral_min = None
        umbral_norm = None

    # Estado de producción reciente (promedio últimos 7 días)
    avg_7d = None
    estado_msg = None
    estado_tipo = 'normal'
    if labels_leche:
        try:
            # Tomar últimos 7 días ordenados
            ultimos = values_leche[-7:] if len(values_leche) > 7 else values_leche
            if ultimos:
                avg_7d = round(sum(ultimos) / len(ultimos), 2)
                if umbral_min is not None and avg_7d < umbral_min:
                    estado_tipo = 'bajo'
                    estado_msg = f"Promedio 7d {avg_7d} por debajo del mínimo ({umbral_min})."
                elif umbral_norm is not None and avg_7d > umbral_norm:
                    estado_tipo = 'alto'
                    estado_msg = f"Promedio 7d {avg_7d} por encima del normal ({umbral_norm})."
                else:
                    estado_tipo = 'normal'
                    estado_msg = f"Promedio 7d {avg_7d} dentro del rango normal ({umbral_min}–{umbral_norm})."
        except Exception:
            estado_msg = None

    # --- Integración de formularios: peso, ciclo reproductivo y estado de salud ---
    try:
        from forms.peso_form import RegistroPesoForm
        from forms.ciclo_reproductivo_form import CicloReproductivoForm, CerrarCicloForm
        from forms.estado_salud_form import EstadoSaludForm
    except Exception:
        RegistroPesoForm = None
        CicloReproductivoForm = None
        CerrarCicloForm = None
        EstadoSaludForm = None

    form_peso = RegistroPesoForm() if RegistroPesoForm else None
    form_ciclo = CicloReproductivoForm() if CicloReproductivoForm else None
    form_cerrar_ciclo = CerrarCicloForm() if CerrarCicloForm else None
    form_salud = EstadoSaludForm() if EstadoSaludForm else None

    # Cargar choices de salud
    estados_salud_choices = []
    if form_salud:
        try:
            estados_salud = EstadoSalud.query.order_by(EstadoSalud.descripcion.asc()).all()
            estados_salud_choices = [(e.id_estado_salud, e.descripcion) for e in estados_salud]
            form_salud.id_estado_salud.choices = estados_salud_choices
        except Exception:
            form_salud.id_estado_salud.choices = []

    # Ciclo activo y últimos registros
    try:
        ciclo_activo = CicloReproductivo.query.filter_by(id_animal=animal.id_animal, fecha_fin=None).order_by(CicloReproductivo.fecha_inicio.desc()).first()
    except Exception:
        ciclo_activo = None
    try:
        ciclos_previos = CicloReproductivo.query.filter_by(id_animal=animal.id_animal).order_by(CicloReproductivo.fecha_inicio.desc()).limit(10).all()
    except Exception:
        ciclos_previos = []
    try:
        registros_peso = RegistroPeso.query.filter_by(id_animal=animal.id_animal).order_by(RegistroPeso.fecha_registro.desc()).limit(10).all()
    except Exception:
        registros_peso = []
    try:
        historial_salud = HistorialEstadoSalud.query.options(joinedload(HistorialEstadoSalud.estado_salud)).filter_by(id_animal=animal.id_animal).order_by(HistorialEstadoSalud.fecha_cambio.desc()).limit(10).all()
        estado_salud_actual = historial_salud[0].estado_salud.descripcion if historial_salud and historial_salud[0].estado_salud else None
    except Exception:
        historial_salud = []
        estado_salud_actual = None

    # Ajustar dinámicamente las opciones del tipo de ciclo según catálogo de estados
    if form_ciclo:
        try:
            estados_db = EstadoReproductivo.query.order_by(EstadoReproductivo.descripcion.asc()).all()
            def _find_label(candidates: set) -> str:
                for e in estados_db:
                    if _normalize(e.descripcion) in candidates:
                        return e.descripcion
                return None
            form_ciclo.tipo_ciclo.choices = [
                ('celo', _find_label({'celo', 'en celo'}) or 'Celo'),
                ('gestación', _find_label({'gestacion', 'preniez', 'preñez', 'prenada', 'preñada'}) or 'Gestación'),
                ('lactancia', _find_label({'lactancia', 'lactacion'}) or 'Lactancia'),
                ('descanso', _find_label({'descanso', 'secado'}) or 'Descanso'),
            ]
        except Exception:
            form_ciclo.tipo_ciclo.choices = [
                ('celo', 'Celo'),
                ('gestación', 'Gestación'),
                ('lactancia', 'Lactancia'),
                ('descanso', 'Descanso'),
            ]

    # Ajustar dinámicamente las opciones del tipo de ciclo según catálogo de estados
    if form_ciclo:
        try:
            estados_db = EstadoReproductivo.query.order_by(EstadoReproductivo.descripcion.asc()).all()
            def _find_label(candidates: set) -> str:
                for e in estados_db:
                    if _normalize(e.descripcion) in candidates:
                        return e.descripcion
                return None
            form_ciclo.tipo_ciclo.choices = [
                ('celo', _find_label({'celo', 'en celo'}) or 'Celo'),
                ('gestación', _find_label({'gestacion', 'preniez', 'preñez', 'prenada', 'preñada'}) or 'Gestación'),
                ('lactancia', _find_label({'lactancia', 'lactacion'}) or 'Lactancia'),
                ('descanso', _find_label({'descanso', 'secado'}) or 'Descanso'),
            ]
        except Exception:
            form_ciclo.tipo_ciclo.choices = [
                ('celo', 'Celo'),
                ('gestación', 'Gestación'),
                ('lactancia', 'Lactancia'),
                ('descanso', 'Descanso'),
            ]

    def _buscar_estado_reprod_por_desc(desc_lower: str):
        # Coincidencia robusta con sinónimos del catálogo
        t = _normalize(desc_lower)
        key_map = {
            'preniez': 'gestacion', 'preñez': 'gestacion', 'prenada': 'gestacion', 'preñada': 'gestacion', 'gestacion': 'gestacion',
            'lactancia': 'lactancia', 'lactacion': 'lactancia',
            'celo': 'celo', 'en celo': 'celo',
            'descanso': 'descanso', 'secado': 'descanso',
        }
        key = key_map.get(t, t)
        candidates_map = {
            'gestacion': {'gestacion', 'preniez', 'preñez', 'prenada', 'preñada'},
            'lactancia': {'lactancia', 'lactacion'},
            'celo': {'celo', 'en celo'},
            'descanso': {'descanso', 'secado'},
        }
        candidates = candidates_map.get(key, {key})
        try:
            estados = EstadoReproductivo.query.all()
            for e in estados:
                if _normalize(e.descripcion) in candidates:
                    return e
        except Exception:
            return None
        return None

    if request.method == 'POST':
        target = request.form.get('form_name')
        if target == 'peso' and form_peso and form_peso.validate_on_submit():
            try:
                nuevo = RegistroPeso(
                    id_animal=animal.id_animal,
                    fecha_registro=form_peso.fecha_registro.data,
                    peso=form_peso.peso.data,
                    tipo_momento=form_peso.tipo_momento.data,
                    notas=form_peso.notas.data,
                )
                db.session.add(nuevo)
                db.session.commit()
                registrar_actividad(current_user.id, f"Registró peso para {animal.nombre_animal}")
                flash('Peso registrado correctamente.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error registrando peso: {e}', 'danger')
            return redirect(url_for('animal_produccion_route', animal_id=animal_id))

        if target == 'ciclo_nuevo' and form_ciclo and form_ciclo.validate_on_submit():
            if ciclo_activo:
                flash('Ya existe un ciclo activo. Cierre el actual antes de iniciar uno nuevo.', 'warning')
                return redirect(url_for('animal_produccion_route', animal_id=animal_id))
            try:
                nuevo_ciclo = CicloReproductivo(
                    id_animal=animal.id_animal,
                    fecha_inicio=form_ciclo.fecha_inicio.data,
                    tipo_ciclo=form_ciclo.tipo_ciclo.data,
                    duracion_esperada=form_ciclo.duracion_esperada.data,
                    notas=form_ciclo.notas.data,
                )
                db.session.add(nuevo_ciclo)

                estado_match = _buscar_estado_reprod_por_desc((form_ciclo.tipo_ciclo.data or '').lower())
                if estado_match:
                    db.session.add(HistorialEstadoReproductivo(
                        id_animal=animal.id_animal,
                        id_estado_reprod=estado_match.id_estado_reprod,
                        observaciones=f"Inicio de ciclo {form_ciclo.tipo_ciclo.data}"
                    ))
                    try:
                        if (animal.sexo or '').lower() == 'hembra':
                            animal.id_estado_reprod = estado_match.id_estado_reprod
                    except Exception:
                        pass
                else:
                    flash('No se encontró un estado reproductivo correspondiente al tipo de ciclo. Verifique que exista "Gestación", "Lactancia", "Celo" o "Descanso" en el catálogo.', 'warning')

                db.session.commit()
                registrar_actividad(current_user.id, f"Inició ciclo {form_ciclo.tipo_ciclo.data} en {animal.nombre_animal}")
                flash('Ciclo reproductivo iniciado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error iniciando ciclo: {e}', 'danger')
            return redirect(url_for('animal_produccion_route', animal_id=animal_id))

        if target == 'ciclo_cerrar' and form_cerrar_ciclo and form_cerrar_ciclo.validate_on_submit():
            if not ciclo_activo:
                flash('No existe un ciclo activo para cerrar.', 'warning')
                return redirect(url_for('animal_produccion_route', animal_id=animal_id))
            try:
                ciclo_activo.fecha_fin = form_cerrar_ciclo.fecha_fin.data
                if form_cerrar_ciclo.notas_fin.data:
                    ciclo_activo.notas = (ciclo_activo.notas or '') + f"\nCierre: {form_cerrar_ciclo.notas_fin.data}"

                estado_descanso = _buscar_estado_reprod_por_desc('descanso')
                if estado_descanso:
                    db.session.add(HistorialEstadoReproductivo(
                        id_animal=animal.id_animal,
                        id_estado_reprod=estado_descanso.id_estado_reprod,
                        observaciones=f"Cierre de ciclo: {ciclo_activo.tipo_ciclo}"
                    ))
                    try:
                        if (animal.sexo or '').lower() == 'hembra':
                            animal.id_estado_reprod = estado_descanso.id_estado_reprod
                    except Exception:
                        pass

                db.session.commit()
                registrar_actividad(current_user.id, f"Cerró ciclo {ciclo_activo.tipo_ciclo} en {animal.nombre_animal}")
                flash('Ciclo reproductivo cerrado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error cerrando ciclo: {e}', 'danger')
            return redirect(url_for('animal_produccion_route', animal_id=animal_id))

        if target == 'salud_estado' and form_salud and form_salud.validate_on_submit():
            try:
                nuevo_hist = HistorialEstadoSalud(
                    id_animal=animal.id_animal,
                    id_estado_salud=form_salud.id_estado_salud.data,
                    observaciones=form_salud.observaciones.data,
                )
                db.session.add(nuevo_hist)
                db.session.commit()
                registrar_actividad(current_user.id, f"Actualizó estado de salud de {animal.nombre_animal}")
                flash('Estado de salud actualizado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error actualizando estado de salud: {e}', 'danger')
            return redirect(url_for('animal_produccion_route', animal_id=animal_id))

    unidad_map = {1: 'litros', 2: 'libras', 3: 'unidades'}

    return render_template(
        'dueño/animal_produccion.html',
        animal=animal,
        producciones=producciones,
        unidad_map=unidad_map,
        productos_disponibles=productos_disponibles,
        producto_id_selected=producto_id or 0,
        leche_labels=labels_leche,
        leche_values=values_leche,
        leche_umbral_min=umbral_min,
        leche_umbral_norm=umbral_norm,
        leche_avg_7d=avg_7d,
        leche_estado_tipo=estado_tipo,
        leche_estado_msg=estado_msg,
        # UI extendida
        form_peso=form_peso,
        registros_peso=registros_peso,
        form_ciclo=form_ciclo,
        form_cerrar_ciclo=form_cerrar_ciclo,
        ciclo_activo=ciclo_activo,
        ciclos_previos=ciclos_previos,
        form_salud=form_salud,
        historial_salud=historial_salud,
        estado_salud_actual=estado_salud_actual,
        estados_salud_choices=estados_salud_choices,
    )

# Página dedicada solo a gráficos
@login_required
def ver_graficos_animal(animal_id):
    """Vista dedicada para gráficos del animal (sin tabla de producción)."""
    animal = Animal.query.get_or_404(animal_id)

    # Agregación: producción de leche por día
    def _es_leche(nombre: str) -> bool:
        n = (nombre or '').lower()
        return 'leche' in n

    try:
        todas_prods = (
            ProductosAnimal.query.options(joinedload(ProductosAnimal.producto))
            .filter(ProductosAnimal.id_animal == animal_id)
            .order_by(ProductosAnimal.fecha.asc())
            .all()
        )
    except Exception:
        todas_prods = []

    from collections import defaultdict
    leche_por_dia = defaultdict(float)
    for p in todas_prods:
        if p.producto and _es_leche(p.producto.nombre_producto) and p.fecha:
            try:
                key = p.fecha.strftime('%Y-%m-%d')
            except Exception:
                key = str(p.fecha)
            leche_por_dia[key] += float(p.cantidad or 0)

    labels_leche = sorted(leche_por_dia.keys())
    values_leche = [round(leche_por_dia[d], 2) for d in labels_leche]

    # Umbrales por raza
    umbral_min = None
    umbral_norm = None
    try:
        if animal.raza:
            umbral_min = float(animal.raza.produccion_leche_dia_min or 0)
            umbral_norm = float(animal.raza.produccion_leche_dia_max or 0)
    except Exception:
        umbral_min = None
        umbral_norm = None

    # Estado de producción reciente (promedio últimos 7 días)
    avg_7d = None
    estado_msg = None
    estado_tipo = 'normal'
    if labels_leche:
        try:
            ultimos = values_leche[-7:] if len(values_leche) > 7 else values_leche
            if ultimos:
                avg_7d = round(sum(ultimos) / len(ultimos), 2)
                if umbral_min is not None and avg_7d < umbral_min:
                    estado_tipo = 'bajo'
                    estado_msg = f"Promedio 7d {avg_7d} por debajo del mínimo ({umbral_min})."
                elif umbral_norm is not None and avg_7d > umbral_norm:
                    estado_tipo = 'alto'
                    estado_msg = f"Promedio 7d {avg_7d} por encima del normal ({umbral_norm})."
                else:
                    estado_tipo = 'normal'
                    estado_msg = f"Promedio 7d {avg_7d} dentro del rango normal ({umbral_min}–{umbral_norm})."
        except Exception:
            estado_msg = None

    return render_template(
        'dueño/animal_graficos.html',
        animal=animal,
        leche_labels=labels_leche,
        leche_values=values_leche,
        leche_umbral_min=umbral_min,
        leche_umbral_norm=umbral_norm,
        leche_avg_7d=avg_7d,
        leche_estado_tipo=estado_tipo,
        leche_estado_msg=estado_msg,
    )

# Páginas dedicadas solicitadas: Peso, Ciclo y Salud
@login_required
def ver_peso_animal(animal_id):
    """Página dedicada para registrar peso y ver historial de un animal."""
    animal = Animal.query.get_or_404(animal_id)

    # Validar acceso a la finca del animal
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este animal', 'danger')
        return redirect(url_for('gestion_animales'))

    try:
        from forms.peso_form import RegistroPesoForm
    except Exception:
        RegistroPesoForm = None

    form_peso = RegistroPesoForm() if RegistroPesoForm else None

    try:
        registros_peso = RegistroPeso.query.filter_by(id_animal=animal.id_animal).order_by(RegistroPeso.fecha_registro.desc()).limit(50).all()
    except Exception:
        registros_peso = []

    peso_actual = None
    try:
        if registros_peso:
            peso_actual = float(registros_peso[0].peso or 0)
    except Exception:
        peso_actual = None

    if request.method == 'POST' and form_peso and form_peso.validate_on_submit():
        try:
            nuevo = RegistroPeso(
                id_animal=animal.id_animal,
                fecha_registro=form_peso.fecha_registro.data,
                peso=form_peso.peso.data,
                tipo_momento=form_peso.tipo_momento.data,
                notas=form_peso.notas.data,
            )
            db.session.add(nuevo)
            db.session.commit()
            registrar_actividad(current_user.id, f"Registró peso para {animal.nombre_animal}")
            flash('Peso registrado correctamente.', 'success')
            return redirect(url_for('animal_peso_route', animal_id=animal_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error registrando peso: {e}', 'danger')

    return render_template(
        'dueño/animal_peso.html',
        animal=animal,
        form_peso=form_peso,
        registros_peso=registros_peso,
        peso_actual=peso_actual,
    )

@login_required
def ver_ciclo_animal(animal_id):
    """Página dedicada para administrar el ciclo reproductivo y ver historial."""
    animal = Animal.query.get_or_404(animal_id)

    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este animal', 'danger')
        return redirect(url_for('gestion_animales'))

    try:
        from forms.ciclo_reproductivo_form import CicloReproductivoForm, CerrarCicloForm
    except Exception:
        CicloReproductivoForm = None
        CerrarCicloForm = None

    form_ciclo = CicloReproductivoForm() if CicloReproductivoForm else None
    form_cerrar_ciclo = CerrarCicloForm() if CerrarCicloForm else None

    # Ajustar dinámicamente las opciones del tipo de ciclo según catálogo de estados
    if form_ciclo:
        try:
            estados_db = EstadoReproductivo.query.order_by(EstadoReproductivo.descripcion.asc()).all()
            def _find_label(candidates: set) -> str:
                for e in estados_db:
                    if _normalize(e.descripcion) in candidates:
                        return e.descripcion
                return None
            form_ciclo.tipo_ciclo.choices = [
                ('celo', _find_label({'celo', 'en celo'}) or 'Celo'),
                ('gestación', _find_label({'gestacion', 'preniez', 'preñez', 'prenada', 'preñada'}) or 'Gestación'),
                ('lactancia', _find_label({'lactancia', 'lactacion'}) or 'Lactancia'),
                ('descanso', _find_label({'descanso', 'secado'}) or 'Descanso'),
            ]
        except Exception:
            form_ciclo.tipo_ciclo.choices = [
                ('celo', 'Celo'),
                ('gestación', 'Gestación'),
                ('lactancia', 'Lactancia'),
                ('descanso', 'Descanso'),
            ]

    try:
        ciclo_activo = CicloReproductivo.query.filter_by(id_animal=animal.id_animal, fecha_fin=None).order_by(CicloReproductivo.fecha_inicio.desc()).first()
    except Exception:
        ciclo_activo = None
    try:
        ciclos_previos = CicloReproductivo.query.filter_by(id_animal=animal.id_animal).order_by(CicloReproductivo.fecha_inicio.desc()).limit(50).all()
    except Exception:
        ciclos_previos = []

    def _normalize(text: str) -> str:
        try:
            return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').lower().strip()
        except Exception:
            return (text or '').lower().strip()

    def _buscar_estado_reprod_por_desc(desc_lower: str):
        t = _normalize(desc_lower)
        key_map = {
            'preniez': 'gestacion', 'preñez': 'gestacion', 'prenada': 'gestacion', 'preñada': 'gestacion', 'gestacion': 'gestacion',
            'lactancia': 'lactancia', 'lactacion': 'lactancia',
            'celo': 'celo', 'en celo': 'celo',
            'descanso': 'descanso', 'secado': 'descanso',
        }
        key = key_map.get(t, t)
        candidates_map = {
            'gestacion': {'gestacion', 'preniez', 'preñez', 'prenada', 'preñada'},
            'lactancia': {'lactancia', 'lactacion'},
            'celo': {'celo', 'en celo'},
            'descanso': {'descanso', 'secado'},
        }
        candidates = candidates_map.get(key, {key})
        try:
            estados = EstadoReproductivo.query.all()
            for e in estados:
                if _normalize(e.descripcion) in candidates:
                    return e
        except Exception:
            return None
        return None

    if request.method == 'POST':
        target = request.form.get('form_name')
        if target == 'ciclo_nuevo' and form_ciclo and form_ciclo.validate_on_submit():
            if ciclo_activo:
                flash('Ya existe un ciclo activo. Cierre el actual antes de iniciar uno nuevo.', 'warning')
                return redirect(url_for('animal_ciclo_route', animal_id=animal_id))
            try:
                nuevo_ciclo = CicloReproductivo(
                    id_animal=animal.id_animal,
                    fecha_inicio=form_ciclo.fecha_inicio.data,
                    tipo_ciclo=form_ciclo.tipo_ciclo.data,
                    duracion_esperada=form_ciclo.duracion_esperada.data,
                    notas=form_ciclo.notas.data,
                )
                db.session.add(nuevo_ciclo)

                estado_match = _buscar_estado_reprod_por_desc((form_ciclo.tipo_ciclo.data or '').lower())
                if estado_match:
                    db.session.add(HistorialEstadoReproductivo(
                        id_animal=animal.id_animal,
                        id_estado_reprod=estado_match.id_estado_reprod,
                        observaciones=f"Inicio de ciclo {form_ciclo.tipo_ciclo.data}"
                    ))
                    try:
                        if (animal.sexo or '').lower() == 'hembra':
                            animal.id_estado_reprod = estado_match.id_estado_reprod
                    except Exception:
                        pass
                else:
                    flash('No se encontró un estado reproductivo correspondiente al tipo de ciclo. Verifique que exista "Gestación", "Lactancia", "Celo" o "Descanso" en el catálogo.', 'warning')

                db.session.commit()
                registrar_actividad(current_user.id, f"Inició ciclo {form_ciclo.tipo_ciclo.data} en {animal.nombre_animal}")
                flash('Ciclo reproductivo iniciado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error iniciando ciclo: {e}', 'danger')
            return redirect(url_for('animal_ciclo_route', animal_id=animal_id))

        if target == 'ciclo_cerrar' and form_cerrar_ciclo and form_cerrar_ciclo.validate_on_submit():
            if not ciclo_activo:
                flash('No existe un ciclo activo para cerrar.', 'warning')
                return redirect(url_for('animal_ciclo_route', animal_id=animal_id))
            try:
                ciclo_activo.fecha_fin = form_cerrar_ciclo.fecha_fin.data
                if form_cerrar_ciclo.notas_fin.data:
                    ciclo_activo.notas = (ciclo_activo.notas or '') + f"\nCierre: {form_cerrar_ciclo.notas_fin.data}"

                estado_descanso = _buscar_estado_reprod_por_desc('descanso')
                if estado_descanso:
                    db.session.add(HistorialEstadoReproductivo(
                        id_animal=animal.id_animal,
                        id_estado_reprod=estado_descanso.id_estado_reprod,
                        observaciones=f"Cierre de ciclo: {ciclo_activo.tipo_ciclo}"
                    ))
                    try:
                        if (animal.sexo or '').lower() == 'hembra':
                            animal.id_estado_reprod = estado_descanso.id_estado_reprod
                    except Exception:
                        pass

                db.session.commit()
                registrar_actividad(current_user.id, f"Cerró ciclo {ciclo_activo.tipo_ciclo} en {animal.nombre_animal}")
                flash('Ciclo reproductivo cerrado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error cerrando ciclo: {e}', 'danger')
            return redirect(url_for('animal_ciclo_route', animal_id=animal_id))

    return render_template(
        'dueño/animal_ciclo.html',
        animal=animal,
        form_ciclo=form_ciclo,
        form_cerrar_ciclo=form_cerrar_ciclo,
        ciclo_activo=ciclo_activo,
        ciclos_previos=ciclos_previos,
    )

@login_required
def ver_salud_animal(animal_id):
    """Página dedicada para actualizar estado de salud y ver historial."""
    animal = Animal.query.get_or_404(animal_id)

    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=animal.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este animal', 'danger')
        return redirect(url_for('gestion_animales'))

    try:
        from forms.estado_salud_form import EstadoSaludForm
    except Exception:
        EstadoSaludForm = None

    form_salud = EstadoSaludForm() if EstadoSaludForm else None

    estados_salud_choices = []
    if form_salud:
        try:
            estados_salud = EstadoSalud.query.order_by(EstadoSalud.descripcion.asc()).all()
            estados_salud_choices = [(e.id_estado_salud, e.descripcion) for e in estados_salud]
            form_salud.id_estado_salud.choices = estados_salud_choices
        except Exception:
            form_salud.id_estado_salud.choices = []

    try:
        historial_salud = HistorialEstadoSalud.query.options(joinedload(HistorialEstadoSalud.estado_salud)).filter_by(id_animal=animal.id_animal).order_by(HistorialEstadoSalud.fecha_cambio.desc()).limit(50).all()
        estado_salud_actual = historial_salud[0].estado_salud.descripcion if historial_salud and historial_salud[0].estado_salud else None
    except Exception:
        historial_salud = []
        estado_salud_actual = None

    if request.method == 'POST' and form_salud and form_salud.validate_on_submit():
        try:
            nuevo_hist = HistorialEstadoSalud(
                id_animal=animal.id_animal,
                id_estado_salud=form_salud.id_estado_salud.data,
                observaciones=form_salud.observaciones.data,
            )
            db.session.add(nuevo_hist)
            db.session.commit()
            registrar_actividad(current_user.id, f"Actualizó estado de salud de {animal.nombre_animal}")
            flash('Estado de salud actualizado.', 'success')
            return redirect(url_for('animal_salud_route', animal_id=animal_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error actualizando estado de salud: {e}', 'danger')

    return render_template(
        'dueño/animal_salud.html',
        animal=animal,
        form_salud=form_salud,
        historial_salud=historial_salud,
        estado_salud_actual=estado_salud_actual,
        estados_salud_choices=estados_salud_choices,
    )

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
    
    # --- Integración de formularios: peso, ciclo reproductivo y estado de salud ---
    try:
        from forms.peso_form import RegistroPesoForm
        from forms.ciclo_reproductivo_form import CicloReproductivoForm, CerrarCicloForm
        from forms.estado_salud_form import EstadoSaludForm
    except Exception:
        RegistroPesoForm = None
        CicloReproductivoForm = None
        CerrarCicloForm = None
        EstadoSaludForm = None

    form_peso = RegistroPesoForm() if RegistroPesoForm else None
    form_ciclo = CicloReproductivoForm() if CicloReproductivoForm else None
    form_cerrar_ciclo = CerrarCicloForm() if CerrarCicloForm else None
    form_salud = EstadoSaludForm() if EstadoSaludForm else None

    # Cargar opciones de estados de salud
    estados_salud_choices = []
    if form_salud:
        try:
            estados_salud = EstadoSalud.query.order_by(EstadoSalud.descripcion.asc()).all()
            estados_salud_choices = [(e.id_estado_salud, e.descripcion) for e in estados_salud]
            form_salud.id_estado_salud.choices = estados_salud_choices
        except Exception:
            form_salud.id_estado_salud.choices = []

    # Ciclo activo y últimas entradas
    try:
        ciclo_activo = CicloReproductivo.query.filter_by(id_animal=animal.id_animal, fecha_fin=None).order_by(CicloReproductivo.fecha_inicio.desc()).first()
    except Exception:
        ciclo_activo = None
    try:
        ciclos_previos = CicloReproductivo.query.filter_by(id_animal=animal.id_animal).order_by(CicloReproductivo.fecha_inicio.desc()).limit(10).all()
    except Exception:
        ciclos_previos = []
    try:
        registros_peso = RegistroPeso.query.filter_by(id_animal=animal.id_animal).order_by(RegistroPeso.fecha_registro.desc()).limit(10).all()
    except Exception:
        registros_peso = []
    try:
        historial_salud = HistorialEstadoSalud.query.options(joinedload(HistorialEstadoSalud.estado_salud)).filter_by(id_animal=animal.id_animal).order_by(HistorialEstadoSalud.fecha_cambio.desc()).limit(10).all()
        estado_salud_actual = historial_salud[0].estado_salud.descripcion if historial_salud and historial_salud[0].estado_salud else None
    except Exception:
        historial_salud = []
        estado_salud_actual = None

    def _buscar_estado_reprod_por_desc(desc_lower: str):
        t = _normalize(desc_lower)
        key_map = {
            'preniez': 'gestacion', 'preñez': 'gestacion', 'prenada': 'gestacion', 'preñada': 'gestacion', 'gestacion': 'gestacion',
            'lactancia': 'lactancia', 'lactacion': 'lactancia',
            'celo': 'celo', 'en celo': 'celo',
            'descanso': 'descanso', 'secado': 'descanso',
        }
        key = key_map.get(t, t)
        candidates_map = {
            'gestacion': {'gestacion', 'preniez', 'preñez', 'prenada', 'preñada'},
            'lactancia': {'lactancia', 'lactacion'},
            'celo': {'celo', 'en celo'},
            'descanso': {'descanso', 'secado'},
        }
        candidates = candidates_map.get(key, {key})
        try:
            estados = EstadoReproductivo.query.all()
            for e in estados:
                if _normalize(e.descripcion) in candidates:
                    return e
        except Exception:
            return None
        return None

    # Manejo de envíos POST
    if request.method == 'POST':
        target = request.form.get('form_name')
        if target == 'peso' and form_peso and form_peso.validate_on_submit():
            try:
                nuevo = RegistroPeso(
                    id_animal=animal.id_animal,
                    fecha_registro=form_peso.fecha_registro.data,
                    peso=form_peso.peso.data,
                    tipo_momento=form_peso.tipo_momento.data,
                    notas=form_peso.notas.data,
                )
                db.session.add(nuevo)
                db.session.commit()
                registrar_actividad(current_user.id, f"Registró peso para {animal.nombre_animal}")
                flash('Peso registrado correctamente.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error registrando peso: {e}', 'danger')
            return redirect(url_for('ver_animal_route', animal_id=animal_id))

        if target == 'ciclo_nuevo' and form_ciclo and form_ciclo.validate_on_submit():
            if ciclo_activo:
                flash('Ya existe un ciclo activo. Cierre el actual antes de iniciar uno nuevo.', 'warning')
                return redirect(url_for('ver_animal_route', animal_id=animal_id))
            try:
                nuevo_ciclo = CicloReproductivo(
                    id_animal=animal.id_animal,
                    fecha_inicio=form_ciclo.fecha_inicio.data,
                    tipo_ciclo=form_ciclo.tipo_ciclo.data,
                    duracion_esperada=form_ciclo.duracion_esperada.data,
                    notas=form_ciclo.notas.data,
                )
                db.session.add(nuevo_ciclo)

                estado_match = _buscar_estado_reprod_por_desc((form_ciclo.tipo_ciclo.data or '').lower())
                if estado_match:
                    db.session.add(HistorialEstadoReproductivo(
                        id_animal=animal.id_animal,
                        id_estado_reprod=estado_match.id_estado_reprod,
                        observaciones=f"Inicio de ciclo {form_ciclo.tipo_ciclo.data}"
                    ))
                    try:
                        if (animal.sexo or '').lower() == 'hembra':
                            animal.id_estado_reprod = estado_match.id_estado_reprod
                    except Exception:
                        pass
                else:
                    flash('No se encontró un estado reproductivo correspondiente al tipo de ciclo. Verifique que exista "Gestación", "Lactancia", "Celo" o "Descanso" en el catálogo.', 'warning')

                db.session.commit()
                registrar_actividad(current_user.id, f"Inició ciclo {form_ciclo.tipo_ciclo.data} en {animal.nombre_animal}")
                flash('Ciclo reproductivo iniciado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error iniciando ciclo: {e}', 'danger')
            return redirect(url_for('ver_animal_route', animal_id=animal_id))

        if target == 'ciclo_cerrar' and form_cerrar_ciclo and form_cerrar_ciclo.validate_on_submit():
            if not ciclo_activo:
                flash('No existe un ciclo activo para cerrar.', 'warning')
                return redirect(url_for('ver_animal_route', animal_id=animal_id))
            try:
                ciclo_activo.fecha_fin = form_cerrar_ciclo.fecha_fin.data
                if form_cerrar_ciclo.notas_fin.data:
                    ciclo_activo.notas = (ciclo_activo.notas or '') + f"\nCierre: {form_cerrar_ciclo.notas_fin.data}"

                estado_descanso = _buscar_estado_reprod_por_desc('descanso')
                if estado_descanso:
                    db.session.add(HistorialEstadoReproductivo(
                        id_animal=animal.id_animal,
                        id_estado_reprod=estado_descanso.id_estado_reprod,
                        observaciones=f"Cierre de ciclo: {ciclo_activo.tipo_ciclo}"
                    ))
                    try:
                        if (animal.sexo or '').lower() == 'hembra':
                            animal.id_estado_reprod = estado_descanso.id_estado_reprod
                    except Exception:
                        pass

                db.session.commit()
                registrar_actividad(current_user.id, f"Cerró ciclo {ciclo_activo.tipo_ciclo} en {animal.nombre_animal}")
                flash('Ciclo reproductivo cerrado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error cerrando ciclo: {e}', 'danger')
            return redirect(url_for('ver_animal_route', animal_id=animal_id))

        if target == 'salud_estado' and form_salud and form_salud.validate_on_submit():
            try:
                nuevo_hist = HistorialEstadoSalud(
                    id_animal=animal.id_animal,
                    id_estado_salud=form_salud.id_estado_salud.data,
                    observaciones=form_salud.observaciones.data,
                )
                db.session.add(nuevo_hist)
                db.session.commit()
                registrar_actividad(current_user.id, f"Actualizó estado de salud de {animal.nombre_animal}")
                flash('Estado de salud actualizado.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error actualizando estado de salud: {e}', 'danger')
            return redirect(url_for('ver_animal_route', animal_id=animal_id))

    return render_template(
        'dueño/ver_animal.html',
        animal=animal,
        # UI extendida
        form_peso=form_peso,
        registros_peso=registros_peso,
        peso_actual=(float(registros_peso[0].peso or 0) if registros_peso else None),
        form_ciclo=form_ciclo,
        form_cerrar_ciclo=form_cerrar_ciclo,
        ciclo_activo=ciclo_activo,
        ciclos_previos=ciclos_previos,
        form_salud=form_salud,
        historial_salud=historial_salud,
        estado_salud_actual=estado_salud_actual,
        estados_salud_choices=estados_salud_choices,
    )


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
        # Requerir explícitamente la finca para garantizar que solo se traen animales de esa finca
        return jsonify({'error': 'Parámetro finca_id es requerido'}), 400

    # Filtro por raza
    if raza_id:
        query = query.filter(Animal.id_raza == raza_id)

    # Filtro por fecha de nacimiento máxima
    fecha_max = None
    if fecha_max_str:
        try:
            from datetime import datetime
            fecha_max = datetime.strptime(fecha_max_str, '%Y-%m-%d').date()
            # El candidato debe haber nacido antes que la fecha de nacimiento del hijo
            query = query.filter(Animal.fecha_nacimiento <= fecha_max)
        except Exception:
            # Si la fecha no es válida, ignorar el filtro
            fecha_max = None

    animales = query.all()

    # Reglas adicionales de madurez para candidatos a padre/madre
    try:
        from datetime import date as _date
        hoy = _date.today()
        edad_hijo_dias = 0
        if fecha_max:
            try:
                edad_hijo_dias = max(0, (hoy - fecha_max).days)
            except Exception:
                edad_hijo_dias = 0

        sexo_lower = (sexo or '').strip().lower()

        if sexo_lower == 'macho':
            # Padre: madurez del macho + edad del hijo (consistente con validación de formulario)
            def _padre_apto(animal_local):
                try:
                    if not animal_local.fecha_nacimiento:
                        return False
                    edad_padre_dias = (hoy - animal_local.fecha_nacimiento).days
                    umbral_meses = None
                    try:
                        umbral_meses = int(getattr(animal_local.raza, 'madurez_sexual_machos_meses', None) or 0)
                    except Exception:
                        umbral_meses = 0
                    if not umbral_meses or umbral_meses <= 0:
                        umbral_meses = 12
                    umbral_dias = umbral_meses * 30
                    requerido = umbral_dias + edad_hijo_dias
                    return edad_padre_dias >= requerido
                except Exception:
                    return False

            animales = [a for a in animales if _padre_apto(a)]
        elif sexo_lower == 'hembra':
            # Madre: madurez de hembra + edad del hijo + 260 días (gestación)
            def _madre_apta(animal_local):
                try:
                    if not animal_local.fecha_nacimiento:
                        return False
                    edad_madre_dias = (hoy - animal_local.fecha_nacimiento).days
                    umbral_meses = None
                    try:
                        umbral_meses = int(getattr(animal_local.raza, 'madurez_sexual_hembras_meses', None) or 0)
                    except Exception:
                        umbral_meses = 0
                    if not umbral_meses or umbral_meses <= 0:
                        umbral_meses = 12
                    umbral_dias = umbral_meses * 30
                    requerido = umbral_dias + edad_hijo_dias + 260
                    return edad_madre_dias >= requerido
                except Exception:
                    return False

            animales = [a for a in animales if _madre_apta(a)]
    except Exception:
        # Si algo falla en el cálculo, mantener el listado sin filtrar adicionalmente
        pass

    animales_json = [{
        'id': animal.id_animal,
        'nombre': animal.nombre_animal,
        'finca': animal.finca.nombre_finca if animal.finca else 'Sin finca'
    } for animal in animales]

    return jsonify(animales_json)

@login_required
def api_existe_nombre_animal():
    """Verifica si ya existe un animal con el nombre indicado.
    Si se proporciona `finca_id`, se limita a esa finca (validando permisos).
    Si no, se limita a las fincas del usuario actual.
    """
    nombre = (request.args.get('nombre') or '').strip()
    finca_id = request.args.get('finca_id', type=int)

    if not nombre:
        return jsonify({'success': False, 'message': 'nombre requerido'}), 400

    # Query por nombre (case-insensitive)
    q = Animal.query.filter(func.lower(Animal.nombre_animal) == nombre.lower())

    if finca_id:
        # Validar acceso a la finca
        relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
        if not relacion and current_user.tipo_usuario != 3:
            return jsonify({'success': False, 'message': 'Sin permisos'}), 403
        q = q.filter(Animal.id_finca == finca_id)
    else:
        # Limitar a fincas del usuario cuando no se especifica finca
        try:
            fincas_usuario_ids = [f.id_finca for f in Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()]
        except Exception:
            fincas_usuario_ids = []
        if fincas_usuario_ids:
            q = q.filter(Animal.id_finca.in_(fincas_usuario_ids))
        else:
            return jsonify({'success': True, 'exists': False})

    exists = q.first() is not None
    return jsonify({'success': True, 'exists': exists})