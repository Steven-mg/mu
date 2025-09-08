from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import backref, relationship
from flask_login import UserMixin
from config import db

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True) 
    nik_name = db.Column(db.String(50), unique=True)  # Cambiado de nombre_usuario a nik_name
    nombres = db.Column(db.String(50), nullable=True)  # Nuevo campo para nombres
    apellidos = db.Column(db.String(50), nullable=True)  # Nuevo campo para apellidos
    correo = db.Column(db.String(120), unique=True, nullable=False)  # Mantenemos correo como obligatorio para la autenticación
    contraseña = db.Column(db.String(255), nullable=True)  # Permitimos nulo para autenticación con Google
    tipo_usuario = db.Column(db.Integer, nullable=False)  # 1: Veterinario, 2: Dueño, 3: Superusuario
    direccion = db.Column(db.String(30), nullable=True)  # Cambiado a nullable=True
    telefono = db.Column(db.String(15), nullable=True)  # Cambiado a nullable=True
    pais = db.Column(db.String(50), nullable=True)
    departamento = db.Column(db.String(50), nullable=True)
    ciudad = db.Column(db.String(50), nullable=True)
    fincas = db.relationship('Finca', secondary='usuario_finca', backref='usuarios')
    
   

class Raza(db.Model):
    __tablename__ = 'raza'
    id_raza = db.Column(db.Integer, primary_key=True)
    nombre_raza = db.Column(db.String(30), nullable=False)
    produccion_leche_aprox = db.Column(db.Float, nullable=False)
    peso_nacimiento = db.Column(db.Float, nullable=False)
    edad_madurez = db.Column(db.Integer, nullable=False)
    tipo_raza = db.Column(db.String(20), nullable=False)
    expectativa_vida = db.Column(db.Integer, nullable=False)
    adaptabilidad_clima = db.Column(db.String(20), nullable=False)
    notas = db.Column(db.String(250), nullable=True)
    animales = db.relationship('Animal', backref='raza')

class Finca(db.Model):
    __tablename__ = 'finca'
    id_finca = db.Column(db.Integer, primary_key=True)
    nombre_finca = db.Column(db.String(30), nullable=False)
    localizacion = db.Column(db.String(100), nullable=True)  # Cambiado a nullable=True
    correo = db.Column(db.String(60), nullable=False)
    telefono = db.Column(db.String(15), nullable=True)  # Cambiado a nullable=True
    nombreEncargado = db.Column(db.String(40), nullable=True)
    pais = db.Column(db.String(50), nullable=True)
    departamento = db.Column(db.String(50), nullable=True)
    ciudad = db.Column(db.String(50), nullable=True)

    animales = db.relationship('Animal', backref='finca')


class EstadoReproductivo(db.Model):
    __tablename__ = 'estado_reproductivo'
    id_estado_reprod = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(20), nullable=False)

    animales = db.relationship('Animal', backref='estado_reproductivo')


class Animal(db.Model):
    __tablename__ = 'animal'
    id_animal = db.Column(db.Integer, primary_key=True)
    nombre_animal = db.Column(db.String(15), nullable=False)
    id_raza = db.Column(db.Integer, db.ForeignKey('raza.id_raza'), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(6), nullable=False)
    id_finca = db.Column(db.Integer, db.ForeignKey('finca.id_finca'), nullable=False)
    id_padre = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=True)
    id_madre = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=True)
    ubicacion_animal = db.Column(db.Enum('en finca', 'fuera de la finca', 'desconocido'), nullable=False)
    # Eliminar la línea siguiente:
    # id_cria = db.Column(db.Integer, nullable=True)
    id_estado_reprod = db.Column(db.Integer, db.ForeignKey('estado_reproductivo.id_estado_reprod'), nullable=True)

    padre = db.relationship('Animal', foreign_keys=[id_padre], remote_side=[id_animal], backref='crias_padre')

    madre = db.relationship('Animal', foreign_keys=[id_madre], remote_side=[id_animal], backref='crias_madre')

    productos_animal = db.relationship('ProductosAnimal', backref='animal')

    registros_peso = db.relationship('RegistroPeso', backref='animal')
    
    servicios_salud = db.relationship('ServiciosSalud', backref='animal')
    ciclos_reproductivos = db.relationship('CicloReproductivo', backref='animal')

class Productos(db.Model):
    __tablename__ = 'productos'
    id_producto = db.Column(db.Integer, primary_key=True)
    nombre_producto = db.Column(db.String(20), nullable=False)
    descripcion_producto = db.Column(db.String(300), nullable=False)

    productos_animal = db.relationship('ProductosAnimal', backref='producto')

class ProductosAnimal(db.Model):
    __tablename__ = 'productos_animal'
    id_produccion = db.Column(db.Integer, primary_key=True)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    notas_produccion = db.Column(db.String(250), nullable=True)

class RegistroPeso(db.Model):
    __tablename__ = 'registro_peso'
    id_registro = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    fecha_registro = db.Column(db.Date, nullable=False)
    peso = db.Column(db.Float, nullable=False)
    tipo_momento = db.Column(db.Enum('nacimieto', 'destete', 'mensual', 'preparto', 'postparto', 'engorde', 'control sanitario'), nullable=False, default='mensual')
    notas = db.Column(db.String(250), nullable=True)

class TipoServicioSalud(db.Model):
    __tablename__ = 'tipo_servicio_salud'
    id_tipo_salud = db.Column(db.Integer, primary_key=True)
    nombre_servicio = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.Enum('Vacunación', 'Desparasitación', 'Tratamiento médico', 'Suplemento', 'Cirugía', 'Control preventivo'), nullable=False)
    frecuencia_recomendada = db.Column(db.String(30), nullable=True)
    costo_referencia = db.Column(db.Numeric(8, 2), nullable=True)
    
    servicios = db.relationship('ServiciosSalud', backref='tipo_servicio')

class Veterinario(db.Model):
    __tablename__ = 'veterinario'
    id_veterinario = db.Column(db.Integer, primary_key=True)
    nombre_veterinario = db.Column(db.String(50), nullable=False)
    telefono = db.Column(db.String(12), nullable=False)
    correo = db.Column(db.String(40), nullable=False)
    direccion = db.Column(db.String(50), nullable=False)
    
    servicios = db.relationship('ServiciosSalud', backref='veterinario')

class ServiciosSalud(db.Model):
    __tablename__ = 'servicios_salud'
    id_servicio_salud = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    id_tipo_salud = db.Column(db.Integer, db.ForeignKey('tipo_servicio_salud.id_tipo_salud'), nullable=False)
    id_veterinario = db.Column(db.Integer, db.ForeignKey('veterinario.id_veterinario'), nullable=False)
    fecha_servicio = db.Column(db.Date, nullable=False)
    fecha_proximo = db.Column(db.Date, nullable=True)
    dosis = db.Column(db.String(50), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    costo = db.Column(db.Numeric(8, 2), nullable=False)

class UsuarioFinca(db.Model):
    __tablename__ = 'usuario_finca'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete='CASCADE'), nullable=False)
    finca_id = db.Column(db.Integer, db.ForeignKey('finca.id_finca', ondelete='CASCADE'), nullable=False)

class CicloReproductivo(db.Model):
    __tablename__ = 'ciclo_reproductivo'
    id_ciclo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    tipo_ciclo = db.Column(db.Enum('celo', 'gestación', 'lactancia', 'descanso'), nullable=False)
    duracion_esperada = db.Column(db.Integer, nullable=True, comment='Duración esperada en días')
    notas = db.Column(db.Text, nullable=True)
    
    # Elimina esta línea para resolver el conflicto
    # animal = db.relationship('Animal', backref='ciclos_reproductivos')

# Agregar al final del archivo, después de la clase CicloReproductivo
class Reporte(db.Model):
    __tablename__ = 'reporte'
    id_reporte = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_generacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tipo_reporte = db.Column(db.Enum('ganado', 'produccion', 'salud', 'financiero', 'general'), nullable=False)
    formato = db.Column(db.Enum('pdf', 'excel', 'csv', 'html'), nullable=False, default='pdf')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    finca_id = db.Column(db.Integer, db.ForeignKey('finca.id_finca'), nullable=True)
    
    usuario = db.relationship('Usuario', backref='reportes')
    finca = db.relationship('Finca', backref='reportes')

# Agregar al final del archivo, después de la clase Reporte
class ActividadReciente(db.Model):
    __tablename__ = 'actividad_reciente'
    id_actividad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    accion = db.Column(db.String(50), nullable=False)  # Creó, Actualizó, Eliminó, Modificó, Añadió, etc.
    elemento = db.Column(db.String(100), nullable=False)  # Usuario: Juan Pérez, Finca: Los Alamos, etc.
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relación con el usuario que realizó la acción
    usuario = db.relationship('Usuario', backref='actividades')

# Agregar esta nueva clase
class Cria(db.Model):
    __tablename__ = 'cria'
    id_cria = db.Column(db.Integer, primary_key=True)
    id_padre = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    id_madre = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    nombre_cria = db.Column(db.String(30), nullable=True)
    
    # Relaciones
    animal = db.relationship('Animal', foreign_keys=[id_animal], backref='crias')
    padre = db.relationship('Animal', foreign_keys=[id_padre], backref='crias_como_padre')
    madre = db.relationship('Animal', foreign_keys=[id_madre], backref='crias_como_madre')

class Potrero(db.Model):
    __tablename__ = 'potrero'
    id_potrero = db.Column(db.Integer, primary_key=True)
    nombre_potrero = db.Column(db.String(50), nullable=False)
    id_finca = db.Column(db.Integer, db.ForeignKey('finca.id_finca'), nullable=False)
    extension = db.Column(db.Float, nullable=False, comment='Área en hectáreas')  # Cambiado de area a extension
    capacidad_animal = db.Column(db.Integer, nullable=True, comment='Capacidad máxima de animales')
    tipo_pasto = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.Enum('activo', 'descanso', 'mantenimiento'), nullable=False, default='activo')  # Cambiado estado_actual a estado y valores del enum
    fecha_ultima_rotacion = db.Column(db.Date, nullable=True)  # Cambiado de fecha_ultimo_uso a fecha_ultima_rotacion
    notas = db.Column(db.Text, nullable=True)
    
    # Relaciones
    finca = db.relationship('Finca', backref='potreros')
    rotaciones = db.relationship('RotacionPotrero', backref='potrero')

class GrupoAnimal(db.Model):
    __tablename__ = 'grupo_animal'
    id_grupo = db.Column(db.Integer, primary_key=True)
    nombre_grupo = db.Column(db.String(50), nullable=False)
    id_finca = db.Column(db.Integer, db.ForeignKey('finca.id_finca'), nullable=False)
    tipo_grupo = db.Column(db.Enum('cría', 'levante', 'ceba', 'producción', 'reproducción', 'otro'), nullable=False)
    fecha_creacion = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    descripcion = db.Column(db.Text, nullable=True)
    
    # Relaciones
    finca = db.relationship('Finca', backref='grupos_animales')
    animales = db.relationship('Animal', secondary='animal_grupo', backref='grupos')

# Tabla de relación muchos a muchos entre Animal y GrupoAnimal
class AnimalGrupo(db.Model):
    __tablename__ = 'animal_grupo'
    id = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal', ondelete='CASCADE'), nullable=False)
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupo_animal.id_grupo', ondelete='CASCADE'), nullable=False)
    fecha_ingreso = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    fecha_salida = db.Column(db.Date, nullable=True)
    motivo_salida = db.Column(db.String(100), nullable=True)

class RotacionPotrero(db.Model):
    __tablename__ = 'rotacion_potrero'
    id_rotacion = db.Column(db.Integer, primary_key=True)
    id_potrero = db.Column(db.Integer, db.ForeignKey('potrero.id_potrero'), nullable=False)
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupo_animal.id_grupo'), nullable=False)
    fecha_ingreso = db.Column(db.DateTime, nullable=False)
    fecha_salida = db.Column(db.DateTime, nullable=True)
    cantidad_animales = db.Column(db.Integer, nullable=False)
    motivo_salida = db.Column(db.String(100), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    
    # Relaciones
    grupo_animal = db.relationship('GrupoAnimal', backref='rotaciones')

class EstadoGeneral(db.Model):
    __tablename__ = 'estado_general'
    id_estado_general = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.Enum('normal', 'alerta', 'crítico'), nullable=False, default='normal')
    requiere_atencion = db.Column(db.Boolean, nullable=False, default=False)

class EstadoSalud(db.Model):
    __tablename__ = 'estado_salud'
    id_estado_salud = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    nivel_gravedad = db.Column(db.Enum('leve', 'moderado', 'grave', 'crítico'), nullable=False)
    requiere_aislamiento = db.Column(db.Boolean, nullable=False, default=False)
    requiere_tratamiento = db.Column(db.Boolean, nullable=False, default=True)
    recomendaciones = db.Column(db.Text, nullable=True)

class HistorialEstadoSalud(db.Model):
    __tablename__ = 'historial_estado_salud'
    id_historial = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    id_estado_salud = db.Column(db.Integer, db.ForeignKey('estado_salud.id_estado_salud'), nullable=False)
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    id_veterinario = db.Column(db.Integer, db.ForeignKey('veterinario.id_veterinario'), nullable=True)
    tratamiento_aplicado = db.Column(db.Text, nullable=True)
    resultado = db.Column(db.Enum('recuperado', 'en tratamiento', 'crónico', 'fallecido'), nullable=True)
    
    # Relaciones
    animal = db.relationship('Animal', backref='historial_salud')
    estado_salud = db.relationship('EstadoSalud', backref='historiales')
    veterinario = db.relationship('Veterinario', backref='historiales_salud')

class HistorialEstadoReproductivo(db.Model):
    __tablename__ = 'historial_estado_reproductivo'
    id_historial = db.Column(db.Integer, primary_key=True)
    id_animal = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    id_estado_reprod = db.Column(db.Integer, db.ForeignKey('estado_reproductivo.id_estado_reprod'), nullable=False)
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    
    # Relaciones
    animal = db.relationship('Animal', backref='historial_reproductivo')
    estado_reproductivo = db.relationship('EstadoReproductivo', backref='historiales')

class TipoServicioSexual(db.Model):
    __tablename__ = 'tipo_servicio_sexual'
    id_tipo_servicio = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    metodo = db.Column(db.Enum('monta natural', 'inseminación artificial', 'transferencia de embriones', 'otro'), nullable=False)
    costo_referencia = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Relaciones
    servicios = db.relationship('ServiciosSexuales', backref='tipo_servicio')

class ServiciosSexuales(db.Model):
    __tablename__ = 'servicios_sexuales'
    id_servicio = db.Column(db.Integer, primary_key=True)
    id_animal_hembra = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=False)
    id_animal_macho = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=True)
    id_tipo_servicio = db.Column(db.Integer, db.ForeignKey('tipo_servicio_sexual.id_tipo_servicio'), nullable=False)
    fecha_servicio = db.Column(db.DateTime, nullable=False)
    exitoso = db.Column(db.Boolean, nullable=True)
    id_cria_resultante = db.Column(db.Integer, db.ForeignKey('animal.id_animal'), nullable=True)
    notas = db.Column(db.Text, nullable=True)
    costo = db.Column(db.Numeric(10, 2), nullable=True)
    id_veterinario = db.Column(db.Integer, db.ForeignKey('veterinario.id_veterinario'), nullable=True)
    
    # Relaciones
    hembra = db.relationship('Animal', foreign_keys=[id_animal_hembra], backref='servicios_como_hembra')
    macho = db.relationship('Animal', foreign_keys=[id_animal_macho], backref='servicios_como_macho')
    cria = db.relationship('Animal', foreign_keys=[id_cria_resultante], backref='servicio_origen')
    veterinario = db.relationship('Veterinario', backref='servicios_sexuales')