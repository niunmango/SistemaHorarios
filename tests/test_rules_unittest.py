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

    def test_materias_route_lists_subjects(self):
        seed_database()
        user = User(username='testgestor', email='gestor@test.com', role='admin', nombre_completo='Test Gestor')
        user.set_password('test')
        db.session.add(user)
        db.session.commit()

        client = self.app.test_client()
        client.post('/login', data={'username': 'testgestor', 'password': 'test'})
        res = client.get('/materias')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Planes de Estudio y Cátedras', res.get_data(as_text=True))
        # Verify that seeded subjects like "Introducción a la Programación" are in the response
        self.assertIn('Introducción a la Programación', res.get_data(as_text=True))


    def test_editar_bloque_route(self):
        seed_database()
        user = User(username='testgestor', email='gestor@test.com', role='admin', nombre_completo='Test Gestor')
        user.set_password('test')
        db.session.add(user)
        db.session.commit()

        bloque = BloqueHorario.query.first()
        self.assertIsNotNone(bloque)

        client = self.app.test_client()
        client.post('/login', data={'username': 'testgestor', 'password': 'test'})
        res = client.get(f'/bloques/{bloque.id}/editar')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Editar Clase / Reserva', res.get_data(as_text=True))


    def test_materia_clases_route(self):
        seed_database()
        user = User(username='testgestor', email='gestor@test.com', role='admin', nombre_completo='Test Gestor')
        user.set_password('test')
        db.session.add(user)
        db.session.commit()

        asig = Asignatura.query.first()
        self.assertIsNotNone(asig)

        client = self.app.test_client()
        client.post('/login', data={'username': 'testgestor', 'password': 'test'})
        res = client.get(f'/materias/{asig.id}/clases')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Clases Programadas Actualmente', res.get_data(as_text=True))

    def test_registro_publico_fuerza_rol_alumno(self):
        client = self.app.test_client()
        # Intentar autorregistrarse como 'admin' desde el formulario público
        res = client.post('/register', data={
            'username': 'attacker',
            'email': 'attacker@test.com',
            'nombre_completo': 'Attacker Admin',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        
        user = User.query.filter_by(username='attacker').first()
        self.assertIsNotNone(user)
        # El rol debe ser estrictamente 'alumno'
        self.assertEqual(user.role, 'alumno')
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_gestor)

    def test_crear_usuario_duplicado_email_mantiene_estabilidad(self):
        seed_database()
        user_admin = User.query.filter_by(username='admin').first()
        client = self.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})

        # Intentar crear un usuario con el email de un usuario ya existente
        res = client.post('/usuarios/nuevo', data={
            'username': 'nuevo_user',
            'email': 'admin@curza.com.ar', # Email duplicado
            'nombre_completo': 'Otro Admin',
            'password': 'password123',
            'role': 'alumno'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('correo electrónico ya está registrado', res.get_data(as_text=True))

    def test_mover_bloque_api_horario_invalido(self):
        seed_database()
        client = self.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        bloque = BloqueHorario.query.first()

        # Enviar horario que excedería las 24 horas del día
        res = client.post(f'/api/bloque/{bloque.id}/mover', json={
            'dia_semana': 0,
            'hora_inicio': '23:30'
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])

    def test_deshacer_bloque_exitoso(self):
        seed_database()
        client = self.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # Crear un bloque limpio sin conflictos iniciales
        asig = Asignatura.query.first()
        bloque = BloqueHorario(
            asignatura_id=asig.id,
            dia_semana=4, # Viernes
            hora_inicio=time(8, 0),
            hora_fin=time(10, 0),
            duracion_horas=2.0,
            modalidad='Virtual',
            es_sincronico=True
        )
        db.session.add(bloque)
        db.session.commit()
            
        dia_original = bloque.dia_semana
        hora_original = bloque.hora_inicio.strftime('%H:%M')

        # 1. Mover bloque a un nuevo día/horario disponible (Jueves = 3, 10:00)
        res_mover = client.post(f'/api/bloque/{bloque.id}/mover', json={
            'dia_semana': 3,
            'hora_inicio': '10:00'
        })
        self.assertEqual(res_mover.status_code, 200)
        self.assertTrue(res_mover.get_json()['success'])

        db.session.refresh(bloque)
        self.assertEqual(bloque.dia_semana, 3)

        # 2. Deshacer el cambio vía /api/bloque/<id>/deshacer
        res_undo = client.post(f'/api/bloque/{bloque.id}/deshacer')
        self.assertEqual(res_undo.status_code, 200)
        data_undo = res_undo.get_json()
        self.assertTrue(data_undo['success'])
        self.assertIn('restaurada', data_undo['message'])

        db.session.refresh(bloque)
        self.assertEqual(bloque.dia_semana, dia_original)
        self.assertEqual(bloque.hora_inicio.strftime('%H:%M'), hora_original)

    def test_deshacer_bloque_sin_cambios_previos(self):
        seed_database()
        client = self.app.test_client()
        client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        bloque = BloqueHorario.query.first()

        # Intentar deshacer un bloque que no ha sido editado
        res_undo = client.post(f'/api/bloque/{bloque.id}/deshacer')
        self.assertEqual(res_undo.status_code, 400)
        data = res_undo.get_json()
        self.assertFalse(data['success'])
        self.assertIn('No hay cambios previos', data['error'])

    def test_base_url_configuracion_defecto_y_personalizado(self):
        # 1. Verificar valor por defecto
        self.assertEqual(self.app.config['BASE_URL'], 'horarios.curza.com.ar')
        self.assertEqual(self.app.config['FULL_BASE_URL'], 'https://horarios.curza.com.ar')

        # 2. Verificar sobreescritura con custom BASE_URL
        custom_app = create_app({
            'TESTING': True,
            'BASE_URL': 'mihorario.ejemplo.edu.ar',
            'FULL_BASE_URL': 'https://mihorario.ejemplo.edu.ar'
        })
        self.assertEqual(custom_app.config['BASE_URL'], 'mihorario.ejemplo.edu.ar')
        self.assertEqual(custom_app.config['FULL_BASE_URL'], 'https://mihorario.ejemplo.edu.ar')

    def test_versionado_sistema(self):
        from app.version import get_version
        v = get_version()
        self.assertTrue(v.startswith('0.1.'))
        self.assertEqual(self.app.config['VERSION'], v)


if __name__ == '__main__':
    unittest.main()
