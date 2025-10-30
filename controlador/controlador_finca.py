import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from modelo.models import Finca, UsuarioFinca, Potrero, RotacionPotrero, GrupoAnimal, Animal, AnimalGrupo, Usuario, Trabajador, Raza
from sqlalchemy.orm import joinedload
from forms.finca_form import FincaForm
from forms.potrero_form import PotreroForm
from config import db, add_server_timing, cache_get, cache_set
import time
from datetime import datetime
from controlador.controlador_actividad import registrar_actividad
import json
import hashlib

@login_required
def crear_finca():
    """Crear una nueva finca"""
    form = FincaForm()
    # Lista de trabajadores existentes para sugerencias (solo los ligados al dueño actual)
    try:
        registros = Trabajador.query.filter_by(id_jefe=current_user.id).all()
        nik_names = [t.usuario for t in registros if t.usuario]
        trabajadores_existentes = Usuario.query.filter(
            Usuario.tipo_usuario == 1,
            Usuario.nik_name.in_(nik_names)
        ).all() if nik_names else []
    except Exception:
        trabajadores_existentes = []
    
    # Poblar el selector de encargado con opciones dinámicas
    try:
        opciones_encargado = [(u.nik_name, u.nik_name) for u in trabajadores_existentes]
        form.nombreEncargado.choices = [('', 'Seleccione Encargado (opcional)')] + opciones_encargado
    except Exception:
        form.nombreEncargado.choices = [('', 'Seleccione Encargado (opcional)')]
    
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
            
            # Crear la relación usuario-finca (dueño actual)
            relacion_usuario_finca = UsuarioFinca(
                usuario_id=current_user.id,
                finca_id=nueva_finca.id_finca
            )
            db.session.add(relacion_usuario_finca)

            # Asignar encargado si coincide con un trabajador existente
            nombre_encargado = (form.nombreEncargado.data or '').strip()
            if nombre_encargado:
                encargado = Usuario.query.filter(Usuario.nik_name == nombre_encargado, Usuario.tipo_usuario == 1).first()
                if encargado and encargado.id != current_user.id:
                    relacion_encargado = UsuarioFinca.query.filter_by(usuario_id=encargado.id, finca_id=nueva_finca.id_finca).first()
                    if not relacion_encargado:
                        relacion_encargado = UsuarioFinca(usuario_id=encargado.id, finca_id=nueva_finca.id_finca)
                        db.session.add(relacion_encargado)
                    relacion_encargado.rol_en_finca = 3  # Administrador/Encargado
                    relacion_encargado.puede_editar = True
            
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
    
    return render_template('dueño/crear_finca.html', form=form, trabajadores_existentes=trabajadores_existentes)

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
    
    # Crear formulario con datos existentes y pasar el id para validación correcta
    form = FincaForm(obj=finca, finca_id=finca.id_finca)
    # Sugerir solo trabajadores ligados al dueño actual
    try:
        registros = Trabajador.query.filter_by(id_jefe=current_user.id).all()
        nik_names = [t.usuario for t in registros if t.usuario]
        trabajadores_existentes = Usuario.query.filter(
            Usuario.tipo_usuario == 1,
            Usuario.nik_name.in_(nik_names)
        ).all() if nik_names else []
    except Exception:
        trabajadores_existentes = []
    
    # Poblar el selector con opciones dinámicas y asegurar que el valor actual esté disponible
    try:
        opciones_encargado = [(u.nik_name, u.nik_name) for u in trabajadores_existentes]
        valor_actual = (finca.nombreEncargado or '').strip()
        if valor_actual and valor_actual not in [v for v, _ in opciones_encargado]:
            opciones_encargado.append((valor_actual, valor_actual))
        form.nombreEncargado.choices = [('', 'Seleccione Encargado (opcional)')] + opciones_encargado
    except Exception:
        form.nombreEncargado.choices = [('', 'Seleccione Encargado (opcional)')]
    
    if form.validate_on_submit():
        try:
            # Actualizar los datos de la finca
            form.populate_obj(finca)

            # Asignar/actualizar encargado si coincide con un trabajador existente
            nombre_encargado = (form.nombreEncargado.data or '').strip()
            if nombre_encargado:
                encargado = Usuario.query.filter(Usuario.nik_name == nombre_encargado, Usuario.tipo_usuario == 1).first()
                if encargado and encargado.id != current_user.id:
                    relacion_encargado = UsuarioFinca.query.filter_by(usuario_id=encargado.id, finca_id=finca.id_finca).first()
                    if not relacion_encargado:
                        relacion_encargado = UsuarioFinca(usuario_id=encargado.id, finca_id=finca.id_finca)
                        db.session.add(relacion_encargado)
                    relacion_encargado.rol_en_finca = 3  # Administrador/Encargado
                    relacion_encargado.puede_editar = True
            
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
    
    return render_template('dueño/editar_finca.html', form=form, finca=finca, trabajadores_existentes=trabajadores_existentes)

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

    # IDs de los potreros de esta finca
    potrero_ids = [p.id_potrero for p in potreros]

    # Rotaciones (todas) para mostrar en UI según sea necesario
    rotaciones = []
    if potrero_ids:
        rotaciones = (db.session.query(RotacionPotrero)
            .filter(RotacionPotrero.id_potrero.in_(potrero_ids))
            .all())

    # Trabajadores asignados a esta finca (excluyendo al dueño)
    relaciones_trabajadores = UsuarioFinca.query.filter(
        UsuarioFinca.finca_id == finca_id,
        UsuarioFinca.usuario_id != current_user.id
    ).all()

    asignados_ids = {rel.usuario_id for rel in relaciones_trabajadores}

    # Trabajadores del dueño (tabla legacy Trabajador vincula por nik_name)
    try:
        registros = Trabajador.query.filter_by(id_jefe=current_user.id).all()
        nik_names = [t.usuario for t in registros if t.usuario]
        trabajadores_dueno = Usuario.query.filter(
            Usuario.tipo_usuario == 1,
            Usuario.nik_name.in_(nik_names)
        ).all() if nik_names else []
    except Exception:
        trabajadores_dueno = []

    # Mapear documento desde tabla legacy para mostrar en UI
    documentos_map = {}
    try:
        doc_por_nik = {t.usuario: t.documento for t in registros}
        for u in trabajadores_dueno:
            documentos_map[u.id] = doc_por_nik.get(u.nik_name)
    except Exception:
        documentos_map = {}

    # Listados auxiliares para modales: sin asignación y con otras fincas
    trabajadores_sin_asignacion = []
    trabajadores_con_otras_fincas = []
    try:
        for u in trabajadores_dueno:
            # Relaciones del usuario en cualquier finca
            rels_usuario = UsuarioFinca.query.filter_by(usuario_id=u.id).all()
            if not rels_usuario:
                trabajadores_sin_asignacion.append(u)
            else:
                # Tiene relaciones, verificar si NO está asignado a esta finca
                asignado_en_esta = any(r.finca_id == finca_id for r in rels_usuario)
                if not asignado_en_esta:
                    trabajadores_con_otras_fincas.append(u)
    except Exception:
        trabajadores_sin_asignacion = []
        trabajadores_con_otras_fincas = []

    # Calcular sobrecupo por potrero y "Último uso" utilizando consultas agregadas
    sobrecupo_map = {}
    ultimo_uso_map = {}

    if potrero_ids:
        # Rotaciones abiertas en todos los potreros de la finca
        rotaciones_abiertas = (db.session.query(RotacionPotrero)
            .filter(
                RotacionPotrero.id_potrero.in_(potrero_ids),
                RotacionPotrero.fecha_fin.is_(None)
            )
            .all())

        # Seleccionar la última rotación abierta por grupo (global)
        last_open_by_group = {}
        for rot in rotaciones_abiertas:
            gid = rot.id_grupo_animal or rot.id_grupo
            if not gid:
                continue
            cur = last_open_by_group.get(gid)
            if (
                cur is None
                or (rot.fecha_inicio or datetime.min) > (cur.fecha_inicio or datetime.min)
                or ((rot.fecha_inicio or datetime.min) == (cur.fecha_inicio or datetime.min) and rot.id_rotacion > cur.id_rotacion)
            ):
                last_open_by_group[gid] = rot

        # Mapear rotaciones filtradas y grupos activos por potrero
        rotaciones_filtradas_por_potrero = {pid: [] for pid in potrero_ids}
        grupos_activos_por_potrero = {pid: set() for pid in potrero_ids}
        for rot in rotaciones_abiertas:
            gid = rot.id_grupo_animal or rot.id_grupo
            if gid and last_open_by_group.get(gid) is rot:
                rotaciones_filtradas_por_potrero[rot.id_potrero].append(rot)
                grupos_activos_por_potrero[rot.id_potrero].add(gid)

        # Incluir grupos cuyos animales están presentes en cada potrero
        grupos_por_animales_all = (db.session.query(Animal.id_potrero, AnimalGrupo.id_grupo)
            .join(AnimalGrupo, Animal.id_animal == AnimalGrupo.id_animal)
            .filter(Animal.id_potrero.in_(potrero_ids))
            .all())
        for pid, gid in grupos_por_animales_all:
            grupos_activos_por_potrero.setdefault(pid, set()).add(gid)

        # Conteos presentes por potrero y grupo
        presentes_por_potrero = {}
        conteos_presentes_all = (db.session.query(
                Animal.id_potrero,
                AnimalGrupo.id_grupo,
                db.func.count(db.func.distinct(AnimalGrupo.id_animal))
            )
            .join(AnimalGrupo, Animal.id_animal == AnimalGrupo.id_animal)
            .filter(Animal.id_potrero.in_(potrero_ids))
            .group_by(Animal.id_potrero, AnimalGrupo.id_grupo)
            .all())
        for pid, gid, cnt in conteos_presentes_all:
            presentes_por_potrero.setdefault(pid, {})[gid] = cnt

        # Conteos totales por grupo (una vez)
        totales_dict = {
            gid: cnt for gid, cnt in (
                db.session.query(
                    AnimalGrupo.id_grupo,
                    db.func.count(db.func.distinct(AnimalGrupo.id_animal))
                )
                .group_by(AnimalGrupo.id_grupo)
                .all()
            )
        }

        # Animales presentes por potrero (conteo total)
        animales_presentes_dict = {
            pid: cnt for pid, cnt in (
                db.session.query(Animal.id_potrero, db.func.count(Animal.id_animal))
                .filter(Animal.id_potrero.in_(potrero_ids))
                .group_by(Animal.id_potrero)
                .all()
            )
        }

        # Última rotación cerrada por potrero (si no hay animales presentes)
        rotaciones_cerradas = (db.session.query(RotacionPotrero)
            .filter(
                RotacionPotrero.id_potrero.in_(potrero_ids),
                RotacionPotrero.fecha_fin.isnot(None)
            )
            .order_by(RotacionPotrero.fecha_fin.desc(), RotacionPotrero.fecha_inicio.desc())
            .all())
        ultima_cerrada_por_potrero = {}
        for rot in rotaciones_cerradas:
            pid = rot.id_potrero
            if pid not in ultima_cerrada_por_potrero:
                ultima_cerrada_por_potrero[pid] = rot

        # Calcular ocupación por grupos (rotaciones abiertas usan tamaño total del grupo)
        ocupacion_grupos_total_dict = {}
        for p in potreros:
            pid = p.id_potrero
            capacidad = p.capacidad_animal or 0
            animales_presentes = int(animales_presentes_dict.get(pid, 0) or 0)

            # Grupos activos en este potrero vía rotación abierta o presencia física
            grupos_activos = grupos_activos_por_potrero.get(pid, set())
            grupos_con_rotacion = { (r.id_grupo_animal or r.id_grupo) for r in rotaciones_filtradas_por_potrero.get(pid, []) if (r.id_grupo_animal or r.id_grupo) }

            # Ocupación por grupos aplicando la regla: si el grupo rota aquí, usar su tamaño total; si no, usar presentes
            ocupacion_grupos_total = 0
            for gid in grupos_activos:
                if gid in grupos_con_rotacion:
                    ocupacion_grupos_total += int(totales_dict.get(gid, 0) or 0)
                else:
                    ocupacion_grupos_total += int(presentes_por_potrero.get(pid, {}).get(gid, 0) or 0)
            ocupacion_grupos_total_dict[pid] = ocupacion_grupos_total

            # Sobrecupo en la lista se determina por ocupación de grupos respecto a capacidad
            sobrecupo_map[pid] = bool(capacidad and ocupacion_grupos_total > capacidad)

            # Último uso: 'En uso' si hay animales presentes; si no, última rotación cerrada
            if animales_presentes > 0:
                ultimo_uso_map[pid] = 'En uso'
            else:
                ultima_cerrada = ultima_cerrada_por_potrero.get(pid)
                if not ultima_cerrada:
                    ultimo_uso_map[pid] = 'No hay uso registrado'
                else:
                    inicio_str = ultima_cerrada.fecha_inicio.strftime('%d/%m/%Y')
                    fin_str = ultima_cerrada.fecha_fin.strftime('%d/%m/%Y')
                    ultimo_uso_map[pid] = f"{inicio_str} - {fin_str}"
    else:
        # Sin potreros: mapas vacíos
        sobrecupo_map = {}
        ultimo_uso_map = {}

    # Datos para gráficas basados en la BD
    chart_uso_potreros = {
        'disponible': sum(1 for p in potreros if p.estado == 'activo' and (animales_presentes_dict.get(p.id_potrero, 0) or 0) == 0),
        'ocupado': sum(1 for p in potreros if p.estado == 'activo' and (animales_presentes_dict.get(p.id_potrero, 0) or 0) > 0),
        'descanso': sum(1 for p in potreros if p.estado == 'descanso'),
    }
    chart_labels = [p.nombre_potrero for p in potreros]
    chart_capacidad = [int(p.capacidad_animal or 0) for p in potreros]
    chart_ocupacion = [(ocupacion_grupos_total_dict.get(p.id_potrero, (animales_presentes_dict.get(p.id_potrero, 0) or 0))) for p in potreros]

    return render_template(
        'dueño/gestionarfinca.html',
        finca=finca,
        potreros=potreros,
        rotaciones=rotaciones,
        relaciones_trabajadores=relaciones_trabajadores,
        trabajadores_dueno=trabajadores_dueno,
        trabajadores_sin_asignacion=trabajadores_sin_asignacion,
        trabajadores_con_otras_fincas=trabajadores_con_otras_fincas,
        asignados_ids=asignados_ids,
        documentos_map=documentos_map,
        sobrecupo_map=sobrecupo_map,
        ultimo_uso_map=ultimo_uso_map,
        chart_uso_potreros=chart_uso_potreros,
        chart_labels=chart_labels,
        chart_capacidad=chart_capacidad,
        chart_ocupacion=chart_ocupacion
    )

@login_required
def obtener_fincas_usuario():
    """API endpoint para obtener las fincas del usuario actual"""
    # Consulta directa para obtener las fincas del usuario actual
    cache_key = f"fincas_usuario:{current_user.id}"
    _tq = time.perf_counter()
    fincas = cache_get(cache_key)
    if fincas is None:
        fincas = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
        cache_set(cache_key, fincas, timeout=60)
        add_server_timing('q_fincas_usuario', (time.perf_counter() - _tq) * 1000.0)
    else:
        add_server_timing('cache_fincas_hit', (time.perf_counter() - _tq) * 1000.0)
    
    # Convertir a JSON
    fincas_json = [{
        'id': finca.id_finca,
        'nombre': finca.nombre_finca
    } for finca in fincas]

    # Compactar payload JSON para reducir tamaño de respuesta
    _tj = time.perf_counter()
    payload = json.dumps(fincas_json, separators=(",", ":"), ensure_ascii=False)
    add_server_timing('json_encode', (time.perf_counter() - _tj) * 1000.0)

    # Calcular ETag débil basado en el contenido
    etag_value = 'W/"' + hashlib.sha256(payload.encode('utf-8')).hexdigest() + '"'

    # Caching: respuesta privada, corta duración
    cache_control = 'private, max-age=60'

    # Responder 304 si el ETag coincide
    if request.headers.get('If-None-Match') == etag_value:
        resp = make_response('', 304)
        resp.headers['ETag'] = etag_value
        resp.headers['Cache-Control'] = cache_control
        resp.headers['Vary'] = 'Cookie'
        return resp

    # Respuesta normal con encabezados de caché
    _tr = time.perf_counter()
    resp = make_response(payload)
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['ETag'] = etag_value
    resp.headers['Cache-Control'] = cache_control
    resp.headers['Vary'] = 'Cookie'
    add_server_timing('build_response', (time.perf_counter() - _tr) * 1000.0)
    return resp

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
def guardar_rotacion():
    """Guardar una rotación de potrero desde el modal con validaciones"""
    try:
        data = request.get_json() or {}
        potrero_id = data.get('potrero_id', None)
        # IDs adicionales para soportar rotación entre potreros
        potrero_origen_id = data.get('potrero_origen_id', None)
        potrero_destino_id = data.get('potrero_destino_id', None)
        grupo_animal_id = data.get('grupo_animal_id', None)
        fecha_inicio_str = data.get('fecha_inicio')
        fecha_fin_str = data.get('fecha_fin')
        tipo_uso = data.get('tipo_uso')
        observaciones = data.get('observaciones')

        # Validaciones básicas
        if not potrero_id or not grupo_animal_id or not fecha_inicio_str or not tipo_uso:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

        # Parseo de fechas
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        except Exception:
            return jsonify({'success': False, 'message': 'Fecha de inicio inválida'}), 400
        fecha_fin = None
        if fecha_fin_str:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except Exception:
                return jsonify({'success': False, 'message': 'Fecha de fin inválida'}), 400
            if fecha_fin < fecha_inicio:
                return jsonify({'success': False, 'message': 'La fecha de fin no puede ser anterior a la de inicio'}), 400

        # Validar tipo de uso contra el Enum del modelo
        tipos_validos = {'pastoreo', 'descanso', 'siembra', 'fertilización', 'mantenimiento'}
        if tipo_uso not in tipos_validos:
            return jsonify({'success': False, 'message': 'Tipo de uso inválido'}), 400

        # Obtener potrero (destino en caso de rotación) y verificar permisos del usuario sobre la finca
        potrero = Potrero.query.get(potrero_id)
        if not potrero:
            return jsonify({'success': False, 'message': 'Potrero no encontrado'}), 404
        relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
        if not relacion and current_user.tipo_usuario != 3:
            return jsonify({'success': False, 'message': 'No tienes permisos para modificar esta finca'}), 403

        # Validar grupo animal existe y pertenece a la misma finca
        grupo = GrupoAnimal.query.get(grupo_animal_id)
        if not grupo:
            return jsonify({'success': False, 'message': 'Grupo animal no encontrado'}), 404
        if grupo.id_finca != potrero.id_finca:
            return jsonify({'success': False, 'message': 'El grupo animal no pertenece a la finca del potrero'}), 400

        # Si es una rotación (hay origen y destino distintos), cerrar rotación activa del origen
        es_rotacion = bool(potrero_origen_id and potrero_destino_id and (str(potrero_origen_id) != str(potrero_destino_id)))
        if es_rotacion:
            potrero_origen = Potrero.query.get(potrero_origen_id)
            if not potrero_origen:
                return jsonify({'success': False, 'message': 'Potrero de origen no encontrado'}), 404
            # Validar permisos y que origen esté en la misma finca
            rel_origen = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero_origen.id_finca).first()
            if not rel_origen and current_user.tipo_usuario != 3:
                return jsonify({'success': False, 'message': 'No tienes permisos para modificar el potrero de origen'}), 403
            if potrero_origen.id_finca != potrero.id_finca:
                return jsonify({'success': False, 'message': 'Origen y destino deben pertenecer a la misma finca'}), 400

            # Cerrar rotaciones activas del grupo en el potrero de origen
            # Cerrar rotaciones activas del origen, contemplando registros antiguos
            rotaciones_origen_activas = (db.session.query(RotacionPotrero)
                .filter(
                    RotacionPotrero.id_potrero == potrero_origen_id,
                    RotacionPotrero.fecha_fin.is_(None),
                    ( (RotacionPotrero.id_grupo_animal == grupo.id_grupo) | (RotacionPotrero.id_grupo == grupo.id_grupo) )
                )
                .all())
            for rot_activa in rotaciones_origen_activas:
                rot_activa.fecha_fin = fecha_inicio

            # Mover todos los animales del grupo al potrero destino
            animales_a_mover = (db.session.query(Animal)
                .join(AnimalGrupo, Animal.id_animal == AnimalGrupo.id_animal)
                .filter(AnimalGrupo.id_grupo == grupo.id_grupo)
                .all())
            for animal in animales_a_mover:
                animal.id_potrero = potrero.id_potrero

        # Si NO es rotación (agregar grupo al potrero), cerrar rotaciones abiertas previas
        # y asignar todos los animales del grupo al potrero destino
        if not es_rotacion:
            # Cerrar cualquier rotación abierta de este grupo en cualquier potrero
            rotaciones_abiertas = (db.session.query(RotacionPotrero)
                .filter(
                    RotacionPotrero.fecha_fin.is_(None),
                    ((RotacionPotrero.id_grupo_animal == grupo.id_grupo) | (RotacionPotrero.id_grupo == grupo.id_grupo))
                )
                .all())
            for rot_abierta in rotaciones_abiertas:
                rot_abierta.fecha_fin = fecha_inicio

            # Asignar todos los animales del grupo al potrero destino
            animales_en_grupo = (db.session.query(Animal)
                .join(AnimalGrupo, Animal.id_animal == AnimalGrupo.id_animal)
                .filter(AnimalGrupo.id_grupo == grupo.id_grupo)
                .all())
            for animal in animales_en_grupo:
                animal.id_potrero = potrero.id_potrero

        # Crear la rotación en el potrero (destino si aplica)
        rotacion = RotacionPotrero(
            id_potrero=potrero.id_potrero,
            id_grupo_animal=grupo.id_grupo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_uso=tipo_uso,
            observaciones=observaciones,
            id_grupo=grupo.id_grupo
        )
        db.session.add(rotacion)

        # Actualizar estado y fecha del potrero según tipo de uso
        # Siempre actualizamos la fecha de última rotación
        potrero.fecha_ultima_rotacion = fecha_inicio
        # Mapear el tipo de uso de la rotación al estado del potrero
        if tipo_uso == 'pastoreo':
            potrero.estado = 'activo'
        elif tipo_uso == 'descanso':
            potrero.estado = 'descanso'
        elif tipo_uso in ('siembra', 'fertilización', 'mantenimiento'):
            potrero.estado = 'mantenimiento'

        db.session.commit()

        # Calcular ocupación actual del potrero y si excede capacidad
        ocupacion_total = db.session.query(db.func.count(Animal.id_animal)).\
            filter(Animal.id_potrero == potrero.id_potrero).scalar() or 0
        capacidad = potrero.capacidad_animal or 0
        excede_capacidad = bool(capacidad and ocupacion_total > capacidad)

        if es_rotacion:
            registrar_actividad('Rotó', f'Grupo {grupo.nombre_grupo} desde {potrero_origen.nombre_potrero} hacia {potrero.nombre_potrero} ({tipo_uso})')
        else:
            registrar_actividad('Registró', f'Rotación en {potrero.nombre_potrero} ({tipo_uso}) - Grupo {grupo.nombre_grupo}')

        return jsonify({'success': True, 'message': 'Rotación guardada correctamente', 'excede_capacidad': excede_capacidad, 'ocupacion_total': ocupacion_total, 'capacidad': capacidad})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar la rotación: {str(e)}'}), 500

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

@login_required
def ver_potrero(potrero_id):
    """Ver detalles de un potrero y los grupos activos (en rotación)"""
    potrero = Potrero.query.get_or_404(potrero_id)

    # Verificar que el usuario actual tiene acceso a la finca de este potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para ver este potrero', 'danger')
        return redirect(url_for('mis_fincas'))

    # Cargar rotaciones abiertas en este potrero y filtrar
    # para mostrar solo si es la última rotación abierta del grupo
    rotaciones_activas = RotacionPotrero.query.filter_by(id_potrero=potrero_id, fecha_fin=None).all()
    rotaciones_activas_filtradas = []
    grupos_activos = []
    for rot in rotaciones_activas:
        # Determinar el identificador del grupo (soporta registros legados con id_grupo)
        grupo_id = rot.id_grupo_animal or rot.id_grupo

        # Buscar la última rotación abierta del grupo en cualquier potrero
        ultima_abierta = (RotacionPotrero.query
            .filter(
                RotacionPotrero.fecha_fin.is_(None),
                ((RotacionPotrero.id_grupo_animal == grupo_id) | (RotacionPotrero.id_grupo == grupo_id))
            )
            .order_by(RotacionPotrero.fecha_inicio.desc(), RotacionPotrero.id_rotacion.desc())
            .first())

        # Si existe una última rotación abierta y no pertenece a este potrero, no mostrar el grupo aquí
        if ultima_abierta and ultima_abierta.id_potrero != potrero_id:
            continue

        rotaciones_activas_filtradas.append(rot)

        # Asegurar inclusión del objeto GrupoAnimal aunque el backref esté ausente en registros antiguos
        grupo_obj = rot.grupo_animal or GrupoAnimal.query.get(grupo_id)
        if grupo_obj and grupo_obj not in grupos_activos:
            grupos_activos.append(grupo_obj)

    # Incluir grupos cuyos animales están actualmente ubicados en este potrero
    grupos_por_animales = db.session.query(GrupoAnimal).\
        join(AnimalGrupo, GrupoAnimal.id_grupo == AnimalGrupo.id_grupo).\
        join(Animal, AnimalGrupo.id_animal == Animal.id_animal).\
        filter(Animal.id_potrero == potrero_id).all()

    for g in grupos_por_animales:
        if g not in grupos_activos:
            grupos_activos.append(g)

    # Conteo de animales por grupo presentes en el potrero (evitar duplicados)
    conteos_presentes = (
        db.session.query(
            AnimalGrupo.id_grupo,
            db.func.count(db.func.distinct(AnimalGrupo.id_animal))
        )
        .join(Animal, Animal.id_animal == AnimalGrupo.id_animal)
        .filter(Animal.id_potrero == potrero_id)
        .group_by(AnimalGrupo.id_grupo)
        .all()
    )
    conteo_presentes_dict = {gid: cnt for gid, cnt in conteos_presentes}

    # Tamaño total del grupo según relaciones en animal_grupo (conteo real por grupo)
    conteos_totales = (
        db.session.query(
            AnimalGrupo.id_grupo,
            db.func.count(db.func.distinct(AnimalGrupo.id_animal))
        )
        .group_by(AnimalGrupo.id_grupo)
        .all()
    )
    conteo_totales_dict = {gid: cnt for gid, cnt in conteos_totales}

    # Si el grupo tiene rotación activa en este potrero, mostrar el tamaño total del grupo;
    # de lo contrario, mostrar los animales presentes físicamente en el potrero.
    grupos_con_rotacion = set()
    for rot in rotaciones_activas_filtradas:
        gid = rot.id_grupo_animal or rot.id_grupo
        if gid:
            grupos_con_rotacion.add(gid)

    conteo_animales_potrero = {}
    for grupo in grupos_activos:
        gid = grupo.id_grupo
        if gid in grupos_con_rotacion:
            conteo_animales_potrero[gid] = conteo_totales_dict.get(gid, 0)
        else:
            conteo_animales_potrero[gid] = conteo_presentes_dict.get(gid, 0)

    # Ocupación por grupos con regla de rotación y bandera de capacidad excedida
    ocupacion_total = db.session.query(db.func.count(Animal.id_animal)).\
        filter(Animal.id_potrero == potrero_id).scalar() or 0
    ocupacion_grupos_total = sum(conteo_animales_potrero.values()) if conteo_animales_potrero else 0
    capacidad = potrero.capacidad_animal or 0
    capacidad_excedida = bool(capacidad and ocupacion_grupos_total > capacidad)

    # Calcular último uso para este potrero
    animales_presentes = (db.session.query(db.func.count(Animal.id_animal))
        .filter(Animal.id_potrero == potrero.id_potrero)
        .scalar()) or 0
    if animales_presentes > 0:
        ultimo_uso_text = 'En uso'
    else:
        ultima_cerrada = (db.session.query(RotacionPotrero)
            .filter(
                RotacionPotrero.id_potrero == potrero.id_potrero,
                RotacionPotrero.fecha_fin.isnot(None)
            )
            .order_by(RotacionPotrero.fecha_fin.desc(), RotacionPotrero.fecha_inicio.desc())
            .first())
        if not ultima_cerrada:
            ultimo_uso_text = 'No hay uso registrado'
        else:
            ultimo_uso_text = f"{ultima_cerrada.fecha_inicio.strftime('%d/%m/%Y')} - {ultima_cerrada.fecha_fin.strftime('%d/%m/%Y')}"

    return render_template(
        'dueño/ver_potrero.html',
        potrero=potrero,
        grupos=grupos_activos,
        rotaciones=rotaciones_activas_filtradas,
        finca=potrero.finca,
        conteo_animales_potrero=conteo_animales_potrero,
        ocupacion_total=ocupacion_total,
        ocupacion_grupos_total=ocupacion_grupos_total,
        capacidad_excedida=capacidad_excedida,
        ultimo_uso_text=ultimo_uso_text
    )

@login_required
def api_grupos_activos_por_potrero():
    """Devuelve grupos activos en un potrero.
    Combina grupos con última rotación abierta en este potrero
    y grupos que tienen animales actualmente ubicados en el potrero.
    """
    potrero_id = request.args.get('potrero_id', type=int)
    if not potrero_id:
        return jsonify({'success': False, 'message': 'potrero_id requerido'}), 400

    potrero = Potrero.query.get(potrero_id)
    if not potrero:
        return jsonify({'success': False, 'message': 'Potrero no encontrado'}), 404

    # Verificar permisos sobre la finca del potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'success': False, 'message': 'Sin permisos'}), 403

    # Rotaciones abiertas en este potrero, mostrando solo la última por grupo
    rotaciones_activas = RotacionPotrero.query.filter_by(id_potrero=potrero_id, fecha_fin=None).all()
    grupos_activos = []
    for rot in rotaciones_activas:
        grupo_id = rot.id_grupo_animal or rot.id_grupo
        ultima_abierta = (RotacionPotrero.query
                          .filter(
                              RotacionPotrero.fecha_fin.is_(None),
                              ((RotacionPotrero.id_grupo_animal == grupo_id) | (RotacionPotrero.id_grupo == grupo_id))
                          )
                          .order_by(RotacionPotrero.fecha_inicio.desc(), RotacionPotrero.id_rotacion.desc())
                          .first())
        if ultima_abierta and ultima_abierta.id_potrero != potrero_id:
            continue
        grupo_obj = rot.grupo_animal or GrupoAnimal.query.get(grupo_id)
        if grupo_obj and grupo_obj not in grupos_activos:
            grupos_activos.append(grupo_obj)

    # Incluir grupos con animales actualmente en el potrero
    grupos_por_animales = (db.session.query(GrupoAnimal)
                           .join(AnimalGrupo, GrupoAnimal.id_grupo == AnimalGrupo.id_grupo)
                           .join(Animal, AnimalGrupo.id_animal == Animal.id_animal)
                           .filter(Animal.id_potrero == potrero_id)
                           .all())
    for g in grupos_por_animales:
        if g not in grupos_activos:
            grupos_activos.append(g)

    # Serializar
    data = [{'id': g.id_grupo, 'nombre': g.nombre_grupo} for g in grupos_activos]
    return jsonify({'success': True, 'grupos': data})

@login_required
def api_grupos_por_finca():
    """Devuelve todos los grupos de una finca si el usuario tiene acceso."""
    finca_id = request.args.get('finca_id', type=int)
    if not finca_id:
        return jsonify({'success': False, 'message': 'finca_id requerido'}), 400

    finca = Finca.query.get(finca_id)
    if not finca:
        return jsonify({'success': False, 'message': 'Finca no encontrada'}), 404

    # Verificar permisos sobre la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'success': False, 'message': 'Sin permisos'}), 403

    grupos = GrupoAnimal.query.filter_by(id_finca=finca_id).order_by(GrupoAnimal.nombre_grupo.asc()).all()
    data = [{'id': g.id_grupo, 'nombre': g.nombre_grupo} for g in grupos]
    return jsonify({'success': True, 'grupos': data})

@login_required
def agregar_animales_potrero(potrero_id):
    """Página para agregar animales disponibles a un potrero"""
    potrero = Potrero.query.get_or_404(potrero_id)

    # Verificar permisos sobre la finca
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para modificar este potrero', 'danger')
        return redirect(url_for('mis_fincas'))

    # Redirigir a la gestión de grupos de la finca para crear/formar grupos
    return redirect(url_for('listar_grupos_finca_route', finca_id=potrero.id_finca))


@login_required
def listar_grupos_finca(finca_id):
    """Listar y crear grupos de una finca"""
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para gestionar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))

    finca = Finca.query.get_or_404(finca_id)
    grupos = GrupoAnimal.query.filter_by(id_finca=finca_id).all()

    # Crear grupo (POST)
    if request.method == 'POST':
        nombre = request.form.get('nombre_grupo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        if not nombre:
            flash('El nombre del grupo es requerido', 'danger')
        else:
            try:
                # Validar duplicado de nombre dentro de la misma finca (case-insensitive)
                existente = GrupoAnimal.query.filter(
                    GrupoAnimal.id_finca == finca_id,
                    db.func.lower(GrupoAnimal.nombre_grupo) == nombre.lower()
                ).first()
                if existente:
                    flash('Ya existe un grupo con ese nombre en esta finca', 'warning')
                    return redirect(url_for('listar_grupos_finca_route', finca_id=finca_id))

                nuevo = GrupoAnimal(nombre_grupo=nombre, id_finca=finca_id, descripcion=descripcion)
                db.session.add(nuevo)
                db.session.commit()
                registrar_actividad('Creó', f'Grupo: {nombre}')
                flash('Grupo creado correctamente', 'success')
                return redirect(url_for('listar_grupos_finca_route', finca_id=finca_id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear grupo: {str(e)}', 'danger')

    return render_template('dueño/grupos_finca.html', finca=finca, grupos=grupos)


@login_required
def gestionar_grupo(grupo_id):
    """Gestionar miembros de un grupo: ver y añadir animales"""
    grupo = GrupoAnimal.query.get_or_404(grupo_id)

    # Verificar permisos sobre la finca del grupo
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=grupo.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para gestionar este grupo', 'danger')
        return redirect(url_for('mis_fincas'))

    # Animales del grupo
    animales_grupo = grupo.animales

    # Animales disponibles de la misma finca: excluir cualquier animal ya asignado a algún grupo
    animales_disponibles_query = (Animal.query
                                  .options(joinedload(Animal.raza))
                                  .filter(
                                      Animal.id_finca == grupo.id_finca,
                                      Animal.ubicacion_animal.in_(['en finca', 'en_finca'])
                                  ))

    # IDs de animales que ya pertenecen a algún grupo dentro de la finca
    ids_en_alguna_relacion = {
        rel.id_animal for rel in (
            db.session.query(AnimalGrupo)
            .join(GrupoAnimal, AnimalGrupo.id_grupo == GrupoAnimal.id_grupo)
            .filter(GrupoAnimal.id_finca == grupo.id_finca)
            .all()
        )
    }

    animales_disponibles = [a for a in animales_disponibles_query.all() if a.id_animal not in ids_en_alguna_relacion]

    # Razas presentes entre los animales disponibles (para filtro en UI)
    try:
        razas_dict = {}
        for a in animales_disponibles:
            if a.raza and getattr(a.raza, 'id_raza', None):
                razas_dict[a.raza.id_raza] = a.raza
        razas_disponibles = sorted(list(razas_dict.values()), key=lambda r: (getattr(r, 'nombre_raza', '') or '').lower())
    except Exception:
        razas_disponibles = []

    # Map de madurez sexual por animal disponible
    def _es_maduro(a: Animal) -> bool:
        # Calcular edad en meses y comparar con umbral por raza y sexo
        try:
            fn = a.fecha_nacimiento
            hoy = datetime.now().date()
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
        try:
            return meses >= int(umbral)
        except Exception:
            return False

    madurez_map = {a.id_animal: _es_maduro(a) for a in animales_disponibles}

    # Potrero de retorno opcional para el botón "Volver"
    potrero_id = request.args.get('potrero_id', type=int)

    return render_template('dueño/gestionar_grupo.html', grupo=grupo, animales_grupo=animales_grupo, animales_disponibles=animales_disponibles, razas_disponibles=razas_disponibles, madurez_map=madurez_map, potrero_id=potrero_id)

@login_required
def eliminar_grupo(grupo_id):
    """Eliminar un grupo de animales de forma segura"""
    grupo = GrupoAnimal.query.get_or_404(grupo_id)

    # Verificar permisos sobre la finca del grupo
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=grupo.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        flash('No tienes permisos para eliminar este grupo', 'danger')
        return redirect(url_for('mis_fincas'))

    try:
        # Cerrar y desvincular rotaciones que referencian este grupo (para evitar FK rotas)
        rotaciones = RotacionPotrero.query.filter_by(id_grupo_animal=grupo_id).all()
        for rot in rotaciones:
            if rot.fecha_fin is None:
                rot.fecha_fin = datetime.now().date()
            # Preservar el id del grupo en el campo legado y limpiar FK
            rot.id_grupo = grupo.id_grupo
            rot.id_grupo_animal = None

        nombre_grupo = grupo.nombre_grupo
        finca_id = grupo.id_finca

        # Eliminar el grupo (las relaciones AnimalGrupo se borran por CASCADE)
        db.session.delete(grupo)
        db.session.commit()

        registrar_actividad('Eliminó', f'Grupo: {nombre_grupo}')
        flash(f'Grupo "{nombre_grupo}" eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el grupo: {str(e)}', 'danger')

    # Redirigir: si viene desde un potrero, regresar allí; si no, a la lista de grupos
    potrero_id = request.form.get('potrero_id', type=int)
    if potrero_id:
        return redirect(url_for('ver_potrero_route', potrero_id=potrero_id))
    return redirect(url_for('listar_grupos_finca_route', finca_id=finca_id))


@login_required
def api_agregar_animal_a_grupo(grupo_id):
    """Agregar un animal al grupo seleccionado"""
    grupo = GrupoAnimal.query.get_or_404(grupo_id)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=grupo.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'success': False, 'message': 'Sin permisos'}), 403

    data = request.json if request.is_json else request.form
    animal_id = int(data.get('animal_id', 0))
    if not animal_id:
        return jsonify({'success': False, 'message': 'animal_id requerido'}), 400

    animal = Animal.query.get(animal_id)
    if not animal or animal.id_finca != grupo.id_finca:
        return jsonify({'success': False, 'message': 'Animal no válido para este grupo'}), 400

    try:
        # Bloquear duplicidad: si el animal ya pertenece a cualquier grupo, no permitir asignarlo de nuevo
        relacion_existente = (db.session.query(AnimalGrupo)
                              .join(GrupoAnimal, AnimalGrupo.id_grupo == GrupoAnimal.id_grupo)
                              .filter(AnimalGrupo.id_animal == animal_id)
                              .first())
        if relacion_existente:
            return jsonify({'success': False, 'message': 'El animal ya pertenece a un grupo'}), 400

        # Asegurar también que no esté ya en este grupo (protección adicional)
        relacion_actual = AnimalGrupo.query.filter_by(id_animal=animal_id, id_grupo=grupo_id).first()
        if relacion_actual:
            return jsonify({'success': False, 'message': 'El animal ya está en el grupo'}), 400

        nueva = AnimalGrupo(id_animal=animal_id, id_grupo=grupo_id, fecha_asignacion=datetime.utcnow().date())
        db.session.add(nueva)
        db.session.commit()
        registrar_actividad('Asignó', f'Animal {animal.nombre_animal} al grupo {grupo.nombre_grupo}')
        return jsonify({'success': True, 'message': 'Animal agregado al grupo'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@login_required
def api_quitar_animal_de_grupo(grupo_id):
    """Quitar un animal del grupo seleccionado"""
    grupo = GrupoAnimal.query.get_or_404(grupo_id)
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=grupo.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'success': False, 'message': 'Sin permisos'}), 403

    data = request.json if request.is_json else request.form
    animal_id = int(data.get('animal_id', 0))
    if not animal_id:
        return jsonify({'success': False, 'message': 'animal_id requerido'}), 400

    try:
        relacion_actual = AnimalGrupo.query.filter_by(id_animal=animal_id, id_grupo=grupo_id).first()
        if not relacion_actual:
            return jsonify({'success': False, 'message': 'El animal no está en el grupo'}), 404

        # Quitar relación
        db.session.delete(relacion_actual)
        db.session.commit()

        animal = Animal.query.get(animal_id)
        nombre = animal.nombre_animal if animal else str(animal_id)
        registrar_actividad('Quitó', f'Animal {nombre} del grupo {grupo.nombre_grupo}')
        return jsonify({'success': True, 'message': 'Animal eliminado del grupo'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@login_required
def api_default_tipo_uso_potrero():
    """Devolver el tipo de uso por defecto para un potrero.
    Usa la última rotación registrada; si no hay, mapea desde el estado actual.
    """
    potrero_id = request.args.get('potrero_id', 0, type=int)
    if not potrero_id:
        return jsonify({'success': False, 'message': 'potrero_id requerido'}), 400

    potrero = Potrero.query.get(potrero_id)
    if not potrero:
        return jsonify({'success': False, 'message': 'Potrero no encontrado'}), 404

    # Verificar permisos sobre la finca del potrero
    relacion = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=potrero.id_finca).first()
    if not relacion and current_user.tipo_usuario != 3:
        return jsonify({'success': False, 'message': 'Sin permisos'}), 403

    try:
        ultima = (RotacionPotrero.query
                  .filter_by(id_potrero=potrero_id)
                  .order_by(RotacionPotrero.fecha_inicio.desc(), RotacionPotrero.id_rotacion.desc())
                  .first())
        if ultima and ultima.tipo_uso:
            default = ultima.tipo_uso
        else:
            # Mapear estado del potrero a un tipo de uso razonable
            if potrero.estado == 'activo':
                default = 'pastoreo'
            elif potrero.estado == 'descanso':
                default = 'descanso'
            else:
                default = 'mantenimiento'

        return jsonify({'success': True, 'potrero_id': potrero_id, 'default_tipo_uso': default})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500