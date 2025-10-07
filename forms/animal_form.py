from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, ValidationError, Optional
from modelo.models import Animal, Raza, Finca, EstadoReproductivo, Potrero

class FiltroAnimalForm(FlaskForm):
    raza = SelectField('Raza', coerce=int, validators=[Optional()])
    sexo = SelectField('Sexo', choices=[('', 'Todos'), ('Macho', 'Macho'), ('Hembra', 'Hembra')], validators=[Optional()])
    ubicacion = SelectField('Ubicación', 
                          choices=[('', 'Todas'), 
                                  ('en finca', 'En Finca'), 
                                  ('fuera de la finca', 'Fuera de la Finca'), 
                                  ('desconocido', 'Desconocido')], 
                          validators=[Optional()])
    origen = SelectField('Origen', 
                        choices=[('', 'Todos'),
                                ('nacido_en_finca', 'Nacido en Finca'), 
                                ('comprado', 'Comprado'), 
                                ('otro', 'Otro')], 
                        validators=[Optional()])
    estado_reprod = SelectField('Estado Reproductivo', coerce=int, validators=[Optional()])
    submit = SubmitField('Filtrar')
    
    def __init__(self, *args, **kwargs):
        super(FiltroAnimalForm, self).__init__(*args, **kwargs)
        self.raza.choices = [(0, 'Todas las razas')] + [(r.id_raza, r.nombre_raza) for r in Raza.query.all()]
        self.estado_reprod.choices = [(0, 'Todos los estados')] + [(e.id_estado_reprod, e.descripcion) for e in EstadoReproductivo.query.all()]

class AnimalForm(FlaskForm):
    nombre_animal = StringField('Nombre del Animal', validators=[DataRequired(), Length(min=2, max=15)])
    id_raza = SelectField('Raza', coerce=int, validators=[DataRequired()])
    fecha_nacimiento = DateField('Fecha de Nacimiento', validators=[DataRequired()])
    sexo = SelectField('Sexo', choices=[('Macho', 'Macho'), ('Hembra', 'Hembra')], validators=[DataRequired()])
    id_finca = SelectField('Finca', coerce=int, validators=[DataRequired()])
    id_potrero = SelectField('Potrero', coerce=int, validators=[Optional()])
    id_padre = SelectField('Padre', coerce=int, validators=[Optional()])
    id_madre = SelectField('Madre', coerce=int, validators=[Optional()])
    ubicacion_animal = SelectField('Ubicación', 
                                 choices=[('en finca', 'En Finca'), 
                                         ('fuera de la finca', 'Fuera de la Finca'), 
                                         ('desconocido', 'Desconocido')], 
                                 validators=[DataRequired()])
    origen = SelectField('Origen', 
                        choices=[('nacido_en_finca', 'Nacido en Finca'), 
                                ('comprado', 'Comprado'), 
                                ('otro', 'Otro')], 
                        validators=[Optional()])
    id_estado_reprod = SelectField('Estado Reproductivo', coerce=int, validators=[Optional()])
    submit = SubmitField('Guardar Animal')
    
    def __init__(self, *args, **kwargs):
        super(AnimalForm, self).__init__(*args, **kwargs)
        
        # Cargar opciones para los SelectField
        self.id_raza.choices = [(0, 'Seleccione una raza')] + [(r.id_raza, r.nombre_raza) for r in Raza.query.all()]
        self.id_finca.choices = [(0, 'Seleccione una finca')] + [(f.id_finca, f.nombre_finca) for f in Finca.query.all()]
        self.id_estado_reprod.choices = [(0, 'Sin estado reproductivo')] + [(e.id_estado_reprod, e.descripcion) for e in EstadoReproductivo.query.all()]
        
        # Inicialmente, sin potreros hasta que se seleccione una finca
        self.id_potrero.choices = [(0, 'Seleccione primero una finca')]
        
        # Para padre y madre, cargar solo animales machos y hembras respectivamente
        machos = Animal.query.filter_by(sexo='Macho').all()
        hembras = Animal.query.filter_by(sexo='Hembra').all()
        
        self.id_padre.choices = [(0, 'Sin padre registrado')] + [(a.id_animal, a.nombre_animal) for a in machos]
        self.id_madre.choices = [(0, 'Sin madre registrada')] + [(a.id_animal, a.nombre_animal) for a in hembras]
    
    def validate_nombre_animal(self, nombre_animal):
        # Verificar que el nombre no esté duplicado en la misma finca
        if self.id_finca.data and self.id_finca.data != 0:
            animal = Animal.query.filter_by(nombre_animal=nombre_animal.data, id_finca=self.id_finca.data).first()
            if animal:
                raise ValidationError('Ya existe un animal con este nombre en la finca seleccionada.')