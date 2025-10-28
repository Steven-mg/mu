from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TextAreaField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional

class ServicioSexualForm(FlaskForm):
    id_servicioanimal = SelectField('Tipo de servicio sexual', coerce=int, validators=[DataRequired(message='Seleccione el tipo de servicio sexual')])
    id_veterinario = SelectField('Profesional', coerce=int, validators=[DataRequired(message='Seleccione el profesional')])
    fecha_servicio = DateField('Fecha del servicio', validators=[DataRequired(message='Ingrese la fecha')])
    fecha_proximo = DateField('Próxima fecha', validators=[Optional()])
    notas_servicio = TextAreaField('Notas', validators=[Optional()])
    costo_total = FloatField('Costo', validators=[Optional()])
    submit = SubmitField('Guardar Servicio Sexual')