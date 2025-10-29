from flask_wtf import FlaskForm
from wtforms import FloatField, DateField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from datetime import date


class RegistroPesoForm(FlaskForm):
    fecha_registro = DateField('Fecha', validators=[DataRequired()], default=date.today)
    peso = FloatField('Peso (kg)', validators=[DataRequired(), NumberRange(min=0)])
    # Nota: Enum en modelo usa 'nacimieto' (sic). Debe coincidir exactamente.
    tipo_momento = SelectField(
        'Momento',
        choices=[
            ('nacimieto', 'Nacimiento'),
            ('destete', 'Destete'),
            ('mensual', 'Mensual'),
            ('preparto', 'Preparto'),
            ('postparto', 'Postparto'),
            ('engorde', 'Engorde'),
            ('control sanitario', 'Control sanitario'),
        ],
        validators=[DataRequired()]
    )
    notas = TextAreaField('Notas')
    submit = SubmitField('Registrar peso')