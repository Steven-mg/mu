from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from modelo.models import db, Usuario, UsuarioFinca, Trabajador
from config import allowed_image
from io import BytesIO

try:
    from PIL import Image
except Exception:
    Image = None


def _guess_mime_type(blob: bytes):
    if Image is None or not blob:
        return 'image/jpeg'
    try:
        im = Image.open(BytesIO(blob))
        fmt = (im.format or '').lower()
        if fmt == 'png':
            return 'image/png'
        if fmt == 'gif':
            return 'image/gif'
        return 'image/jpeg'
    except Exception:
        return 'image/jpeg'


def _stream_blob(blob: bytes):
    if not blob:
        abort(404)
    mime = _guess_mime_type(blob)
    return blob, 200, {'Content-Type': mime}


def ver_foto_usuario(usuario_id: int):
    user = Usuario.query.get_or_404(usuario_id)
    # Permisos: el dueño y el propio usuario o superusuario
    if not (current_user.tipo_usuario in (2, 3) or current_user.id == user.id):
        abort(403)
    return _stream_blob(user.foto_usuario)


def ver_trabajador_admin(usuario_id: int):
    user = Usuario.query.get_or_404(usuario_id)
    if current_user.tipo_usuario not in (2, 3):
        abort(403)
    # Relación Trabajador con el dueño actual, si existe
    rel_trab = Trabajador.query.filter_by(usuario=user.nik_name, id_jefe=current_user.id).first()
    return render_template('dueño/administrar_trabajador.html', usuario=user, trabajador_rel=rel_trab)


def actualizar_trabajador_admin(usuario_id: int):
    user = Usuario.query.get_or_404(usuario_id)
    if current_user.tipo_usuario not in (2, 3):
        abort(403)

    # Actualizar datos básicos
    user.nombres = request.form.get('nombres', user.nombres)
    user.apellidos = request.form.get('apellidos', user.apellidos)
    user.telefono = request.form.get('telefono', user.telefono)

    # Foto
    if 'foto' in request.files:
        foto = request.files['foto']
        if foto and (foto.filename and allowed_image(foto.filename)):
            user.foto_usuario = foto.read()
        elif foto and foto.filename:
            flash('Formato de imagen no permitido', 'danger')

    # Cambiar estado general del trabajador respecto al dueño
    nuevo_estado = request.form.get('estado')
    if nuevo_estado in ('activo', 'inactivo'):
        try:
            rel_trab = Trabajador.query.filter_by(usuario=user.nik_name, id_jefe=current_user.id).first()
            if rel_trab:
                rel_trab.estado = nuevo_estado
                # Si se inactiva, desasignar de todas las fincas del dueño
                if nuevo_estado == 'inactivo':
                    UsuarioFinca.query.filter(UsuarioFinca.usuario_id == user.id).update({UsuarioFinca.estado_asignacion: 'no_asignado'})
        except Exception:
            pass

    db.session.commit()
    flash('Trabajador actualizado', 'success')
    return redirect(url_for('administrar_trabajador_route', usuario_id=usuario_id))


def eliminar_trabajador(usuario_id: int):
    """Eliminar un trabajador (usuario tipo 1) y sus relaciones con fincas.
    Solo permitido para dueños (2) o admin (3). No elimina dueños ni admin.
    """
    user = Usuario.query.get_or_404(usuario_id)
    if current_user.tipo_usuario not in (2, 3):
        abort(403)

    if user.tipo_usuario != 1:
        flash('Solo se pueden eliminar cuentas de trabajadores/veterinarios', 'danger')
        return redirect(url_for('administrar_trabajador_route', usuario_id=usuario_id))

    try:
        # Eliminar relaciones con fincas (cascade por FK, pero asegurar explícito)
        UsuarioFinca.query.filter_by(usuario_id=user.id).delete()
        # Eliminar registro legacy en la tabla `trabajador` asociado al dueño
        try:
            Trabajador.query.filter_by(usuario=user.nik_name).delete()
        except Exception:
            pass
        db.session.delete(user)
        db.session.commit()
        flash(f'Trabajador {user.nik_name} eliminado correctamente', 'success')
        return redirect(url_for('gestionar_trabajadores_route'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar trabajador: {str(e)}', 'danger')
        return redirect(url_for('administrar_trabajador_route', usuario_id=usuario_id))