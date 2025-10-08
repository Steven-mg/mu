from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FileField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Optional


class DocumentoGeneticoForm(FlaskForm):
    nombre_documento = StringField(
        'Nombre del documento',
        validators=[Optional(), Length(max=100)]
    )
    tipo_documento = SelectField(
        'Tipo de documento',
        choices=[
            ('', 'Seleccione un tipo'),
            ('prueba_adn', 'Análisis ADN'),
            ('pedigri', 'Pedigrí / Registro genealógico'),
            ('certificado_raza', 'Certificado de raza')
        ],
        validators=[DataRequired(message='Seleccione el tipo de documento')]
    )
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=1000)])
    fecha_emision = DateField('Fecha de emisión', validators=[Optional()])
    entidad_emisora = StringField('Entidad emisora', validators=[Optional(), Length(max=100)])
    archivo = FileField('Archivo', validators=[DataRequired(message='Seleccione un archivo')])


class EditarDocumentoGeneticoForm(FlaskForm):
    nombre_documento = StringField('Nombre del documento', validators=[Optional(), Length(max=100)])
    tipo_documento = SelectField(
        'Tipo de documento',
        choices=[
            ('', 'Seleccione un tipo'),
            ('prueba_adn', 'Análisis ADN'),
            ('pedigri', 'Pedigrí / Registro genealógico'),
            ('certificado_raza', 'Certificado de raza')
        ],
        validators=[DataRequired(message='Seleccione el tipo de documento')]
    )
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=1000)])
    fecha_emision = DateField('Fecha de emisión', validators=[Optional()])
    entidad_emisora = StringField('Entidad emisora', validators=[Optional(), Length(max=100)])
    archivo = FileField('Archivo', validators=[Optional()])