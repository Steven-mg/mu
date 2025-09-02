from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from modelo.models import Finca

class FincaForm(FlaskForm):
    nombre_finca = StringField('Nombre de la Finca', validators=[DataRequired(), Length(min=2, max=30)])
    localizacion = StringField('Localización', validators=[Length(max=100)])
    correo = EmailField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono', validators=[Length(max=15)])
    nombreEncargado = StringField('Nombre del Encargado', validators=[Length(max=40)])
    pais = StringField('País', validators=[Length(max=50)])
    departamento = StringField('Departamento', validators=[Length(max=50)])
    ciudad = StringField('Ciudad/Localidad', validators=[Length(max=50)])
    submit = SubmitField('Guardar Finca')
    
    def validate_nombre_finca(self, nombre_finca):
        finca = Finca.query.filter_by(nombre_finca=nombre_finca.data).first()
        if finca:
            raise ValidationError('Este nombre de finca ya está en uso. Por favor, elija otro.')