import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import unittest
from datetime import time
from app import create_app, db
from app.models import User, Carrera, Asignatura, EspacioFisico, BloqueHorario, Profesor
from app.rules import calcular_minimo_sincronico, validar_bloque_nuevo, auditar_sistema_completo, obtener_ids_bloques_en_conflicto
from app.seed import seed_database

class TestSistemaHorariosRules(unittest.TestCase):

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_calculo_minimo_sincronico(self):
        # Rule >50%: floor(total / 2) + 1
        self.assertEqual(calcular_minimo_sincronico(4), 3)
        self.assertEqual(calcular_minimo_sincronico(8), 5)
        self.assertEqual(calcular_minimo_sincronico(10), 6)

    def test_solapamiento_aula_fisica(self):
        carrera = Carrera(codigo='TUASSL', nombre='TUASSL')
        db.session.add(carrera)
        db.session.commit()

        asig1 = Asignatura(carrera_id=carrera.id, anio_cursada=1, cuatrimestre=2, nombre='Prog 1', carga_horaria_semanal=8)
        asig2 = Asignatura(carrera_id=carrera.id, anio_cursada=2, cuatrimestre=2, nombre='Prog 2', carga_horaria_semanal=8)
        db.session.add_all([asig1, asig2])
        
        aula = EspacioFisico(nombre='Sala 1 (JCBrocca)', capacidad=30)
        db.session.add(aula)
        db.session.commit()

        b1 = BloqueHorario(asignatura_id=asig1.id, espacio_fisico_id=aula.id, dia_semana=0, hora_inicio=time(15,0), hora_fin=time(17,0), duracion_horas=2.0, modalidad='Presencial', es_sincronico=True)
        db.session.add(b1)
        db.session.commit()

        valido, errores, adv = validar_bloque_nuevo(asig2.id, 0, time(16,0), time(18,0), 'Presencial', aula.id)
        self.assertFalse(valido)
        self.assertTrue(len(errores) > 0)
        self.assertIn('Conflicto de Aula', errores[0])

    def test_conflicto_docente_mismo_horario(self):
        carrera = Carrera(codigo='TUASSL', nombre='TUASSL')
        db.session.add(carrera)
        db.session.commit()

        asig1 = Asignatura(carrera_id=carrera.id, anio_cursada=1, cuatrimestre=2, nombre='Prog 1', carga_horaria_semanal=8)
        asig2 = Asignatura(carrera_id=carrera.id, anio_cursada=2, cuatrimestre=2, nombre='Prog 2', carga_horaria_semanal=8)
        db.session.add_all([asig1, asig2])
        
        prof = Profesor(nombre_completo='Prof. Ramiro García Poggi', categoria_habitual='PAD')
        db.session.add(prof)
        db.session.commit()

        # Class 1: Ramiro as PAD on Lunes 15:00 - 17:00
        b1 = BloqueHorario(asignatura_id=asig1.id, profesor_id=prof.id, rol_docente='PAD', dia_semana=0, hora_inicio=time(15,0), hora_fin=time(17,0), duracion_horas=2.0, modalidad='Virtual', es_sincronico=True)
        db.session.add(b1)
        db.session.commit()

        # Class 2: Ramiro as AYP on Lunes 16:00 - 18:00 (Collision!)
        valido, errores, adv = validar_bloque_nuevo(asig2.id, 0, time(16,0), time(18,0), 'Virtual', profesor_id=prof.id)
        self.assertFalse(valido)
        self.assertTrue(len(errores) > 0)
        self.assertIn('Conflicto de Docente', errores[0])

    def test_seeder_y_auditoria(self):
        seed_database()
        reporte = auditar_sistema_completo()
        self.assertGreater(reporte['total_asignaturas'], 10)
        self.assertGreater(reporte['cumplen_sincronico'], 0)


if __name__ == '__main__':
    unittest.main()
