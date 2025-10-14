from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, BooleanField, FileField, EmailField
from wtforms.validators import DataRequired, Length, Email, Optional
from modelo.models import Finca

class TrabajadorForm(FlaskForm):
    nik_name = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=50)])
    nombres = StringField('Nombres', validators=[Optional(), Length(max=50)])
    apellidos = StringField('Apellidos', validators=[Optional(), Length(max=50)])
    documento = StringField('Documento', validators=[DataRequired(), Length(max=20)])
    correo = EmailField('Correo', validators=[Optional(), Email(message='Correo electrónico inválido')])
    telefono = StringField('Teléfono', validators=[Optional(), Length(max=15)])
    foto = FileField('Foto', validators=[Optional()])
    # Rol global del trabajador (según tabla legacy `trabajador`)
    rol = SelectField('Rol (global)', choices=[('administrador', 'Administrador'), ('operario', 'Operario'), ('veterinario', 'Veterinario')], coerce=str, validators=[DataRequired()])
    # Rol solo aplica si se asigna a una finca; hacerlo opcional
    rol_en_finca = SelectField('Rol', choices=[(1, 'Trabajador'), (2, 'Veterinario'), (3, 'Administrador')], coerce=int, validators=[Optional()])
    # Finca opcional: permitir "Sin asignar" como 0
    finca_id = SelectField('Finca', coerce=int)
    puede_editar = BooleanField('Puede editar en la finca')
    submit = SubmitField('Guardar Trabajador')

    def __init__(self, *args, **kwargs):
        super(TrabajadorForm, self).__init__(*args, **kwargs)
        # Cargar fincas existentes para asignación, con opción de no asignar
        try:
            self.finca_id.choices = [(0, 'Sin asignar')] + [(f.id_finca, f.nombre_finca) for f in Finca.query.all()]
        except Exception:
            # En contextos sin DB disponible (tests), mantener opción mínima
            self.finca_id.choices = [(0, 'Sin asignar')]