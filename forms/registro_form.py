from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from modelo.models import Usuario

class RegistroForm(FlaskForm):
    nik_name = StringField('Nombre de Usuario (Nickname)', validators=[DataRequired(), Length(min=2, max=50)])  # Cambiado de nombre_usuario a nik_name
    nombres = StringField('Nombres', validators=[Length(max=50)])  # Nuevo campo
    apellidos = StringField('Apellidos', validators=[Length(max=50)])  # Nuevo campo
    correo = EmailField('Correo Electrónico', validators=[DataRequired(), Email()])
    contraseña = PasswordField('Contraseña', validators=[Length(min=6)])  # Eliminado DataRequired
    confirmar_contraseña = PasswordField('Confirmar Contraseña', validators=[EqualTo('contraseña', message='Las contraseñas deben coincidir')])  # Eliminado DataRequired
    direccion = StringField('Dirección', validators=[Length(max=30)])  # Eliminado DataRequired
    telefono = StringField('Teléfono', validators=[Length(max=15)])  # Eliminado DataRequired
    pais = StringField('País', validators=[Length(max=50)])
    departamento = StringField('Departamento', validators=[Length(max=50)])
    ciudad = StringField('Ciudad/Localidad', validators=[Length(max=50)])
    submit = SubmitField('Registrarse')
    
    def validate_nik_name(self, nik_name):  # Cambiado de nombre_usuario a nik_name
        usuario = Usuario.query.filter_by(nik_name=nik_name.data).first()  # Cambiado de nombre_usuario a nik_name
        if usuario:
            raise ValidationError('Este nombre de usuario ya está en uso. Por favor, elija otro.')
    
    def validate_correo(self, correo):
        usuario = Usuario.query.filter_by(correo=correo.data).first()
        if usuario:
            raise ValidationError('Este correo electrónico ya está registrado. Por favor, use otro.')