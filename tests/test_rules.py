import pytest
from app import create_app, db
from app.models import Carrera, Asignatura, EspacioFisico, BloqueHorario
from app.rules import calcular_minimo_sincronico, validar_bloque_nuevo
from datetime import time

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_calculo_minimo_sincronico():
    # 4hs -> min 3hs
    assert calcular_minimo_sincronico(4) == 3
    # 8hs -> min 5hs
    assert calcular_minimo_sincronico(8) == 5
    # 10hs -> min 6hs
    assert calcular_minimo_sincronico(10) == 6
    # 6hs -> min 4hs
    assert calcular_minimo_sincronico(6) == 4

def test_solapamiento_aula(app):
    with app.app_context():
        carrera = Carrera(codigo='TUASSL', nombre='TUASSL')
        db.session.add(carrera)
        db.session.commit()

        asig1 = Asignatura(carrera_id=carrera.id, anio_cursada=1, cuatrimestre=2, nombre='Materia 1', carga_horaria_semanal=8)
        asig2 = Asignatura(carrera_id=carrera.id, anio_cursada=2, cuatrimestre=2, nombre='Materia 2', carga_horaria_semanal=8)
        db.session.add_all([asig1, asig2])
        
        aula = EspacioFisico(nombre='Sala 1 Informática', capacidad=30)
        db.session.add(aula)
        db.session.commit()

        # Insert first block: Lunes 15:00 - 17:00 in Sala 1
        b1 = BloqueHorario(asignatura_id=asig1.id, espacio_fisico_id=aula.id, dia_semana=0, hora_inicio=time(15,0), hora_fin=time(17,0), duracion_horas=2.0, modalidad='Presencial', es_sincronico=True)
        db.session.add(b1)
        db.session.commit()

        # Validate overlapping block in same room: Lunes 16:00 - 18:00
        valido, errores, adv = validar_bloque_nuevo(asig2.id, 0, time(16,0), time(18,0), 'Presencial', aula.id)
        assert valido is False
        assert len(errores) > 0
        assert 'Conflicto de Aula' in errores[0]

def test_bloqueo_externo_aula(app):
    with app.app_context():
        carrera_ext = Carrera(codigo='EXTERNA', nombre='Materias Externas')
        carrera_tu = Carrera(codigo='TUDW', nombre='TUDW')
        db.session.add_all([carrera_ext, carrera_tu])
        db.session.commit()

        ext_mat = Asignatura(carrera_id=carrera_ext.id, anio_cursada=1, cuatrimestre=2, nombre='Estadística Aplicada', carga_horaria_semanal=6, es_externa=True)
        tu_mat = Asignatura(carrera_id=carrera_tu.id, anio_cursada=1, cuatrimestre=2, nombre='Prog Web', carga_horaria_semanal=8)
        db.session.add_all([ext_mat, tu_mat])
        
        aula = EspacioFisico(nombre='Sala 2 Informática', capacidad=30)
        db.session.add(aula)
        db.session.commit()

        # Insert external room lock: Martes 13:00 - 15:00 in Sala 2
        b_ext = BloqueHorario(asignatura_id=ext_mat.id, espacio_fisico_id=aula.id, dia_semana=1, hora_inicio=time(13,0), hora_fin=time(15,0), duracion_horas=2.0, modalidad='Bloqueo Aula', es_sincronico=True, es_bloqueo_externo=True)
        db.session.add(b_ext)
        db.session.commit()

        # Validate booking attempt by tecnicatura class in locked time slot: Martes 14:00 - 16:00
        valido, errores, adv = validar_bloque_nuevo(tu_mat.id, 1, time(14,0), time(16,0), 'Presencial', aula.id)
        assert valido is False
        assert len(errores) > 0
        assert 'Bloqueo de Aula Físico' in errores[0]
