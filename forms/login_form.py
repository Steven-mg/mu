from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    nik_name = StringField('Nombre de Usuario o Correo Electrónico', validators=[DataRequired(), Length(min=2, max=50)])
    contraseña = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')