from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, StringField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional

class ServicioSaludForm(FlaskForm):
    id_tipo_salud = SelectField('Tipo de servicio', coerce=int, validators=[DataRequired(message='Seleccione el tipo de servicio')])
    id_veterinario = SelectField('Profesional', coerce=int, validators=[DataRequired(message='Seleccione el profesional')])
    fecha_servicio = DateField('Fecha del servicio', validators=[DataRequired(message='Ingrese la fecha')])
    fecha_proximo = DateField('Próxima fecha', validators=[Optional()])
    dosis = StringField('Dosis', validators=[Optional()])
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    costo = FloatField('Costo', validators=[DataRequired(message='Ingrese el costo')])
    submit = SubmitField('Guardar Servicio de Salud')