from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from modelo.models import Potrero

class PotreroForm(FlaskForm):
    nombre_potrero = StringField('Nombre del Potrero', validators=[DataRequired(), Length(min=2, max=50)])
  
    extension = FloatField('Extensión (hectáreas)', validators=[DataRequired(), NumberRange(min=0.1)])
    capacidad_animal = IntegerField('Capacidad (animales)', validators=[Optional(), NumberRange(min=1)])
    tipo_pasto = SelectField('Tipo de Pasto', choices=[
        ('', 'Seleccione un tipo'),
        ('corte', 'Pasto de corte'),
        ('pastoreo', 'Pasto de pastoreo'),
        ('levante', 'Pasto de levante'),
        ('engorde', 'Pasto de engorde'),
        ('leche', 'Pasto de leche')
    ], validators=[Optional()])
    estado = SelectField('Estado', choices=[
        ('activo', 'Activo'),
        ('descanso', 'En Descanso'),
        ('mantenimiento', 'En Mantenimiento')
    ], validators=[DataRequired()])
    fecha_ultima_rotacion = DateField('Fecha Última Rotación', validators=[Optional()])
    notas = TextAreaField('Notas', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Guardar Potrero')
    
    def __init__(self, *args, **kwargs):
        super(PotreroForm, self).__init__(*args, **kwargs)