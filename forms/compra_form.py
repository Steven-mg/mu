from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, FloatField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Optional
from datetime import date

class CompraAnimalForm(FlaskForm):
    fecha_compra = DateField('Fecha de Compra', validators=[DataRequired()], default=date.today)
    precio_compra = FloatField('Precio de Compra (COP)', validators=[DataRequired()], default=0)
    vendedor = StringField('Vendedor', validators=[Optional()])
    lugar_compra = StringField('Lugar de Compra', validators=[Optional()])
    documento_compra = StringField('Documento de Compra', validators=[Optional()])
    peso_compra = FloatField('Peso en la Compra (kg)', validators=[Optional()])
    edad_compra = IntegerField('Edad en la Compra (meses)', validators=[Optional()])
    estado_salud_compra = TextAreaField('Estado de Salud en la Compra', validators=[Optional()])
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    submit = SubmitField('Guardar Datos de Compra')