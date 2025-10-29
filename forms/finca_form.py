from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, SelectField
from wtforms.validators import DataRequired, Length, Email, ValidationError, Optional
from modelo.models import Finca

class FincaForm(FlaskForm):
    nombre_finca = StringField('Nombre de la Finca', validators=[DataRequired(), Length(min=2, max=30)])
    localizacion = StringField('Localización', validators=[Length(max=100)])
    correo = EmailField('Correo Electrónico', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono', validators=[Length(max=15)])
    nombreEncargado = SelectField('Nombre del Encargado', choices=[], validators=[Optional(), Length(max=40)], validate_choice=False)
    pais = StringField('País', validators=[Length(max=50)])
    departamento = StringField('Departamento', validators=[Length(max=50)])
    ciudad = StringField('Ciudad/Localidad', validators=[Length(max=50)])
    submit = SubmitField('Guardar Finca')
    
    def __init__(self, *args, **kwargs):
        # Permitir que el controlador de edición pase el ID actual de la finca
        self._finca_id = kwargs.pop('finca_id', None)
        super(FincaForm, self).__init__(*args, **kwargs)
    
    def validate_nombre_finca(self, nombre_finca):
        # Normalizar valor ingresado
        nombre = (nombre_finca.data or '').strip()
        if not nombre:
            return  # DataRequired se encargará

        # Excluir la finca actual al validar duplicados
        duplicada = Finca.query.filter(
            Finca.nombre_finca == nombre,
            Finca.id_finca != (self._finca_id or 0)
        ).first()

        if duplicada:
            raise ValidationError('Este nombre de finca ya está en uso. Por favor, elija otro.')