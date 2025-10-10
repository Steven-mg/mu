from dotenv import load_dotenv
load_dotenv()  # Cargar variables de entorno

from flask import render_template, request, session, flash, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from forms.login_form import LoginForm
from flask_login import login_required, current_user, logout_user  # Añadir logout_user
from config import app, db
from modelo.models import Usuario, Finca, Animal, Reporte, ActividadReciente, UsuarioFinca, Potrero, RotacionPotrero, GrupoAnimal, Trabajador  # Agregar RotacionPotrero y GrupoAnimal
from controlador.controlador_actividad import obtener_actividades_recientes  # Importar la función
from datetime import datetime  # Añadir esta importación
from sqlalchemy import text

# Migración segura: asegurar columnas aplica_a_sexo en tablas de tipos de servicio
def ensure_aplica_a_sexo_columns():
    try:
        dialect = db.engine.dialect.name
        if dialect != 'mysql':
            print('Salto migración aplica_a_sexo: dialecto no MySQL ->', dialect)
            return
        with db.engine.connect() as conn:
            # Salud
            exists_salud = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'tipo_servicio_salud' 
                  AND COLUMN_NAME = 'aplica_a_sexo'
                """
            )).first()
            if not exists_salud:
                conn.execute(text(
                    """
                    ALTER TABLE tipo_servicio_salud 
                    ADD COLUMN aplica_a_sexo ENUM('macho','hembra','ambos') NULL DEFAULT 'ambos'
                    """
                ))
                print('Columna aplica_a_sexo agregada a tipo_servicio_salud')
            conn.execute(text("UPDATE tipo_servicio_salud SET aplica_a_sexo = 'ambos' WHERE aplica_a_sexo IS NULL"))

            # Sexual
            exists_sexual = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'tipo_servicio_sexual' 
                  AND COLUMN_NAME = 'aplica_a_sexo'
                """
            )).first()
            if not exists_sexual:
                conn.execute(text(
                    """
                    ALTER TABLE tipo_servicio_sexual 
                    ADD COLUMN aplica_a_sexo ENUM('macho','hembra','ambos') NULL DEFAULT 'ambos'
                    """
                ))
                print('Columna aplica_a_sexo agregada a tipo_servicio_sexual')
            conn.execute(text("UPDATE tipo_servicio_sexual SET aplica_a_sexo = 'ambos' WHERE aplica_a_sexo IS NULL"))
    except Exception as e:
        # No romper arranque; solo loguear
        print('Error asegurando aplica_a_sexo:', e)

# Migración segura: asegurar columnas de permisos por finca en usuario_finca
def ensure_usuario_finca_permission_columns():
    try:
        dialect = db.engine.dialect.name
        if dialect != 'mysql':
            print('Salto migración usuario_finca: dialecto no MySQL ->', dialect)
            return
        with db.engine.connect() as conn:
            # Verificar columna rol_en_finca
            exists_rol = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'usuario_finca' 
                  AND COLUMN_NAME = 'rol_en_finca'
                """
            )).first()
            if not exists_rol:
                conn.execute(text(
                    """
                    ALTER TABLE usuario_finca 
                    ADD COLUMN rol_en_finca SMALLINT NULL
                    """
                ))
                print('Columna rol_en_finca agregada a usuario_finca')

            # Verificar columna puede_editar
            exists_editar = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'usuario_finca' 
                  AND COLUMN_NAME = 'puede_editar'
                """
            )).first()
            if not exists_editar:
                conn.execute(text(
                    """
                    ALTER TABLE usuario_finca 
                    ADD COLUMN puede_editar TINYINT(1) NULL DEFAULT 0
                    """
                ))
                print('Columna puede_editar agregada a usuario_finca')

            # Verificar columna estado_asignacion
            exists_estado_asignacion = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'usuario_finca' 
                  AND COLUMN_NAME = 'estado_asignacion'
                """
            )).first()
            if not exists_estado_asignacion:
                conn.execute(text(
                    """
                    ALTER TABLE usuario_finca 
                    ADD COLUMN estado_asignacion ENUM('asignado','no_asignado') NOT NULL DEFAULT 'asignado'
                    """
                ))
                print('Columna estado_asignacion agregada a usuario_finca')
                # Inicializar estado_asignacion para filas existentes
                conn.execute(text("UPDATE usuario_finca SET estado_asignacion = 'asignado' WHERE estado_asignacion IS NULL"))
    except Exception as e:
        print('Error asegurando columnas usuario_finca:', e)

# Migración segura: agregar columna foto_usuario en tabla usuario si no existe
def ensure_foto_usuario_column():
    try:
        dialect = db.engine.dialect.name
        if dialect != 'mysql':
            print('Salto migración foto_usuario: dialecto no MySQL ->', dialect)
            return
        with db.engine.connect() as conn:
            exists_foto = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'usuario' 
                  AND COLUMN_NAME = 'foto_usuario'
                """
            )).first()
            if not exists_foto:
                conn.execute(text(
                    """
                    ALTER TABLE usuario 
                    ADD COLUMN foto_usuario LONGBLOB NULL
                    """
                ))
                print('Columna foto_usuario agregada a usuario')
    except Exception as e:
        print('Error asegurando columna foto_usuario:', e)

# Migración segura: crear tabla trabajador si no existe y asegurar índices/unique
def ensure_trabajador_table():
    try:
        dialect = db.engine.dialect.name
        if dialect != 'mysql':
            print('Salto migración trabajador: dialecto no MySQL ->', dialect)
            return
        with db.engine.connect() as conn:
            exists_tbl = conn.execute(text(
                """
                SELECT 1 FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador'
                """
            )).first()
            if not exists_tbl:
                conn.execute(text(
                    """
                    CREATE TABLE trabajador (
                      id INT AUTO_INCREMENT PRIMARY KEY,
                      usuario_id INT NOT NULL,
                      dueno_id INT NOT NULL,
                      fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
                      activo TINYINT(1) NOT NULL DEFAULT 1,
                      CONSTRAINT fk_trabajador_usuario FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE,
                      CONSTRAINT fk_trabajador_dueno FOREIGN KEY (dueno_id) REFERENCES usuario(id) ON DELETE CASCADE,
                      CONSTRAINT uq_trabajador_dueno_usuario UNIQUE (dueno_id, usuario_id)
                    )
                    """
                ))
                print('Tabla trabajador creada')

            # Asegurar columnas clave si la tabla ya existía pero sin ellas
            exists_usuario_col = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND COLUMN_NAME = 'usuario_id'
                """
            )).first()
            if not exists_usuario_col:
                conn.execute(text("ALTER TABLE trabajador ADD COLUMN usuario_id INT NULL"))
                print('Columna usuario_id agregada a trabajador')

            exists_dueno_col = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND COLUMN_NAME = 'dueno_id'
                """
            )).first()
            if not exists_dueno_col:
                conn.execute(text("ALTER TABLE trabajador ADD COLUMN dueno_id INT NULL"))
                print('Columna dueno_id agregada a trabajador')

            # Asegurar columna fecha_creacion para evitar errores 1054 al insertar
            exists_fecha_creacion = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND COLUMN_NAME = 'fecha_creacion'
                """
            )).first()
            if not exists_fecha_creacion:
                conn.execute(text(
                    """
                    ALTER TABLE trabajador 
                    ADD COLUMN fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    """
                ))
                print('Columna fecha_creacion agregada a trabajador')

            # Asegurar columna legacy activo para compatibilidad con el modelo
            exists_activo = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND COLUMN_NAME = 'activo'
                """
            )).first()
            if not exists_activo:
                conn.execute(text("ALTER TABLE trabajador ADD COLUMN activo TINYINT(1) NOT NULL DEFAULT 1"))
                print('Columna activo agregada a trabajador')

            # Mitigar columna legacy id_jefe (algunos esquemas antiguos la requieren NOT NULL)
            try:
                id_jefe_info = conn.execute(text(
                    """
                    SELECT IS_NULLABLE, COLUMN_DEFAULT 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'trabajador' 
                      AND COLUMN_NAME = 'id_jefe'
                    """
                )).first()
            except Exception:
                id_jefe_info = None

            if id_jefe_info:
                # Si existe y no permite NULL, flexibilizar para evitar 1364
                try:
                    if id_jefe_info[0] == 'NO':
                        conn.execute(text(
                            """
                            ALTER TABLE trabajador 
                            MODIFY COLUMN id_jefe INT NULL DEFAULT NULL
                            """
                        ))
                        print('Columna legacy id_jefe flexibilizada (NULL DEFAULT NULL)')
                except Exception:
                    pass
                # Opcional: backfill con dueno_id si está NULL para mayor compatibilidad
                try:
                    conn.execute(text("UPDATE trabajador SET id_jefe = dueno_id WHERE id_jefe IS NULL"))
                except Exception:
                    pass

            # Mitigar columna legacy usuario (evitar 1364 si es NOT NULL sin default)
            try:
                usuario_info = conn.execute(text(
                    """
                    SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'trabajador' 
                      AND COLUMN_NAME = 'usuario'
                    """
                )).first()
            except Exception:
                usuario_info = None

            if usuario_info:
                col_type, is_nullable, col_default = usuario_info
                try:
                    if is_nullable == 'NO':
                        conn.execute(text(
                            f"""
                            ALTER TABLE trabajador 
                            MODIFY COLUMN usuario {col_type} NULL DEFAULT NULL
                            """
                        ))
                        print('Columna legacy usuario flexibilizada (NULL DEFAULT NULL)')
                except Exception:
                    pass
                # Opcional: normalizar valores vacíos a NULL
                try:
                    conn.execute(text("UPDATE trabajador SET usuario = NULL WHERE usuario = ''"))
                except Exception:
                    pass

            # Asegurar llaves foráneas si faltan (no falla si ya existen)
            try:
                fk_usuario = conn.execute(text(
                    """
                    SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'trabajador' 
                      AND COLUMN_NAME = 'usuario_id' 
                      AND REFERENCED_TABLE_NAME = 'usuario'
                    """
                )).first()
                if not fk_usuario:
                    conn.execute(text("ALTER TABLE trabajador ADD CONSTRAINT fk_trabajador_usuario FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE"))
            except Exception:
                pass
            try:
                fk_dueno = conn.execute(text(
                    """
                    SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'trabajador' 
                      AND COLUMN_NAME = 'dueno_id' 
                      AND REFERENCED_TABLE_NAME = 'usuario'
                    """
                )).first()
                if not fk_dueno:
                    conn.execute(text("ALTER TABLE trabajador ADD CONSTRAINT fk_trabajador_dueno FOREIGN KEY (dueno_id) REFERENCES usuario(id) ON DELETE CASCADE"))
            except Exception:
                pass

            # Asegurar índices si faltan
            exists_ix_dueno = conn.execute(text(
                """
                SELECT 1 FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND INDEX_NAME = 'ix_trabajador_dueno_id'
                """
            )).first()
            if not exists_ix_dueno:
                conn.execute(text("CREATE INDEX ix_trabajador_dueno_id ON trabajador(dueno_id)"))
                print('Índice ix_trabajador_dueno_id agregado')

            exists_ix_usuario = conn.execute(text(
                """
                SELECT 1 FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND INDEX_NAME = 'ix_trabajador_usuario_id'
                """
            )).first()
            if not exists_ix_usuario:
                conn.execute(text("CREATE INDEX ix_trabajador_usuario_id ON trabajador(usuario_id)"))
                print('Índice ix_trabajador_usuario_id agregado')

            # Asegurar unique compuesto
            exists_uq = conn.execute(text(
                """
                SELECT 1 
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND CONSTRAINT_NAME = 'uq_trabajador_dueno_usuario' 
                  AND CONSTRAINT_TYPE = 'UNIQUE'
                """
            )).first()
            if not exists_uq:
                conn.execute(text("ALTER TABLE trabajador ADD UNIQUE KEY uq_trabajador_dueno_usuario (dueno_id, usuario_id)"))
                print('Unique uq_trabajador_dueno_usuario agregado')

            # Asegurar columna estado en esquema existente
            exists_estado = conn.execute(text(
                """
                SELECT 1 FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'trabajador' 
                  AND COLUMN_NAME = 'estado'
                """
            )).first()
            if not exists_estado:
                conn.execute(text(
                    """
                    ALTER TABLE trabajador 
                    ADD COLUMN estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo'
                    """
                ))
                print('Columna estado agregada a trabajador')
                # Migrar desde columna legacy activo si existe
                exists_activo_col = conn.execute(text(
                    """
                    SELECT 1 FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'trabajador' 
                      AND COLUMN_NAME = 'activo'
                    """
                )).first()
                if exists_activo_col:
                    conn.execute(text("UPDATE trabajador SET estado = 'activo' WHERE activo = 1"))
                    conn.execute(text("UPDATE trabajador SET estado = 'inactivo' WHERE activo = 0"))
    except Exception as e:
        print('Error asegurando tabla trabajador:', e)

# Crear todas las tablas en la base de datos
with app.app_context():
    db.create_all()
    print("Tablas creadas correctamente en la base de datos")
    # Ejecutar migración segura de columnas aplica_a_sexo
    ensure_aplica_a_sexo_columns()
    # Ejecutar migración segura de columnas de usuario_finca
    ensure_usuario_finca_permission_columns()
    # Ejecutar migración segura de foto_usuario
    ensure_foto_usuario_column()
    # Omitir migración de tabla trabajador para respetar esquema del dump
    
    # Importar e inicializar el usuario administrador
    from modelo.models import inicializar_usuario_admin
    inicializar_usuario_admin()

# Importar las funciones después de definir las rutas para evitar la importación circular
@app.route('/')
def pagina_inicio():
    return render_template('pages/inicio.html')

# Definir las rutas primero
@app.route('/dashboard/root')
def dashboard_root():
    # Obtener estadísticas desde la base de datos
    total_usuarios = Usuario.query.count()
    total_fincas = Finca.query.count()
    total_ganado = Animal.query.count()
    total_reportes = Reporte.query.count()
    
    # Obtener actividades recientes
    actividades_recientes = obtener_actividades_recientes(5)  # Obtener las 5 actividades más recientes
    
    return render_template('root/dashboard_root.html', 
                          total_usuarios=total_usuarios,
                          total_fincas=total_fincas,
                          total_ganado=total_ganado,
                          total_reportes=total_reportes,
                          actividades_recientes=actividades_recientes)  # Pasar actividades a la plantilla

# En la ruta del dashboard:
@app.route('/dashboard/dueno')
@login_required
def dashboard_dueno():
    # Obtener el usuario actual
    usuario_actual = Usuario.query.get(current_user.id)
    
    # Contar las fincas del usuario actual de forma eficiente (evita subconsulta pesada en MySQL)
    from sqlalchemy import func
    # Optimizado: usar subconsulta de las fincas del dueño con DISTINCT y COUNT
    fincas_dueno_subq = db.session.query(UsuarioFinca.finca_id).\
        filter(UsuarioFinca.usuario_id == current_user.id).distinct()
    total_fincas = db.session.query(func.count()).select_from(fincas_dueno_subq).scalar() or 0
    
    # Contar los animales en las fincas del usuario sin seleccionar todas las columnas
    # Optimizado: filtrar por fincas del dueño usando subconsulta y contar ids
    total_animales = db.session.query(func.count(Animal.id_animal)).\
        filter(Animal.id_finca.in_(fincas_dueno_subq)).scalar() or 0
    
    # Definir total_produccion (ajusta esto según tu modelo de datos)
    total_produccion = 0  # Inicializar con un valor predeterminado o calcular según tus necesidades
    
    # Contar trabajadores: preferir Trabajador con estado 'activo', fallback seguro a UsuarioFinca
    from sqlalchemy import func
    try:
        total_trabajadores = db.session.query(func.count(Trabajador.id_trabajador)).\
            filter(Trabajador.id_jefe == current_user.id, Trabajador.estado == 'activo').scalar() or 0
    except Exception:
        # Fallback: contar usuarios relacionados a fincas del dueño que no sean el dueño mismo
        total_trabajadores = db.session.query(func.count(UsuarioFinca.usuario_id)).\
            filter(
                UsuarioFinca.finca_id.in_(fincas_dueno_subq),
                UsuarioFinca.usuario_id != current_user.id
            ).scalar() or 0
    
    # Obtener actividades recientes del usuario
    actividades_recientes = ActividadReciente.query.filter_by(usuario_id=current_user.id).order_by(ActividadReciente.fecha.desc()).limit(5).all()
    
    # Añadir la fecha y hora actual
    now = datetime.now()
    
    return render_template('dueño/dashboard_dueno.html', 
                           total_fincas=total_fincas,
                           total_animales=total_animales,
                           total_produccion=total_produccion,
                           total_trabajadores=total_trabajadores,
                           now=now)

@app.route('/dashboard/trabajador')
def dashboard_trabajador():
    return render_template('trabajador-veternario/dashboard_trabajador.html')

# Ahora importar las funciones de autenticación
# Agregar después de la importación de controlador_autenticacion
from controlador.controlador_autenticacion import ruta_login, ruta_logout, requiere_rol, ruta_registro, configurar_google_oauth, google_login, cambiar_password

# Configurar Google OAuth
google_blueprint = configurar_google_oauth(app)

# Agregar la ruta de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    return ruta_registro()

# Y aplicar los decoradores después de importar
@app.route('/login', methods=['GET', 'POST'])
def login():
    return ruta_login()

@app.route('/logout')
def logout():
    return ruta_logout()

# Añadir ruta para el login con Google
@app.route('/login/google')
def login_google():
    return google_login()

# Ruta de cambio de contraseña obligatoria
@app.route('/cambiar-password', methods=['GET', 'POST'])
def cambiar_password_route():
    return cambiar_password()

# Importar controlador de usuarios
from controlador.controlador_usuario import listar_usuarios, crear_usuario, editar_usuario, eliminar_usuario_controlador

# Importar las funciones de gestión de animales
from controlador.controlador_animal import listar_animales, crear_animal, editar_animal, eliminar_animal, ver_animal, obtener_animales_por_finca, obtener_animales_por_sexo, get_potreros_por_finca, get_animales_disponibles, get_animales_potrero, asignar_animales_potrero, ver_foto_animal, ver_animales_finca, ver_animales_fuera, ver_animales_fuera_global, api_madurez_sexual_por_raza, documentos_geneticos, agregar_documento_genetico, ver_documento_genetico, descargar_documento_genetico, eliminar_documento_genetico, procedimientos_animal, eliminar_servicio_salud, eliminar_servicio_sexual
from controlador.controlador_animal import editar_documento_genetico

# Importar las funciones de gestión de fincas
from controlador.controlador_finca import (
    crear_finca, editar_finca, eliminar_finca, listar_fincas, gestionar_finca,
    obtener_fincas_usuario, ver_finca, crear_potrero, editar_potrero,
    eliminar_potrero, ver_potrero, agregar_animales_potrero,
    listar_grupos_finca, gestionar_grupo, api_agregar_animal_a_grupo, api_quitar_animal_de_grupo, eliminar_grupo
)
from controlador.controlador_finca import guardar_rotacion
from controlador.controlador_finca import api_default_tipo_uso_potrero

# Importar controlador de compras
from controlador.controlador_compra import *
from controlador.controlador_trabajador import listar_trabajadores_dueno, crear_trabajador_dueno, actualizar_permiso_trabajador, asignar_trabajador_finca, quitar_trabajador_finca
from controlador.controlador_trabajador_admin import ver_trabajador_admin, actualizar_trabajador_admin, ver_foto_usuario, eliminar_trabajador

# Aplicar los decoradores de rol a las rutas ya definidas
dashboard_root = requiere_rol(3)(dashboard_root)  # Solo accesible para rol 3 (root)
dashboard_dueno = requiere_rol(2)(dashboard_dueno)  # Accesible para roles 2 y 3
dashboard_trabajador = requiere_rol(1)(dashboard_trabajador)  # Accesible para roles 1, 2 y 3

# Rutas de gestión de usuarios (solo para admin)
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    return listar_usuarios()

@app.route('/admin/usuario/crear', methods=['GET', 'POST'])
@login_required
def crear_usuario_route():
    return crear_usuario()

@app.route('/admin/usuario/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario_route(usuario_id):
    return editar_usuario(usuario_id)

@app.route('/admin/usuario/<int:usuario_id>/eliminar', methods=['POST'])
@login_required
def eliminar_usuario_route(usuario_id):
    return eliminar_usuario_controlador(usuario_id)

# Ruta para eliminar un usuario (solo accesible para el administrador root)
@app.route('/admin/eliminar-usuario/<int:usuario_id>', methods=['POST'])
@login_required
def eliminar_usuario(usuario_id):
    # Verificar que el usuario actual es administrador (tipo_usuario = 3)
    if current_user.tipo_usuario != 3:
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # No permitir eliminar al superadmin
    if usuario.tipo_usuario == 3:
        flash('No se puede eliminar al administrador del sistema', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario {usuario.nik_name} eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'danger')
    
    return redirect(url_for('admin_usuarios'))

# Ruta para que un usuario elimine su propia cuenta
@app.route('/mi-cuenta/eliminar', methods=['POST'])
@login_required
def eliminar_mi_cuenta():
    try:
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        flash('Tu cuenta ha sido eliminada correctamente', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar tu cuenta: {str(e)}', 'danger')
        return redirect(url_for('mi_cuenta'))


# Rutas para gestión de animales
@app.route('/gestion_animales')
@login_required
def gestion_animales():
    return listar_animales()

@app.route('/finca/<int:finca_id>/animales')
@login_required
def ver_animales_finca_route(finca_id):
    return ver_animales_finca(finca_id)

@app.route('/finca/<int:finca_id>/animales-fuera')
@login_required
def ver_animales_fuera_route(finca_id):
    return ver_animales_fuera(finca_id)

@app.route('/animales-fuera', endpoint='ver_animales_fuera_global_route')
@login_required
def ver_animales_fuera_global_route():
    return ver_animales_fuera_global()

@app.route('/animal/crear', methods=['GET', 'POST'])
@login_required
def crear_animal_route():
    return crear_animal()

@app.route('/animal/<int:animal_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_animal_route(animal_id):
    return editar_animal(animal_id)

@app.route('/animal/<int:animal_id>/eliminar', methods=['POST'])
@login_required
def eliminar_animal_route(animal_id):
    return eliminar_animal(animal_id)

@app.route('/animal/<int:animal_id>')
@login_required
def ver_animal_route(animal_id):
    return ver_animal(animal_id)

# Procedimientos del animal (salud y sexuales)
@app.route('/animal/<int:animal_id>/procedimientos', endpoint='procedimientos_animal_route')
@login_required
def procedimientos_animal_route(animal_id):
    return procedimientos_animal(animal_id)

# Documentos genéticos
@app.route('/animal/<int:animal_id>/documentos_geneticos', endpoint='documentos_geneticos_route')
@login_required
def documentos_geneticos_route(animal_id):
    return documentos_geneticos(animal_id)

@app.route('/animal/<int:animal_id>/documentos_geneticos/agregar', methods=['GET', 'POST'], endpoint='agregar_documento_genetico_route')
@login_required
def agregar_documento_genetico_route(animal_id):
    return agregar_documento_genetico(animal_id)

@app.route('/documento_genetico/<int:documento_id>', endpoint='ver_documento_genetico_route')
@login_required
def ver_documento_genetico_route(documento_id):
    return ver_documento_genetico(documento_id)

# Descargar documento genético
@app.route('/documento_genetico/<int:documento_id>/descargar', endpoint='descargar_documento_genetico_route')
@login_required
def descargar_documento_genetico_route(documento_id):
    return descargar_documento_genetico(documento_id)

# Eliminar documento genético
@app.route('/documento_genetico/<int:documento_id>/eliminar', methods=['POST'], endpoint='eliminar_documento_genetico_route')
@login_required
def eliminar_documento_genetico_route(documento_id):
    return eliminar_documento_genetico(documento_id)

# Eliminar procedimientos
@app.route('/animal/<int:animal_id>/servicio_salud/<int:servicio_id>/eliminar', methods=['POST'], endpoint='eliminar_servicio_salud_route')
@login_required
def eliminar_servicio_salud_route(animal_id, servicio_id):
    return eliminar_servicio_salud(animal_id, servicio_id)

@app.route('/animal/<int:animal_id>/servicio_sexual/<int:servicio_id>/eliminar', methods=['POST'], endpoint='eliminar_servicio_sexual_route')
@login_required
def eliminar_servicio_sexual_route(animal_id, servicio_id):
    return eliminar_servicio_sexual(animal_id, servicio_id)

# Ruta para servir la foto del animal desde BD
@app.route('/animal/<int:animal_id>/foto')
@login_required
def ver_foto_animal_route(animal_id):
    return ver_foto_animal(animal_id)

# Ruta para servir la foto del usuario
@app.route('/usuario/<int:usuario_id>/foto')
@login_required
def ver_foto_usuario_route(usuario_id):
    return ver_foto_usuario(usuario_id)

# API endpoints para animales
@app.route('/api/animales/finca/<int:finca_id>')
@login_required
def api_animales_por_finca(finca_id):
    return obtener_animales_por_finca(finca_id)

@app.route('/api/animales/sexo/<sexo>')
@login_required
def api_animales_por_sexo(sexo):
    return obtener_animales_por_sexo(sexo)

@app.route('/api/potreros-por-finca')
@login_required
def api_potreros_por_finca():
    return get_potreros_por_finca()

@app.route('/api/potrero/default-tipo-uso')
@login_required
def api_default_tipo_uso_potrero_route():
    return api_default_tipo_uso_potrero()

# API para grupos activos por potrero
@app.route('/api/grupos-activos-por-potrero')
@login_required
def api_grupos_activos_por_potrero_route():
    return api_grupos_activos_por_potrero()

# API para grupos por finca (fallback)
@app.route('/api/grupos-por-finca')
@login_required
def api_grupos_por_finca_route():
    return api_grupos_por_finca()

# API para madurez sexual por raza
@app.route('/api/raza/<int:raza_id>/madurez-sexual')
@login_required
def api_madurez_sexual_por_raza_route(raza_id):
    return api_madurez_sexual_por_raza(raza_id)

# Endpoints adicionales para gestión de animales en potreros
@app.route('/api/animales-disponibles')
@login_required
def api_animales_disponibles():
    return get_animales_disponibles()

@app.route('/api/animales-potrero')
@login_required
def api_animales_potrero():
    return get_animales_potrero()

@app.route('/api/asignar-animales-potrero', methods=['POST'])
@login_required
def api_asignar_animales_potrero():
    return asignar_animales_potrero()

# Aplicar decoradores de rol a las rutas de gestión de usuarios
admin_usuarios = requiere_rol(3)(admin_usuarios)
crear_usuario_route = requiere_rol(3)(crear_usuario_route)
editar_usuario_route = requiere_rol(3)(editar_usuario_route)
eliminar_usuario_route = requiere_rol(3)(eliminar_usuario_route)

# Ruta para administración de fincas (solo para admin)
@app.route('/admin/fincas')
@login_required
@requiere_rol(3)
def admin_fincas():
    from modelo.models import Finca, Usuario, UsuarioFinca
    
    # Obtener todas las fincas con información del propietario a través de UsuarioFinca
    fincas = db.session.query(Finca, Usuario).join(
        UsuarioFinca, Finca.id_finca == UsuarioFinca.finca_id
    ).join(
        Usuario, UsuarioFinca.usuario_id == Usuario.id
    ).all()
    
    # Obtener todos los usuarios dueños de finca (tipo_usuario = 2)
    usuarios_duenos = Usuario.query.filter(Usuario.tipo_usuario == 2).all()
    
    # Estadísticas
    total_fincas = Finca.query.count()
    total_propietarios = db.session.query(Usuario.id).filter(Usuario.tipo_usuario == 2).count()
    
    return render_template('root/admin_fincas.html', 
                         fincas=fincas,
                         usuarios_duenos=usuarios_duenos,
                         total_fincas=total_fincas,
                         fincas_activas=total_fincas,  # Usar total_fincas ya que no hay campo estado
                         total_propietarios=total_propietarios)

# Rutas para gestión de fincas
@app.route('/crear-finca', methods=['GET', 'POST'])
@login_required
def crear_finca_route():
    return crear_finca()

@app.route('/mis-fincas')
@login_required
def mis_fincas():
    return listar_fincas()

@app.route('/finca/<int:finca_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_finca_route(finca_id):
    return editar_finca(finca_id)

@app.route('/finca/<int:finca_id>/eliminar', methods=['POST'])
@login_required
def eliminar_finca_route(finca_id):
    return eliminar_finca(finca_id)

@app.route('/finca/gestionar/<int:finca_id>')
@login_required
def gestionar_finca_route(finca_id):
    return gestionar_finca(finca_id)

@app.route('/obtener-fincas-usuario')
@login_required
def obtener_fincas_usuario_route():
    return obtener_fincas_usuario()

@app.route('/finca/<int:finca_id>')
@login_required
def ver_finca_route(finca_id):
    return ver_finca(finca_id)

# Rutas de gestión de potreros
@app.route('/finca/<int:finca_id>/potrero/crear', methods=['GET', 'POST'])
@login_required
def crear_potrero_route(finca_id):
    return crear_potrero(finca_id)

@app.route('/potrero/<int:potrero_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_potrero_route(potrero_id):
    return editar_potrero(potrero_id)

@app.route('/potrero/<int:potrero_id>/eliminar', methods=['POST'])
@login_required
def eliminar_potrero_route(potrero_id):
    return eliminar_potrero(potrero_id)

# Nuevas páginas de potrero
@app.route('/potrero/<int:potrero_id>/ver')
@login_required
def ver_potrero_route(potrero_id):
    return ver_potrero(potrero_id)

@app.route('/potrero/<int:potrero_id>/agregar-animales')
@login_required
def agregar_animales_potrero_route(potrero_id):
    return agregar_animales_potrero(potrero_id)

# Endpoint para guardar rotación desde el modal
@app.route('/guardar-rotacion', methods=['POST'])
@login_required
def guardar_rotacion_route():
    return guardar_rotacion()

# Gestión de grupos de animales
@app.route('/finca/<int:finca_id>/grupos', methods=['GET', 'POST'])
@login_required
def listar_grupos_finca_route(finca_id):
    return listar_grupos_finca(finca_id)

@app.route('/grupo/<int:grupo_id>/gestionar')
@login_required
def gestionar_grupo_route(grupo_id):
    return gestionar_grupo(grupo_id)

@app.route('/grupo/<int:grupo_id>/eliminar', methods=['POST'], endpoint='eliminar_grupo_route')
@login_required
def eliminar_grupo_route(grupo_id):
    return eliminar_grupo(grupo_id)

@app.route('/api/grupo/<int:grupo_id>/agregar-animal', methods=['POST'])
@login_required
def api_agregar_animal_a_grupo_route(grupo_id):
    return api_agregar_animal_a_grupo(grupo_id)

@app.route('/api/grupo/<int:grupo_id>/quitar-animal', methods=['POST'])
@login_required
def api_quitar_animal_de_grupo_route(grupo_id):
    return api_quitar_animal_de_grupo(grupo_id)

# Aplicar decoradores de rol a las rutas de gestión de animales
gestion_animales = requiere_rol(2)(gestion_animales)
crear_animal_route = requiere_rol(2)(crear_animal_route)
editar_animal_route = requiere_rol(2)(editar_animal_route)
eliminar_animal_route = requiere_rol(2)(eliminar_animal_route)
ver_animal_route = requiere_rol(2)(ver_animal_route)
procedimientos_animal_route = requiere_rol(2)(procedimientos_animal_route)
ver_foto_animal_route = requiere_rol(2)(ver_foto_animal_route)
documentos_geneticos_route = requiere_rol(2)(documentos_geneticos_route)
agregar_documento_genetico_route = requiere_rol(2)(agregar_documento_genetico_route)
ver_documento_genetico_route = requiere_rol(2)(ver_documento_genetico_route)
descargar_documento_genetico_route = requiere_rol(2)(descargar_documento_genetico_route)
eliminar_documento_genetico_route = requiere_rol(2)(eliminar_documento_genetico_route)
eliminar_servicio_salud_route = requiere_rol(2)(eliminar_servicio_salud_route)
eliminar_servicio_sexual_route = requiere_rol(2)(eliminar_servicio_sexual_route)

# Rutas de gestión de trabajadores (Dueño)
@app.route('/trabajadores')
@login_required
def gestionar_trabajadores_route():
    return listar_trabajadores_dueno()

@app.route('/trabajadores/crear', methods=['GET', 'POST'])
@login_required
def crear_trabajador_dueno_route():
    return crear_trabajador_dueno()

@app.route('/trabajadores/actualizar-permisos', methods=['POST'])
@login_required
def actualizar_permiso_trabajador_route():
    return actualizar_permiso_trabajador()

# Ruta y vista de administración de trabajador
@app.route('/trabajador/<int:usuario_id>/administrar', methods=['GET', 'POST'])
@login_required
@requiere_rol(2)
def administrar_trabajador_route(usuario_id):
    return ver_trabajador_admin(usuario_id) if request.method == 'GET' else actualizar_trabajador_admin(usuario_id)

# Eliminar trabajador
@app.route('/trabajador/<int:usuario_id>/eliminar', methods=['POST'], endpoint='eliminar_trabajador_route')
@login_required
@requiere_rol(2)
def eliminar_trabajador_route(usuario_id):
    return eliminar_trabajador(usuario_id)

# Aplicar decoradores de rol a rutas de trabajadores
gestionar_trabajadores_route = requiere_rol(2)(gestionar_trabajadores_route)
crear_trabajador_dueno_route = requiere_rol(2)(crear_trabajador_dueno_route)
actualizar_permiso_trabajador_route = requiere_rol(2)(actualizar_permiso_trabajador_route)
ver_foto_usuario_route = requiere_rol(1)(ver_foto_usuario_route)

# Asignar/Quitar trabajador en finca
@app.route('/finca/<int:finca_id>/trabajador/<int:usuario_id>/asignar', methods=['POST'])
@login_required
@requiere_rol(2)
def asignar_trabajador_finca_route(finca_id, usuario_id):
    return asignar_trabajador_finca(finca_id, usuario_id)

@app.route('/finca/<int:finca_id>/trabajador/<int:usuario_id>/quitar', methods=['POST'])
@login_required
@requiere_rol(2)
def quitar_trabajador_finca_route(finca_id, usuario_id):
    return quitar_trabajador_finca(finca_id, usuario_id)

# Editar documento genético
@app.route('/documento_genetico/<int:documento_id>/editar', methods=['GET', 'POST'], endpoint='editar_documento_genetico_route')
@login_required
def editar_documento_genetico_route(documento_id):
    return editar_documento_genetico(documento_id)

editar_documento_genetico_route = requiere_rol(2)(editar_documento_genetico_route)
ver_animales_finca_route = requiere_rol(2)(ver_animales_finca_route)
ver_animales_fuera_route = requiere_rol(2)(ver_animales_fuera_route)
ver_animales_fuera_global_route = requiere_rol(2)(ver_animales_fuera_global_route)
api_animales_por_finca = requiere_rol(2)(api_animales_por_finca)
api_animales_por_sexo = requiere_rol(2)(api_animales_por_sexo)
api_animales_disponibles = requiere_rol(2)(api_animales_disponibles)
api_animales_potrero = requiere_rol(2)(api_animales_potrero)
api_asignar_animales_potrero = requiere_rol(2)(api_asignar_animales_potrero)
api_default_tipo_uso_potrero_route = requiere_rol(2)(api_default_tipo_uso_potrero_route)
api_madurez_sexual_por_raza_route = requiere_rol(2)(api_madurez_sexual_por_raza_route)

# Aplicar decoradores de rol a las rutas de gestión de fincas
crear_finca_route = requiere_rol(2)(crear_finca_route)
mis_fincas = requiere_rol(2)(mis_fincas)
editar_finca_route = requiere_rol(2)(editar_finca_route)
eliminar_finca_route = requiere_rol(2)(eliminar_finca_route)
gestionar_finca_route = requiere_rol(2)(gestionar_finca_route)
obtener_fincas_usuario_route = requiere_rol(2)(obtener_fincas_usuario_route)
ver_finca_route = requiere_rol(2)(ver_finca_route)

# Aplicar decoradores de rol a las rutas de gestión de potreros
crear_potrero_route = requiere_rol(2)(crear_potrero_route)
editar_potrero_route = requiere_rol(2)(editar_potrero_route)
eliminar_potrero_route = requiere_rol(2)(eliminar_potrero_route)
ver_potrero_route = requiere_rol(2)(ver_potrero_route)
agregar_animales_potrero_route = requiere_rol(2)(agregar_animales_potrero_route)
guardar_rotacion_route = requiere_rol(2)(guardar_rotacion_route)
listar_grupos_finca_route = requiere_rol(2)(listar_grupos_finca_route)
gestionar_grupo_route = requiere_rol(2)(gestionar_grupo_route)
api_agregar_animal_a_grupo_route = requiere_rol(2)(api_agregar_animal_a_grupo_route)
api_quitar_animal_de_grupo_route = requiere_rol(2)(api_quitar_animal_de_grupo_route)
api_grupos_activos_por_potrero_route = requiere_rol(2)(api_grupos_activos_por_potrero_route)
api_grupos_por_finca_route = requiere_rol(2)(api_grupos_por_finca_route)
eliminar_grupo_route = requiere_rol(2)(eliminar_grupo_route)

# Eliminada: Ruta /guardar-potrero que procesaba el formulario modal mediante AJAX
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
    
    

