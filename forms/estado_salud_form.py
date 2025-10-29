from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional


class EstadoSaludForm(FlaskForm):
    id_estado_salud = SelectField('Estado de salud', coerce=int, validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    submit = SubmitField('Actualizar estado de salud')