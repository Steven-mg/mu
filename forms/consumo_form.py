from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TextAreaField, FloatField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Optional


class ConsumoLecheForm(FlaskForm):
    id_producto = HiddenField('Producto leche')
    cantidad = FloatField('Cantidad', validators=[DataRequired(message='Ingrese la cantidad')])
    fecha = DateField('Fecha', validators=[DataRequired(message='Ingrese la fecha')])
    notas_produccion = TextAreaField('Notas', validators=[Optional()])
    submit = SubmitField('Guardar Leche')


class ConsumoProductoForm(FlaskForm):
    id_producto = SelectField('Producto consumible', coerce=int, validators=[DataRequired(message='Seleccione el producto')])
    cantidad = FloatField('Cantidad', validators=[DataRequired(message='Ingrese la cantidad')])
    fecha = DateField('Fecha', validators=[DataRequired(message='Ingrese la fecha')])
    notas_produccion = TextAreaField('Notas', validators=[Optional()])
    submit = SubmitField('Guardar Consumo')