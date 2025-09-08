from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from modelo.models import Potrero

class PotreroForm(FlaskForm):
    nombre_potrero = StringField('Nombre del Potrero', validators=[DataRequired(), Length(min=2, max=50)])
    area = FloatField('Área (hectáreas)', validators=[DataRequired(), NumberRange(min=0.1)])
    capacidad_animal = IntegerField('Capacidad (animales)', validators=[Optional(), NumberRange(min=1)])
    tipo_pasto = StringField('Tipo de Pasto', validators=[Optional(), Length(max=50)])
    estado_actual = SelectField('Estado', choices=[
        ('disponible', 'Disponible'),
        ('ocupado', 'Ocupado'),
        ('en descanso', 'En Descanso'),
        ('en mantenimiento', 'En Mantenimiento')
    ], validators=[DataRequired()])
    notas = TextAreaField('Notas', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Guardar Potrero')
    
    def __init__(self, *args, **kwargs):
        super(PotreroForm, self).__init__(*args, **kwargs)