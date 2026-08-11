import math
from datetime import datetime, time, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

def utc_now():
    return datetime.now(timezone.utc)

class ConfiguracionSistema(db.Model):
    __tablename__ = 'configuracion_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    congelado = db.Column(db.Boolean, nullable=False, default=False)
    motivo_congelacion = db.Column(db.String(250), nullable=True)
    congelado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    congelado_fecha = db.Column(db.DateTime, nullable=True)
    actualizado_fecha = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    @staticmethod
    def get_config():
        config = ConfiguracionSistema.query.first()
        if not config:
            config = ConfiguracionSistema(congelado=False)
            db.session.add(config)
            db.session.commit()
        return config

    @staticmethod
    def esta_congelado():
        return ConfiguracionSistema.get_config().congelado


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre_completo = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='alumno') # admin, gestor_aulas, docente, alumno
    
    # Vinculación opcional con una entidad Profesor
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=True)
    profesor = db.relationship('Profesor', backref='usuario_asociado', uselist=False)

    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_gestor(self):
        return self.role in ['admin', 'gestor_aulas', 'gestor']

    @property
    def is_docente(self):
        return self.role in ['admin', 'gestor_aulas', 'gestor', 'docente']

    @property
    def is_alumno(self):
        return self.role == 'alumno'

    def puede_editar_bloque(self, bloque):
        if self.is_gestor:
            return True
        if self.role == 'docente' and bloque:
            if self.profesor_id and bloque.profesor_id == self.profesor_id:
                return True
            if bloque.profesor and self.nombre_completo.strip().lower() == bloque.profesor.nombre_completo.strip().lower():
                return True
        return False


class Profesor(db.Model):
    __tablename__ = 'profesores'

    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(120), nullable=False)
    categoria_habitual = db.Column(db.String(20), nullable=True, default='PAD')
    email = db.Column(db.String(120), nullable=True)

    bloques_horarios = db.relationship('BloqueHorario', backref='profesor', lazy=True)


# Tabla Intermedia para Múltiples Ayudantes (AYP) por Materia
asignatura_ayps = db.Table('asignatura_ayps',
    db.Column('asignatura_id', db.Integer, db.ForeignKey('asignaturas.id'), primary_key=True),
    db.Column('profesor_id', db.Integer, db.ForeignKey('profesores.id'), primary_key=True)
)


class Carrera(db.Model):
    __tablename__ = 'carreras'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False) # TUASSL, TUDW, EXTERNA
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    asignaturas = db.relationship('Asignatura', backref='carrera', lazy=True, cascade='all, delete-orphan')


class Asignatura(db.Model):
    __tablename__ = 'asignaturas'
    
    id = db.Column(db.Integer, primary_key=True)
    carrera_id = db.Column(db.Integer, db.ForeignKey('carreras.id'), nullable=False)
    anio_cursada = db.Column(db.Integer, nullable=False) # 1, 2 o 3
    cuatrimestre = db.Column(db.Integer, nullable=False) # 1 o 2 cuatrimestre
    codigo = db.Column(db.String(20), nullable=True)
    nombre = db.Column(db.String(150), nullable=False)
    carga_horaria_semanal = db.Column(db.Integer, nullable=False, default=8) # Total hs semanales
    profesor_cargo = db.Column(db.String(150), nullable=True) # Texto libre / legacy
    es_externa = db.Column(db.Boolean, nullable=False, default=False) # Bloqueo externo / otra materia

    # Un único Profesor PAD (Adjunto / Titular) por Materia
    profesor_pad_id = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=True)
    profesor_pad = db.relationship('Profesor', foreign_keys=[profesor_pad_id], backref='asignaturas_pad')

    # Múltiples Profesores AYP (Ayudantes de Primera / JTPs) por Materia
    profesores_ayp = db.relationship('Profesor', secondary=asignatura_ayps, backref='asignaturas_ayp')

    bloques_horarios = db.relationship('BloqueHorario', backref='asignatura', lazy=True, cascade='all, delete-orphan')

    @property
    def nombre_pad(self):
        if self.profesor_pad:
            return f"{self.profesor_pad.nombre_completo} (PAD)"
        return self.profesor_cargo or "Sin PAD asignado"

    @property
    def nombres_ayps_lista(self):
        if self.profesores_ayp:
            return [f"{p.nombre_completo} (AYP)" for p in self.profesores_ayp]
        return []

    @property
    def min_horas_sincronicas(self):
        if self.es_externa:
            return 0
        return math.floor(self.carga_horaria_semanal / 2) + 1

    @property
    def max_horas_asincronicas(self):
        if self.es_externa:
            return 0
        return self.carga_horaria_semanal - self.min_horas_sincronicas

    @property
    def total_horas_sincronicas_programadas(self):
        return sum(b.duracion_horas for b in self.bloques_horarios if b.es_sincronico)

    @property
    def total_horas_asincronicas_programadas(self):
        return sum(b.duracion_horas for b in self.bloques_horarios if not b.es_sincronico)

    @property
    def cumple_regla_sincronica(self):
        if self.es_externa:
            return True
        return self.total_horas_sincronicas_programadas >= self.min_horas_sincronicas


class EspacioFisico(db.Model):
    __tablename__ = 'espacios_fisicos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False) # Ej: Sala 1 (JCBrocca)
    capacidad = db.Column(db.Integer, default=30)
    es_laboratorio = db.Column(db.Boolean, default=False)
    equipamiento = db.Column(db.String(200), default='Computadoras / Proyector / Red')
    activa = db.Column(db.Boolean, default=True)

    bloques_horarios = db.relationship('BloqueHorario', backref='espacio_fisico', lazy=True)


DIAS_SEMANA = {
    0: 'Lunes',
    1: 'Martes',
    2: 'Miércoles',
    3: 'Jueves',
    4: 'Viernes',
    5: 'Sábado'
}

MODALIDADES = ['Presencial', 'Virtual', 'Híbrido', 'Asincrónico (PEDCO)', 'Bloqueo Aula']
TIPOS_CLASE = ['Teoría', 'Práctica', 'Taller', 'Consulta', 'Plataforma Asincrónica', 'Bloqueo Externo']

class BloqueHorario(db.Model):
    __tablename__ = 'bloques_horarios'
    
    id = db.Column(db.Integer, primary_key=True)
    asignatura_id = db.Column(db.Integer, db.ForeignKey('asignaturas.id'), nullable=False)
    espacio_fisico_id = db.Column(db.Integer, db.ForeignKey('espacios_fisicos.id'), nullable=True) # Null si es Virtual / PEDCO
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesores.id'), nullable=True) # Asignación de docente
    rol_docente = db.Column(db.String(20), nullable=False, default='PAD') # 'PAD' o 'AYP' en ESTE bloque
    
    dia_semana = db.Column(db.Integer, nullable=False) # 0=Lunes..4=Viernes
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    
    duracion_horas = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(50), nullable=False, default='Teoría')
    modalidad = db.Column(db.String(50), nullable=False, default='Presencial')
    es_sincronico = db.Column(db.Boolean, nullable=False, default=True)
    es_bloqueo_externo = db.Column(db.Boolean, nullable=False, default=False)
    observaciones = db.Column(db.String(250), nullable=True)

    @property
    def dia_nombre(self):
        return DIAS_SEMANA.get(self.dia_semana, 'Desconocido')

    @property
    def rol_docente_label(self):
        return 'PAD (Teoría)' if self.rol_docente == 'PAD' else 'AYP (Práctica)'

    @property
    def requiere_aula(self):
        return self.modalidad in ['Presencial', 'Híbrido', 'Bloqueo Aula'] and self.espacio_fisico_id is not None
