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
    id_cria = db.Column(db.Integer, nullable=True)
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
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    finca_id = db.Column(db.Integer, db.ForeignKey('finca.id_finca'), nullable=False)

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