from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date


class CicloReproductivoForm(FlaskForm):
    fecha_inicio = DateField('Fecha de inicio', validators=[DataRequired()], default=date.today)
    tipo_ciclo = SelectField(
        'Tipo de ciclo',
        choices=[],
        validators=[DataRequired()],
        validate_choice=False
    )
    duracion_esperada = IntegerField('Duración esperada (días)', validators=[Optional(), NumberRange(min=1)])
    notas = TextAreaField('Notas')
    submit = SubmitField('Iniciar ciclo')


class CerrarCicloForm(FlaskForm):
    fecha_fin = DateField('Fecha de fin', validators=[DataRequired()], default=date.today)
    notas_fin = TextAreaField('Notas de cierre')
    submit = SubmitField('Cerrar ciclo')