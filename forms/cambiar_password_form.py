from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class CambiarPasswordForm(FlaskForm):
    nueva_contraseña = PasswordField('Nueva contraseña', validators=[DataRequired(), Length(min=4, max=128)])
    confirmar_contraseña = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('nueva_contraseña', message='Las contraseñas no coinciden')])
    submit = SubmitField('Actualizar contraseña')