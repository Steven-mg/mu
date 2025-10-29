from datetime import datetime
from sqlalchemy import ForeignKey, SmallInteger, DECIMAL, Text
from sqlalchemy.orm import backref, relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from config import db

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    __table_args__ = (
        db.UniqueConstraint('nik_name', name='uq_usuario_nik_name'),
        db.UniqueConstraint('correo', name='uq_usuario_correo'),
        db.Index('ix_usuario_tipo_usuario', 'tipo_usuario'),
    )

    id = db.Column(db.Integer, primary_key=True) 
    nik_name = db.Column(db.String(50), nullable=False)  
    nombres = db.Column(db.String(50), nullable=True)  
    apellidos = db.Column(db.String(50), nullable=True)  
    correo = db.Column(db.String(120), nullable=False)  
    contraseña = db.Column(db.String(255), nullable=True) 
    tipo_usuario = db.Column(db.SmallInteger, nullable=False)  # 1: Trabajador/Veterinario, 2: Dueño, 3: Superusuario
    direccion = db.Column(db.String(30), nullable=True) 
    telefono = db.Column(db.String(15), nullable=True)
    pais = db.Column(db.String(50), nullable=True)
    departamento = db.Column(db.String(50), nullable=True)
    ciudad = db.Column(db.String(50), nullable=True)
    # Foto del usuario almacenada como binario
    foto_usuario = db.Column(db.LargeBinary, nullable=True)
    fincas = db.relationship('Finca', secondary='usuario_finca', backref='usuarios')

class Trabajador(db.Model):
    __tablename__ = 'trabajador'
    __table_args__ = (
        db.UniqueConstraint('usuario', name='usuario_unique'),
        db.UniqueConstraint('documento', name='documento_unique'),
        db.Index('ix_trabajador_id_jefe', 'id_jefe'),
    )

    id_trabajador = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_jefe = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    correo = db.Column(db.String(100), nullable=True)
    rol = db.Column(db.Enum('administrador', 'operario', 'veterinario'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    foto = db.Column(db.LargeBinary, nullable=True)
    estado = db.Column(db.Enum('activo', 'inactivo'), nullable=True, default='activo')

class Raza(db.Model):
    __tablename__ = 'raza'
    id_raza = db.Column(db.SmallInteger, primary_key=True)
    nombre_raza = db.Column(db.String(30), nullable=False)
    produccion_leche_dia_min = db.Column(db.Float, nullable=False, default=0)
    produccion_leche_dia_max = db.Column(db.Float, nullable=False, default=0)
    peso_nacimiento_kg = db.Column(db.Float, nullable=True)
    madurez_sexual_hembras_meses = db.Column(db.SmallInteger, nullable=True)
    tipo_raza = db.Column(db.String(20), nullable=False)
    expectativa_vida_anos = db.Column(db.SmallInteger, nullable=False)
    adaptabilidad_clima = db.Column(db.String(20), nullable=False)
    notas = db.Column(db.String(250), nullable=True)
    variacion_genetica = db.Column(db.Enum('Alta', 'Media', 'Baja'), nullable=True)
    madurez_sexual_machos_meses = db.Column(db.SmallInteger, nullable=True)
    animales = db.relationship('Animal', backref='raza')

class Finca(db.Model):
    __tablename__ = 'finca'
    id_finca = db.Column(db.SmallInteger, primary_key=True)
    nombre_finca = db.Column(db.String(30), nullable=False)
    localizacion = db.Column(db.String(100), nullable=True)
    latitud = db.Column(DECIMAL(10,6), nullable=True)
    longitud = db.Column(DECIMAL(10,6), nullable=True)
    correo = db.Column(db.String(60), nullable=False)
    telefono = db.Column(db.String(15), nullable=True)
    nombreEncargado = db.Column(db.String(40), nullable=True)
    pais = db.Column(db.String(50), nullable=True)
    departamento = db.Column(db.String(50), nullable=True)
    ciudad = db.Column(db.String(50), nullable=True)

    animales = db.relationship('Animal', backref='finca')


class EstadoReproductivo(db.Model):
    __tablename__ = 'estado_reproductivo'
    id_estado_reprod = db.Column(db.SmallInteger, primary_key=True)
    descripcion = db.Column(db.String(20), nullable=False)
    duracion_promedio = db.Column(db.Integer, nullable=True)
    intervalo_entre_ciclos = db.Column(db.Integer, nullable=True)

    animales = db.relationship('Animal', backref='estado_reproductivo')


class Animal(db.Model):
    __tablename__ = 'animal'
    __table_args__ = (
        db.Index('ix_animal_id_finca', 'id_finca'),
        db.Index('ix_animal_sexo', 'sexo'),
        db.Index('ix_animal_ubicacion', 'ubicacion_animal'),
    )
    id_animal = db.Column(db.SmallInteger, primary_key=True)
    nombre_animal = db.Column(db.String(15), nullable=False)
    id_raza = db.Column(db.SmallInteger, db.ForeignKey('raza.id_raza'), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(6), nullable=False)
    id_finca = db.Column(db.SmallInteger, db.ForeignKey('finca.id_finca', ondelete='CASCADE'), nullable=False)
    id_potrero = db.Column(db.SmallInteger, db.ForeignKey('potrero.id_potrero'), nullable=True)
    id_padre = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal'), nullable=True)
    id_madre = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal'), nullable=True)
    ubicacion_animal = db.Column(db.Enum('en finca', 'fuera de la finca', 'desconocido'), nullable=False)
    origen = db.Column(db.Enum('nacido_en_finca', 'comprado', 'otro'), nullable=True, default='otro')
    id_estado_reprod = db.Column(db.SmallInteger, db.ForeignKey('estado_reproductivo.id_estado_reprod'), nullable=True)
    # Ajuste para coincidir con la BD: almacenar bytes en columna existente `foto_animal`
    foto_animal = db.Column(db.LargeBinary, nullable=True)

    padre = db.relationship('Animal', foreign_keys=[id_padre], remote_side=[id_animal], backref='crias_padre')
    madre = db.relationship('Animal', foreign_keys=[id_madre], remote_side=[id_animal], backref='crias_madre')
    potrero = db.relationship('Potrero', backref='animales')
    productos_animal = db.relationship('ProductosAnimal', backref='animal')
    registros_peso = db.relationship('RegistroPeso', backref='animal')
    servicios_salud = db.relationship('ServiciosSalud', backref='animal')
    ciclos_reproductivos = db.relationship('CicloReproductivo', backref='animal')

class DocumentoGenetico(db.Model):
    __tablename__ = 'documentos_geneticos'
    __table_args__ = {'extend_existing': True}

    # PK del documento genético
    id_documento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # FK al animal propietario del documento
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)

    # Metadatos opcionales del documento (ajustables según la BD real)
    nombre_documento = db.Column(db.String(100), nullable=False)
    # Alinear con BD: ENUM('pedigri','prueba_adn','certificado_raza') y NOT NULL
    tipo_documento = db.Column(db.Enum('pedigri', 'prueba_adn', 'certificado_raza'), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    # Campos adicionales presentes en la BD
    fecha_emision = db.Column(db.Date, nullable=True)
    entidad_emisora = db.Column(db.String(100), nullable=True)
    fecha_registro = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)

    # Contenido binario del documento (e.g., PDF, imagen de análisis ADN, etc.)
    archivo = db.Column(db.LargeBinary, nullable=False)

    # Relación con Animal
    animal = db.relationship('Animal', backref='documentos_geneticos')

class Productos(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.SmallInteger, primary_key=True)
    nombre_producto = db.Column(db.String(20), nullable=False)
    descripcion_producto = db.Column(db.String(300), nullable=False)
    # Tipo de cantidad para unidades dinámicas en formularios:
    # 1 = litros, 2 = libras, 3 = unidades
    tipo_cantidad = db.Column(db.SmallInteger, nullable=True)
    # Sin precio_venta: el esquema SQL no define esta columna

    productos_animal = db.relationship('ProductosAnimal', backref='producto')

class ProductosAnimal(db.Model):
    __tablename__ = 'productos_animal'
    id_produccion = db.Column(db.Integer, primary_key=True)
    id_producto = db.Column(db.SmallInteger, db.ForeignKey('productos.id_producto'), nullable=False)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    notas_produccion = db.Column(db.String(250), nullable=True)

class RegistroPeso(db.Model):
    __tablename__ = 'registro_peso'
    id_registro = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    fecha_registro = db.Column(db.Date, nullable=False)
    peso = db.Column(db.Float, nullable=False)
    tipo_momento = db.Column(db.Enum('nacimieto', 'destete', 'mensual', 'preparto', 'postparto', 'engorde', 'control sanitario'), nullable=False, default='mensual')
    notas = db.Column(db.String(250), nullable=True)

class TipoServicioSalud(db.Model):
    __tablename__ = 'tipo_servicio_salud'
    id_tipo_salud = db.Column(db.SmallInteger, primary_key=True)
    nombre_servicio = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(Text, nullable=True)
    categoria = db.Column(db.Enum('Vacunación', 'Desparasitación', 'Tratamiento médico', 'Suplemento', 'Cirugía', 'Control preventivo'), nullable=False)
    frecuencia_recomendada = db.Column(db.String(30), nullable=True)
    aplica_a_sexo = db.Column(db.Enum('macho', 'hembra', 'ambos'), nullable=True, default='ambos')
    # Campos adicionales presentes en la BD según el esquema SQL
    duracion_efecto_dias = db.Column(db.Integer, nullable=True)
    edad_minima_aplicacion = db.Column(db.Integer, nullable=True, default=0)
    requiere_veterinario = db.Column(db.Boolean, nullable=True, default=True)
    
    servicios = db.relationship('ServiciosSalud', backref='tipo_servicio')

# Eliminado: tabla Veterinario. Ahora los servicios referencian a Trabajador con rol 'veterinario'.

class ServiciosSalud(db.Model):
    __tablename__ = 'servicios_salud'
    id_servicio_salud = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    id_tipo_salud = db.Column(db.SmallInteger, db.ForeignKey('tipo_servicio_salud.id_tipo_salud'), nullable=False)
    # La columna se mantiene como id_veterinario en la BD pero referencia a trabajador
    id_veterinario = db.Column(db.Integer, db.ForeignKey('trabajador.id_trabajador'), nullable=False)
    fecha_servicio = db.Column(db.Date, nullable=False)
    fecha_proximo = db.Column(db.Date, nullable=True)
    dosis = db.Column(db.String(50), nullable=True)
    observaciones = db.Column(Text, nullable=True)
    costo = db.Column(DECIMAL(8, 2), nullable=False)
    # Relación hacia Trabajador (rol veterinario)
    trabajador = db.relationship('Trabajador', backref='servicios_salud')

class UsuarioFinca(db.Model):
    __tablename__ = 'usuario_finca'
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'finca_id', name='uq_usuario_finca'),
        db.Index('ix_usuario_finca_usuario_id', 'usuario_id'),
        db.Index('ix_usuario_finca_finca_id', 'finca_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    finca_id = db.Column(db.SmallInteger, db.ForeignKey('finca.id_finca', ondelete='CASCADE'), nullable=False)
    # Nuevo: rol del usuario en esta finca (1=trabajador, 2=veterinario)
    rol_en_finca = db.Column(db.SmallInteger, nullable=True)
    # Nuevo: permisos de edición específicos para esta finca
    puede_editar = db.Column(db.Boolean, nullable=True, default=False)
    # Estado específico de la asignación trabajador-finca: 'asignado' o 'no_asignado'
    estado_asignacion = db.Column(db.Enum('asignado', 'no_asignado'), nullable=False, default='asignado')


class PermisoFincaUsuario(db.Model):
    __tablename__ = 'permiso_finca_usuario'
    __table_args__ = (
        db.UniqueConstraint('trabajador_id', 'finca_id', name='uq_permiso_finca_trabajador'),
        db.Index('ix_permiso_trabajador', 'trabajador_id'),
        db.Index('ix_permiso_finca', 'finca_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    trabajador_id = db.Column(db.Integer, db.ForeignKey('trabajador.id_trabajador', ondelete='CASCADE'), nullable=False)
    finca_id = db.Column(db.SmallInteger, db.ForeignKey('finca.id_finca', ondelete='CASCADE'), nullable=False)
    crear_potreros = db.Column(db.Boolean, nullable=False, default=False)
    agregar_animales = db.Column(db.Boolean, nullable=False, default=False)
    eliminar_animales = db.Column(db.Boolean, nullable=False, default=False)
    crear_usuarios_ligados = db.Column(db.Boolean, nullable=False, default=False)
    actualizar_datos_usuario = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CicloReproductivo(db.Model):
    __tablename__ = 'ciclo_reproductivo'
    id_ciclo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    tipo_ciclo = db.Column(db.Enum('celo', 'gestación', 'lactancia', 'descanso'), nullable=False)
    duracion_esperada = db.Column(db.Integer, nullable=True)
    notas = db.Column(Text, nullable=True)
    
  
class Reporte(db.Model):
    __tablename__ = 'reporte'
    id_reporte = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(Text, nullable=True)
    fecha_generacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tipo_reporte = db.Column(db.Enum('ganado', 'produccion', 'salud', 'financiero', 'general'), nullable=False)
    formato = db.Column(db.Enum('pdf', 'excel', 'csv', 'html'), nullable=False, default='pdf')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    finca_id = db.Column(db.SmallInteger, db.ForeignKey('finca.id_finca'), nullable=True)
    
    usuario = db.relationship('Usuario', backref='reportes')
    finca = db.relationship('Finca', backref='reportes')


class ActividadReciente(db.Model):
    __tablename__ = 'actividad_reciente'
    id_actividad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    accion = db.Column(db.String(50), nullable=False)
    elemento = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    usuario = db.relationship('Usuario', backref='actividades')


class Potrero(db.Model):
    __tablename__ = 'potrero'
    id_potrero = db.Column(db.SmallInteger, primary_key=True)
    nombre_potrero = db.Column(db.String(50), nullable=False)
    id_finca = db.Column(db.SmallInteger, db.ForeignKey('finca.id_finca', ondelete='CASCADE'), nullable=False)
    extension = db.Column(DECIMAL(10, 2), nullable=False)
    capacidad_animal = db.Column(db.SmallInteger, nullable=True)
    tipo_pasto = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.Enum('activo', 'descanso', 'mantenimiento'), nullable=False, default='activo')
    fecha_ultima_rotacion = db.Column(db.Date, nullable=True)
    notas = db.Column(Text, nullable=True)
    
    finca = db.relationship('Finca', backref='potreros')
    rotaciones = db.relationship('RotacionPotrero', backref='potrero')

class GrupoAnimal(db.Model):
    __tablename__ = 'grupo_animal'
    id_grupo = db.Column(db.SmallInteger, primary_key=True)
    nombre_grupo = db.Column(db.String(50), nullable=False)
    id_finca = db.Column(db.SmallInteger, db.ForeignKey('finca.id_finca'), nullable=False)
    fecha_creacion = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    descripcion = db.Column(Text, nullable=True)
    
    finca = db.relationship('Finca', backref='grupos_animales')
    animales = db.relationship('Animal', secondary='animal_grupo', backref='grupos')

# Tabla de relación muchos a muchos entre Animal y GrupoAnimal
class AnimalGrupo(db.Model):
    __tablename__ = 'animal_grupo'
    id = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    id_grupo = db.Column(db.SmallInteger, db.ForeignKey('grupo_animal.id_grupo', ondelete='CASCADE'), nullable=False)
    fecha_asignacion = db.Column(db.Date, nullable=False)

class RotacionPotrero(db.Model):
    __tablename__ = 'rotacion_potrero'
    id_rotacion = db.Column(db.Integer, primary_key=True)
    id_potrero = db.Column(db.SmallInteger, db.ForeignKey('potrero.id_potrero', ondelete='CASCADE'), nullable=False)
    id_grupo_animal = db.Column(db.SmallInteger, db.ForeignKey('grupo_animal.id_grupo'), nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    tipo_uso = db.Column(db.Enum('pastoreo', 'descanso', 'siembra', 'fertilización', 'mantenimiento'), nullable=False)
    observaciones = db.Column(Text, nullable=True)
    id_grupo = db.Column(db.Integer, nullable=False)
    
    grupo_animal = db.relationship('GrupoAnimal', backref='rotaciones', foreign_keys=[id_grupo_animal])

class EstadoSalud(db.Model):
    __tablename__ = 'estado_salud'
    id_estado_salud = db.Column(db.SmallInteger, primary_key=True)
    descripcion = db.Column(db.String(20), nullable=False)

class HistorialEstadoSalud(db.Model):
    __tablename__ = 'historial_estado_salud'
    id_historial_salud = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    id_estado_salud = db.Column(db.SmallInteger, db.ForeignKey('estado_salud.id_estado_salud'), nullable=False)
    fecha_cambio = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    observaciones = db.Column(Text, nullable=True)
    
    animal = db.relationship('Animal', backref='historial_salud')
    estado_salud = db.relationship('EstadoSalud', backref='historiales')

class HistorialEstadoReproductivo(db.Model):
    __tablename__ = 'historial_estado_reproductivo'
    id_historial_reprod = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    id_estado_reprod = db.Column(db.SmallInteger, db.ForeignKey('estado_reproductivo.id_estado_reprod'), nullable=False)
    fecha_cambio = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    observaciones = db.Column(Text, nullable=True)
    
    animal = db.relationship('Animal', backref='historial_reproductivo')
    estado_reproductivo = db.relationship('EstadoReproductivo', backref='historiales')

class TipoServicioSexual(db.Model):
    __tablename__ = 'tipo_servicio_sexual'
    id_servicio = db.Column(db.SmallInteger, primary_key=True)
    nombre_servicio = db.Column(db.String(40), nullable=False)
    descripcion_servicio = db.Column(db.String(200), nullable=False)
    aplica_a_sexo = db.Column(db.Enum('macho', 'hembra', 'ambos'), nullable=True, default='ambos')
    
    servicios = db.relationship('ServiciosSexuales', backref='tipo_servicio')

class ServiciosSexuales(db.Model):
    __tablename__ = 'servicios_sexuales'
    id_servicio = db.Column(db.SmallInteger, primary_key=True)
    id_servicioanimal = db.Column(db.SmallInteger, db.ForeignKey('tipo_servicio_sexual.id_servicio'), nullable=False)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal'), nullable=False)
    # La columna se mantiene como id_veterinario en la BD pero referencia a trabajador
    id_veterinario = db.Column(db.Integer, db.ForeignKey('trabajador.id_trabajador'), nullable=False)
    fecha_servicio = db.Column(db.Date, nullable=False)
    fecha_proximo = db.Column(db.Date, nullable=True)
    notas_servicio = db.Column(db.String(200), nullable=True)
    costo_total = db.Column(db.Float, nullable=True)
    
    animal = db.relationship('Animal', backref='servicios_sexuales')
    # Relación hacia Trabajador (rol veterinario)
    trabajador = db.relationship('Trabajador', backref='servicios_sexuales')

class EstadoGeneral(db.Model):
    __tablename__ = 'estado_general'
    id_estado = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal'), nullable=False)
    estado = db.Column(db.Enum('vivo', 'muerto', 'vendido'), nullable=True)
    fecha_estado = db.Column(db.Date, nullable=True)
    
    animal = db.relationship('Animal', backref='estado_general')

class ManejoPasto(db.Model):
    __tablename__ = 'manejo_pasto'
    id_manejo = db.Column(db.Integer, primary_key=True)
    id_potrero = db.Column(db.SmallInteger, db.ForeignKey('potrero.id_potrero'), nullable=False)
    fecha_medicion = db.Column(db.Date, nullable=False)
    altura_pasto = db.Column(DECIMAL(5, 2), nullable=True)
    cobertura = db.Column(DECIMAL(5, 2), nullable=True)
    estado_pasto = db.Column(db.Enum('excelente', 'bueno', 'regular', 'malo'), nullable=False)
    observaciones = db.Column(Text, nullable=True)
    
    potrero = db.relationship('Potrero', backref='manejo_pasto')


def inicializar_usuario_admin():
    """Función para crear el usuario administrador por defecto si no existe"""
    admin_existente = Usuario.query.filter_by(nik_name='superadmin').first()
    
    if not admin_existente:
        admin_usuario = Usuario(
            nik_name='superadmin',
            nombres='Super',
            apellidos='Administrador',
            correo='superadmin@ganacontrol.com',
            contraseña=generate_password_hash('superadmin123'),
            tipo_usuario=3,  # Tipo 3 = Superusuario/Administrador
            direccion='Dirección Central',
            telefono='987654321',
            pais='Colombia',
            departamento='Nacional',
            ciudad='Bogotá'
        )
        
        try:
            db.session.add(admin_usuario)
            db.session.commit()
            print("Usuario administrador 'superadmin' creado exitosamente")
        except Exception as e:
            db.session.rollback()
            print(f"Error al crear usuario administrador: {e}")
    else:
        print("Usuario administrador 'superadmin' ya existe")


class CompraAnimales(db.Model):
    __tablename__ = 'compra_animales'
    __table_args__ = {'extend_existing': True}  # Permite usar una tabla existente
    
    id_compra = db.Column(db.SmallInteger, primary_key=True)
    id_animal = db.Column(db.SmallInteger, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    fecha_compra = db.Column(db.Date, nullable=False)
    precio_compra = db.Column(db.Numeric(10, 2), nullable=False)
    vendedor = db.Column(db.String(100), nullable=True)
    lugar_compra = db.Column(db.String(100), nullable=True)
    documento_compra = db.Column(db.String(50), nullable=True)
    peso_compra = db.Column(db.Float, nullable=True)
    edad_compra = db.Column(db.SmallInteger, nullable=True)
    estado_salud_compra = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relación con el animal
    animal = db.relationship('Animal', backref='compra')