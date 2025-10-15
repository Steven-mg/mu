import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from config import db, allowed_image
from modelo.models import Usuario, UsuarioFinca, Finca, Trabajador, PermisoFincaUsuario
from forms.trabajador_form import TrabajadorForm
from controlador.controlador_actividad import registrar_actividad
from sqlalchemy import text
from werkzeug.security import generate_password_hash
from datetime import datetime

@login_required
def listar_trabajadores_dueno():
    # Fincas del dueño actual
    fincas_dueno = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    finca_ids = [f.id_finca for f in fincas_dueno]
    # Debug
    try:
        print(f"[Trabajadores] Usuario actual: {current_user.id}")
        print(f"[Trabajadores] Fincas del dueño: {len(fincas_dueno)} -> {finca_ids}")
    except Exception:
        pass

    # Usuarios relacionados a esas fincas como trabajadores o veterinarios
    relaciones = UsuarioFinca.query.filter(
        UsuarioFinca.finca_id.in_(finca_ids),
        UsuarioFinca.usuario_id != current_user.id  # Excluir relación del dueño
    ).all() if finca_ids else []
    try:
        print(f"[Trabajadores] Relaciones encontradas: {len(relaciones)}")
    except Exception:
        pass
    usuario_ids = list({rel.usuario_id for rel in relaciones})
    trabajadores = Usuario.query.filter(Usuario.id.in_(usuario_ids)).all() if usuario_ids else []
    # Mapear documento por usuario usando tabla legacy trabajador
    documentos_map = {}
    try:
        registros = Trabajador.query.filter_by(id_jefe=current_user.id).all()
        doc_por_nik = {t.usuario: t.documento for t in registros}
        for u in trabajadores:
            documentos_map[u.id] = doc_por_nik.get(u.nik_name)
    except Exception:
        documentos_map = {}
    try:
        print(f"[Trabajadores] Usuarios relacionados: {len(trabajadores)} -> {usuario_ids}")
    except Exception:
        pass

    # Trabajadores/Veterinarios sin asignación a ninguna finca
    try:
        subq = db.session.query(UsuarioFinca.usuario_id).distinct()
        trabajadores_sin_asignacion = Usuario.query.filter(
            Usuario.tipo_usuario == 1,
            ~Usuario.id.in_(subq)
        ).all()
        for u in trabajadores_sin_asignacion:
            if u.id not in documentos_map:
                documentos_map[u.id] = doc_por_nik.get(u.nik_name) if 'doc_por_nik' in locals() else None
        print(f"[Trabajadores] Sin asignación: {len(trabajadores_sin_asignacion)}")
    except Exception:
        trabajadores_sin_asignacion = []

    return render_template('dueño/gestionar_trabajadores.html', fincas=fincas_dueno, trabajadores=trabajadores, relaciones=relaciones, trabajadores_sin_asignacion=trabajadores_sin_asignacion, documentos_map=documentos_map)

@login_required
def crear_trabajador_dueno():
    form = TrabajadorForm()
    # Limitar fincas a las del dueño
    fincas_dueno = Finca.query.join(UsuarioFinca).filter(UsuarioFinca.usuario_id == current_user.id).all()
    # Incluir opción de no asignar aún
    form.finca_id.choices = [(0, 'Sin asignar')] + [(f.id_finca, f.nombre_finca) for f in fincas_dueno]

    # Contexto de relaciones actuales para listar en la misma vista
    finca_ids = [f.id_finca for f in fincas_dueno]
    relaciones = UsuarioFinca.query.filter(
        UsuarioFinca.finca_id.in_(finca_ids),
        UsuarioFinca.usuario_id != current_user.id
    ).all() if finca_ids else []
    usuario_ids = list({rel.usuario_id for rel in relaciones})
    trabajadores = Usuario.query.filter(Usuario.id.in_(usuario_ids)).all() if usuario_ids else []

    # Mapear documento por usuario usando tabla legacy trabajador
    documentos_map = {}
    try:
        registros = Trabajador.query.filter_by(id_jefe=current_user.id).all()
        doc_por_nik = {t.usuario: t.documento for t in registros}
        for u in trabajadores:
            documentos_map[u.id] = doc_por_nik.get(u.nik_name)
    except Exception:
        documentos_map = {}

    if form.validate_on_submit():
        # Validar duplicado de nickname por dueño en tabla legacy Trabajador
        try:
            existente = Trabajador.query.\
                filter(Trabajador.id_jefe == current_user.id, db.func.lower(Trabajador.usuario) == (form.nik_name.data or '').lower()).first()
        except Exception:
            existente = None
        if existente:
            flash('Ya existe un trabajador con ese nickname creado por ti.', 'warning')
            return redirect(url_for('gestionar_trabajadores_route'))

        # Crear o reutilizar usuario base tipo 1 (Trabajador/Veterinario)
        usuario = Usuario.query.filter_by(nik_name=form.nik_name.data).first()
        if not usuario:
            usuario = Usuario(
                nik_name=form.nik_name.data,
                nombres=form.nombres.data or None,
                apellidos=form.apellidos.data or None,
                # Correo no puede ser nulo en la BD: usar fallback si no se suministra
                correo=(form.correo.data or f"{form.nik_name.data}@no-email.local"),
                telefono=form.telefono.data or None,
                tipo_usuario=1,
                contraseña=generate_password_hash('0000')
            )
            db.session.add(usuario)
            db.session.flush()  # obtener id
        else:
            # Si el usuario existe y es el dueño actual, bloquear asignación
            if usuario.id == current_user.id:
                flash('No puedes asignarte como trabajador en tus propias fincas.', 'danger')
                return redirect(url_for('gestionar_trabajadores_route'))
            # Asegurar que sea tipo trabajador/veterinario
            if usuario.tipo_usuario != 1:
                usuario.tipo_usuario = 1
            # Actualizar correo si el formulario lo trae y es diferente al actual
            try:
                nuevo_correo = (form.correo.data or '').strip()
                if nuevo_correo and nuevo_correo.lower() != (usuario.correo or '').lower():
                    # Validar unicidad del correo en usuarios
                    conflicto = Usuario.query.filter(Usuario.correo == nuevo_correo, Usuario.id != usuario.id).first()
                    if conflicto:
                        flash('El correo proporcionado ya está en uso por otro usuario.', 'danger')
                        return redirect(url_for('gestionar_trabajadores_route'))
                    usuario.correo = nuevo_correo
            except Exception:
                # Si algo falla en la validación, no bloquear el flujo de creación
                pass

        # Foto opcional del usuario
        try:
            if 'foto' in request.files:
                archivo = request.files['foto']
                if archivo and archivo.filename:
                    if allowed_image(archivo.filename):
                        usuario.foto_usuario = archivo.read()
                    else:
                        flash('Formato de imagen no permitido', 'danger')
        except Exception:
            # En caso de error de lectura, continuar sin bloquear creación
            flash('No se pudo procesar la imagen enviada', 'warning')

        # Insertar en tabla legacy `trabajador` mediante el modelo
        try:
            reg = Trabajador(
                id_jefe=current_user.id,
                usuario=usuario.nik_name,
                nombre=usuario.nombres or '',
                apellido=usuario.apellidos or '',
                documento=form.documento.data,
                telefono=usuario.telefono,
                correo=usuario.correo,
                rol=form.rol.data,
                estado='activo'
            )
            db.session.add(reg)
        except Exception as e:
            try:
                flash(f'Advertencia: no se insertó en tabla trabajador: {str(e)}', 'warning')
            except Exception:
                pass

        # Asignación opcional de finca
        if form.finca_id.data and int(form.finca_id.data) != 0:
            relacion = UsuarioFinca.query.filter_by(usuario_id=usuario.id, finca_id=form.finca_id.data).first()
            if not relacion:
                relacion = UsuarioFinca(usuario_id=usuario.id, finca_id=form.finca_id.data)
                db.session.add(relacion)

            relacion.rol_en_finca = form.rol_en_finca.data or 1
            relacion.puede_editar = bool(form.puede_editar.data)
            # Marcar estado de asignación
            try:
                relacion.estado_asignacion = 'asignado'
            except Exception:
                pass

            db.session.commit()
            registrar_actividad('Creó', f'Trabajador {usuario.nik_name} ligado al dueño y asignado a finca {relacion.finca_id}')
            flash('Trabajador/Veterinario creado y asignado correctamente', 'success')
        else:
            # Solo crear usuario sin asignar a finca
            db.session.commit()
            registrar_actividad('Creó', f'Trabajador {usuario.nik_name} ligado al dueño sin asignación de finca')
            flash('Trabajador/Veterinario creado sin asignación de finca. Puedes asignarlo más tarde.', 'info')

        return redirect(url_for('gestionar_trabajadores_route'))

    # También mostrar trabajadores sin asignación en esta vista
    try:
        subq = db.session.query(UsuarioFinca.usuario_id).distinct()
        trabajadores_sin_asignacion = Usuario.query.filter(
            Usuario.tipo_usuario == 1,
            ~Usuario.id.in_(subq)
        ).all()
        for u in trabajadores_sin_asignacion:
            if u.id not in documentos_map:
                documentos_map[u.id] = doc_por_nik.get(u.nik_name) if 'doc_por_nik' in locals() else None
    except Exception:
        trabajadores_sin_asignacion = []

    return render_template('dueño/gestionar_trabajadores.html', form=form, fincas=fincas_dueno, trabajadores=trabajadores, relaciones=relaciones, trabajadores_sin_asignacion=trabajadores_sin_asignacion, documentos_map=documentos_map)

@login_required
def actualizar_permiso_trabajador():
    usuario_id = request.form.get('usuario_id', type=int)
    finca_id = request.form.get('finca_id', type=int)
    puede_editar = request.form.get('puede_editar') == 'true'
    estado_asignacion = request.form.get('estado_asignacion')
    rol_en_finca = request.form.get('rol_en_finca', type=int)

    # Bloquear intentos de cambiar permisos/rol del dueño en su propia finca
    if usuario_id == current_user.id:
        flash('El dueño no puede tener rol de trabajador en sus propias fincas.', 'danger')
        return redirect(url_for('gestionar_trabajadores_route'))

    relacion = UsuarioFinca.query.filter_by(usuario_id=usuario_id, finca_id=finca_id).first()
    if not relacion:
        flash('Relación trabajador-finca no encontrada', 'danger')
        return redirect(url_for('gestionar_trabajadores_route'))

    # Validar que el dueño esté editando su propia finca
    dueno_rel = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not dueno_rel and current_user.tipo_usuario != 3:
        flash('No tienes permisos para modificar esta finca', 'danger')
        return redirect(url_for('gestionar_trabajadores_route'))

    relacion.puede_editar = puede_editar
    # Actualizar estado de asignación si es válido
    if estado_asignacion in ('asignado', 'no_asignado'):
        try:
            relacion.estado_asignacion = estado_asignacion
        except Exception:
            pass
    if rol_en_finca in (1, 2, 3):
        relacion.rol_en_finca = rol_en_finca
    db.session.commit()
    registrar_actividad('Actualizó', f'Permisos de usuario {usuario_id} en finca {finca_id}')
    return redirect(url_for('gestionar_trabajadores_route'))

@login_required
def asignar_trabajador_finca(finca_id: int, usuario_id: int):
    """Asignar un trabajador/veterinario a una finca del dueño actual."""
    # Validar que el dueño tenga acceso a la finca
    dueno_rel = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not dueno_rel and current_user.tipo_usuario != 3:
        flash('No tienes permisos para modificar esta finca', 'danger')
        return redirect(url_for('gestionar_finca_route', finca_id=finca_id))

    # No permitir asignar al propio dueño como trabajador
    if usuario_id == current_user.id:
        flash('El dueño no puede asignarse como trabajador en su propia finca.', 'danger')
        return redirect(url_for('gestionar_finca_route', finca_id=finca_id))

    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.tipo_usuario != 1:
        # Asegurar que sea trabajador/veterinario
        usuario.tipo_usuario = 1
        db.session.add(usuario)

    # Crear relación si no existe
    relacion = UsuarioFinca.query.filter_by(usuario_id=usuario_id, finca_id=finca_id).first()
    if not relacion:
        relacion = UsuarioFinca(usuario_id=usuario_id, finca_id=finca_id)
        db.session.add(relacion)

    # Valores por defecto al asignar
    try:
        relacion.estado_asignacion = 'asignado'
    except Exception:
        pass
    if not relacion.rol_en_finca:
        relacion.rol_en_finca = 1  # Trabajador por defecto
    relacion.puede_editar = bool(relacion.puede_editar)

    db.session.commit()
    registrar_actividad('Asignó', f'Usuario {usuario.nik_name} a finca {finca_id}')
    flash('Trabajador asignado a la finca correctamente', 'success')
    return redirect(url_for('gestionar_finca_route', finca_id=finca_id))


# === Página dedicada: Administrar trabajadores de una finca ===
@login_required
def gestionar_trabajadores_finca(finca_id: int):
    """Página dedicada para administrar los trabajadores de una finca específica."""
    # Validar acceso del dueño a la finca
    dueno_rel = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not dueno_rel and current_user.tipo_usuario != 3:
        flash('No tienes permisos para administrar esta finca', 'danger')
        return redirect(url_for('mis_fincas'))

    finca = Finca.query.get_or_404(finca_id)

    # Relaciones de trabajadores asignados a esta finca (excluye dueño)
    relaciones_trabajadores = UsuarioFinca.query.filter(
        UsuarioFinca.finca_id == finca_id,
        UsuarioFinca.usuario_id != current_user.id
    ).all()

    usuario_ids = [rel.usuario_id for rel in relaciones_trabajadores]
    usuarios_asignados = Usuario.query.filter(Usuario.id.in_(usuario_ids)).all() if usuario_ids else []

    # Map de documentos desde tabla legacy Trabajador
    documentos_map = {}
    try:
        registros = Trabajador.query.filter_by(id_jefe=current_user.id).all()
        doc_por_nik = {t.usuario: t.documento for t in registros}
        for u in usuarios_asignados:
            documentos_map[u.id] = doc_por_nik.get(u.nik_name)
    except Exception:
        documentos_map = {}

    # Listas auxiliares para agregar
    trabajadores_sin_asignacion = []
    trabajadores_con_otras_fincas = []
    try:
        nik_names = [t.usuario for t in registros if t.usuario] if 'registros' in locals() else []
        trabajadores_dueno = Usuario.query.filter(
            Usuario.tipo_usuario == 1,
            Usuario.nik_name.in_(nik_names)
        ).all() if nik_names else []

        for u in trabajadores_dueno:
            rels_usuario = UsuarioFinca.query.filter_by(usuario_id=u.id).all()
            if not rels_usuario:
                trabajadores_sin_asignacion.append(u)
            else:
                asignado_en_esta = any(r.finca_id == finca_id for r in rels_usuario)
                if not asignado_en_esta:
                    trabajadores_con_otras_fincas.append(u)
            if u.id not in documentos_map:
                documentos_map[u.id] = doc_por_nik.get(u.nik_name) if 'doc_por_nik' in locals() else None
    except Exception:
        trabajadores_sin_asignacion = []
        trabajadores_con_otras_fincas = []

    return render_template(
        'dueño/trabajadores_finca.html',
        finca=finca,
        relaciones_trabajadores=relaciones_trabajadores,
        usuarios_asignados=usuarios_asignados,
        documentos_map=documentos_map,
        trabajadores_sin_asignacion=trabajadores_sin_asignacion,
        trabajadores_con_otras_fincas=trabajadores_con_otras_fincas
    )


# === Permisos por funcionalidad (por finca y trabajador) ===
@login_required
def obtener_permisos_finca_trabajador(finca_id: int, usuario_id: int):
    # Validación de acceso del dueño a la finca
    dueno_rel = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not dueno_rel and current_user.tipo_usuario != 3:
        return jsonify({"ok": False, "message": "Sin permisos para esta finca"}), 403

    rel = UsuarioFinca.query.filter_by(usuario_id=usuario_id, finca_id=finca_id).first()
    if not rel:
        return jsonify({"ok": False, "message": "Trabajador no asignado a esta finca"}), 404

    # Mapear usuario -> trabajador del dueño actual
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"ok": False, "message": "Usuario no encontrado"}), 404
    trab = Trabajador.query.filter_by(usuario=usuario.nik_name, id_jefe=current_user.id).first()
    if not trab:
        return jsonify({"ok": False, "message": "Trabajador no encontrado para este dueño"}), 404

    permisos = PermisoFincaUsuario.query.filter_by(trabajador_id=trab.id_trabajador, finca_id=finca_id).first()
    if not permisos:
        permisos = PermisoFincaUsuario(trabajador_id=trab.id_trabajador, finca_id=finca_id)
        db.session.add(permisos)
        db.session.commit()

    return jsonify({
        "ok": True,
        "crear_potreros": bool(permisos.crear_potreros),
        "agregar_animales": bool(permisos.agregar_animales),
        "eliminar_animales": bool(permisos.eliminar_animales),
        "crear_usuarios_ligados": bool(permisos.crear_usuarios_ligados),
        "actualizar_datos_usuario": bool(permisos.actualizar_datos_usuario),
    })


@login_required
def actualizar_permiso_finca_trabajador():
    data = request.get_json(force=True) or {}
    usuario_id = int(data.get('usuario_id'))
    finca_id = int(data.get('finca_id'))
    permiso = str(data.get('permiso') or '')
    habilitado = bool(data.get('habilitado'))

    # Validación de acceso
    dueno_rel = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not dueno_rel and current_user.tipo_usuario != 3:
        return jsonify({"ok": False, "message": "Sin permisos para esta finca"}), 403

    rel = UsuarioFinca.query.filter_by(usuario_id=usuario_id, finca_id=finca_id).first()
    if not rel:
        return jsonify({"ok": False, "message": "Trabajador no asignado a esta finca"}), 404

    # Mapear usuario -> trabajador del dueño actual
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({"ok": False, "message": "Usuario no encontrado"}), 404
    trab = Trabajador.query.filter_by(usuario=usuario.nik_name, id_jefe=current_user.id).first()
    if not trab:
        return jsonify({"ok": False, "message": "Trabajador no encontrado para este dueño"}), 404

    permisos = PermisoFincaUsuario.query.filter_by(trabajador_id=trab.id_trabajador, finca_id=finca_id).first()
    if not permisos:
        permisos = PermisoFincaUsuario(trabajador_id=trab.id_trabajador, finca_id=finca_id)
        db.session.add(permisos)

    # Actualizar campo dinámico si existe
    campos_validos = {
        'crear_potreros',
        'agregar_animales',
        'eliminar_animales',
        'crear_usuarios_ligados',
        'actualizar_datos_usuario'
    }
    if permiso not in campos_validos:
        return jsonify({"ok": False, "message": "Permiso inválido"}), 400

    setattr(permisos, permiso, habilitado)
    db.session.commit()
    registrar_actividad('Actualizó', f'Permiso {permiso} de trabajador {trab.id_trabajador} en finca {finca_id} -> {habilitado}')
    return jsonify({"ok": True})

@login_required
def quitar_trabajador_finca(finca_id: int, usuario_id: int):
    """Quitar (desasignar) un trabajador/veterinario de una finca del dueño actual."""
    # Validar que el dueño tenga acceso a la finca
    dueno_rel = UsuarioFinca.query.filter_by(usuario_id=current_user.id, finca_id=finca_id).first()
    if not dueno_rel and current_user.tipo_usuario != 3:
        flash('No tienes permisos para modificar esta finca', 'danger')
        return redirect(url_for('gestionar_finca_route', finca_id=finca_id))

    # No permitir quitar al propio dueño
    if usuario_id == current_user.id:
        flash('El dueño no es un trabajador de la finca.', 'warning')
        return redirect(url_for('gestionar_finca_route', finca_id=finca_id))

    relacion = UsuarioFinca.query.filter_by(usuario_id=usuario_id, finca_id=finca_id).first()
    if not relacion:
        flash('El usuario no está asignado a esta finca.', 'info')
        return redirect(url_for('gestionar_finca_route', finca_id=finca_id))

    try:
        db.session.delete(relacion)
        db.session.commit()
        registrar_actividad('Quitó', f'Usuario {usuario_id} de finca {finca_id}')
        flash('Trabajador quitado de la finca', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al quitar trabajador: {str(e)}', 'danger')

    return redirect(url_for('gestionar_finca_route', finca_id=finca_id))