from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, ValidationError, Optional
from modelo.models import Animal, Raza, Finca, EstadoReproductivo, Potrero, GrupoAnimal
from datetime import date

class FiltroAnimalForm(FlaskForm):
    raza = SelectField('Raza', coerce=int, validators=[Optional()])
    sexo = SelectField('Sexo', choices=[('', 'Todos'), ('Macho', 'Macho'), ('Hembra', 'Hembra')], validators=[Optional()])
    ubicacion = SelectField('Ubicación', 
                          choices=[('', 'Todas'), 
                                  ('en finca', 'En Finca'), 
                                  ('fuera de la finca', 'Fuera de la Finca'), 
                                  ('desconocido', 'Desconocido')], 
                          validators=[Optional()])
    origen = SelectField('Origen', 
                        choices=[('', 'Todos'),
                                ('nacido_en_finca', 'Nacido en Finca'), 
                                ('comprado', 'Comprado'), 
                                ('otro', 'Otro')], 
                        validators=[Optional()])
    estado_reprod = SelectField('Estado Reproductivo', coerce=int, validators=[Optional()])
    submit = SubmitField('Filtrar')
    
    def __init__(self, *args, **kwargs):
        super(FiltroAnimalForm, self).__init__(*args, **kwargs)
        self.raza.choices = [(0, 'Todas las razas')] + [(r.id_raza, r.nombre_raza) for r in Raza.query.all()]
        self.estado_reprod.choices = [(0, 'Todos los estados')] + [(e.id_estado_reprod, e.descripcion) for e in EstadoReproductivo.query.all()]

class AnimalForm(FlaskForm):
    nombre_animal = StringField('Nombre del Animal', validators=[DataRequired(), Length(min=2, max=15)])
    id_raza = SelectField('Raza', coerce=int, validators=[DataRequired()])
    fecha_nacimiento = DateField('Fecha de Nacimiento', validators=[DataRequired()])
    sexo = SelectField('Sexo', choices=[('Macho', 'Macho'), ('Hembra', 'Hembra')], validators=[DataRequired()])
    id_finca = SelectField('Finca', coerce=int, validators=[DataRequired()])
    # validate_choice=False porque las opciones se cargan dinámicamente vía JS
    id_potrero = SelectField('Potrero', coerce=int, validators=[Optional()], validate_choice=False)
    id_grupo = SelectField('Grupo', coerce=int, validators=[Optional()], validate_choice=False)
    id_padre = SelectField('Padre', coerce=int, validators=[Optional()])
    id_madre = SelectField('Madre', coerce=int, validators=[Optional()])
    ubicacion_animal = SelectField('Ubicación', 
                                 choices=[('en finca', 'En Finca'), 
                                         ('fuera de la finca', 'Fuera de la Finca'), 
                                         ('desconocido', 'Desconocido')], 
                                 validators=[DataRequired()])
    foto = FileField('Foto', validators=[Optional()])
    origen = SelectField('Origen', 
                        choices=[('nacido_en_finca', 'Nacido en Finca'), 
                                ('comprado', 'Comprado'), 
                                ('otro', 'Otro')], 
                        validators=[Optional()])
    id_estado_reprod = SelectField('Estado Reproductivo', coerce=int, validators=[Optional()])
    submit = SubmitField('Guardar Animal')
    
    def __init__(self, *args, **kwargs):
        super(AnimalForm, self).__init__(*args, **kwargs)
        # Identificador del animal en edición (si aplica)
        self.editing_id = None
        try:
            obj = kwargs.get('obj')
            if obj is not None and hasattr(obj, 'id_animal'):
                self.editing_id = getattr(obj, 'id_animal')
        except Exception:
            # En caso de no recibir kwargs/obj, mantener editing_id en None
            self.editing_id = None
        
        # Cargar opciones para los SelectField
        self.id_raza.choices = [(0, 'Seleccione una raza')] + [(r.id_raza, r.nombre_raza) for r in Raza.query.all()]
        self.id_finca.choices = [(0, 'Seleccione una finca')] + [(f.id_finca, f.nombre_finca) for f in Finca.query.all()]
        self.id_estado_reprod.choices = [(0, 'Sin estado reproductivo')] + [(e.id_estado_reprod, e.descripcion) for e in EstadoReproductivo.query.all()]
        
        # Inicialmente, sin potreros hasta que se seleccione una finca
        self.id_potrero.choices = [(0, 'Seleccione primero una finca')]
        # Inicialmente, sin grupos hasta que se seleccione potrero (o finca)
        self.id_grupo.choices = [(0, 'Seleccione primero un potrero')]
        
        # Para padre y madre, cargar solo animales machos y hembras respectivamente
        machos = Animal.query.filter_by(sexo='Macho').all()
        hembras = Animal.query.filter_by(sexo='Hembra').all()
        
        self.id_padre.choices = [(0, 'Sin padre registrado')] + [(a.id_animal, a.nombre_animal) for a in machos]
        self.id_madre.choices = [(0, 'Sin madre registrada')] + [(a.id_animal, a.nombre_animal) for a in hembras]

    def validate_nombre_animal(self, nombre_animal):
        # Verificar que el nombre no esté duplicado en la misma finca,
        # excluyendo el propio animal cuando se está editando.
        if self.id_finca.data and self.id_finca.data != 0:
            query = Animal.query.filter(
                Animal.nombre_animal == nombre_animal.data,
                Animal.id_finca == self.id_finca.data
            )
            if self.editing_id:
                query = query.filter(Animal.id_animal != self.editing_id)
            animal = query.first()
            if animal:
                raise ValidationError('Ya existe un animal con este nombre en la finca seleccionada.')

    # --- Validaciones de Genealogía ---
    def _edad_en_dias(self, fecha_nac):
        if not fecha_nac:
            return 0
        try:
            return max(0, (date.today() - fecha_nac).days)
        except Exception:
            return 0

    def validate_id_padre(self, id_padre):
        # Permitir vacío
        if not id_padre.data or id_padre.data == 0:
            return

        # No permitir ser su propio padre
        if self.editing_id and id_padre.data == self.editing_id:
            raise ValidationError('El animal no puede ser su propio padre.')

        padre = Animal.query.get(id_padre.data)
        if not padre:
            return

        # Debe ser de la misma raza que el animal
        try:
            raza_hijo_id = int(self.id_raza.data or 0)
        except Exception:
            raza_hijo_id = 0
        if raza_hijo_id and padre.id_raza and int(padre.id_raza) != raza_hijo_id:
            raise ValidationError('El padre debe ser de la misma raza que el animal.')

        # Calcular edades en días
        edad_padre_dias = self._edad_en_dias(padre.fecha_nacimiento)
        edad_hijo_dias = self._edad_en_dias(self.fecha_nacimiento.data)

        # Obtener umbral de madurez por raza del padre (meses -> días aproximados)
        umbral_meses = 0
        try:
            umbral_meses = int(padre.raza.madurez_sexual_machos_meses or 0)
        except Exception:
            umbral_meses = 0
        umbral_dias = umbral_meses * 30

        # Regla: Padre debe tener al menos (madurez mínima + edad del hijo)
        requerido_dias = umbral_dias + edad_hijo_dias
        if edad_padre_dias < requerido_dias:
            raise ValidationError('El padre seleccionado no cumple la edad mínima requerida (madurez + edad del animal).')

    def validate_id_madre(self, id_madre):
        # Permitir vacío
        if not id_madre.data or id_madre.data == 0:
            return

        # No permitir ser su propia madre
        if self.editing_id and id_madre.data == self.editing_id:
            raise ValidationError('El animal no puede ser su propia madre.')

        madre = Animal.query.get(id_madre.data)
        if not madre:
            return

        # Debe ser de la misma raza que el animal
        try:
            raza_hijo_id = int(self.id_raza.data or 0)
        except Exception:
            raza_hijo_id = 0
        if raza_hijo_id and madre.id_raza and int(madre.id_raza) != raza_hijo_id:
            raise ValidationError('La madre debe ser de la misma raza que el animal.')

        # Calcular edades en días
        edad_madre_dias = self._edad_en_dias(madre.fecha_nacimiento)
        edad_hijo_dias = self._edad_en_dias(self.fecha_nacimiento.data)

        # Umbral de madurez por raza de la madre (meses -> días aproximados)
        umbral_meses = 0
        try:
            umbral_meses = int(madre.raza.madurez_sexual_hembras_meses or 0)
        except Exception:
            umbral_meses = 0
        umbral_dias = umbral_meses * 30

        # Regla: Madre debe tener al menos (madurez mínima + edad del hijo + 260 días)
        requerido_dias = umbral_dias + edad_hijo_dias + 260
        if edad_madre_dias < requerido_dias:
            raise ValidationError('La madre seleccionada no cumple la edad mínima requerida (madurez + edad del animal + 260 días).')