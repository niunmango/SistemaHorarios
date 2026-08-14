import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import unittest
from datetime import time
from app import create_app, db
from app.models import User, Carrera, Asignatura, Profesor, EspacioFisico, BloqueHorario, SolicitudCambio, Auditoria, ConfiguracionSistema


class TestDeletionSecurity(unittest.TestCase):

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
        })
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Configuración
        ConfiguracionSistema.get_config()

        # Usuarios
        self.admin = User(username='admin_test', email='admin@uncoma.edu.ar', nombre_completo='Admin User', role='admin')
        self.admin.set_password('pass123')

        self.gestor = User(username='gestor_test', email='gestor@uncoma.edu.ar', nombre_completo='Gestor User', role='gestor')
        self.gestor.set_password('pass123')

        self.docente = User(username='docente_test', email='docente@uncoma.edu.ar', nombre_completo='Docente User', role='docente')
        self.docente.set_password('pass123')

        self.alumno = User(username='alumno_test', email='alumno@uncoma.edu.ar', nombre_completo='Alumno User', role='alumno')
        self.alumno.set_password('pass123')

        db.session.add_all([self.admin, self.gestor, self.docente, self.alumno])
        db.session.commit()

        # Carrera
        self.carrera = Carrera(codigo='TUDW', nombre='Tecnicatura en Desarrollo Web')
        db.session.add(self.carrera)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self, username, password='pass123'):
        self.client.get('/logout', follow_redirects=True)
        return self.client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_eliminar_materia_solo_admin(self):
        materia = Asignatura(carrera_id=self.carrera.id, anio_cursada=1, cuatrimestre=1, nombre='Bases de Datos I', carga_horaria_semanal=8)
        db.session.add(materia)
        db.session.commit()
        m_id = materia.id

        # Gestor intenta borrar -> Debe ser rechazado
        self._login('gestor_test')
        res = self.client.post(f'/materias/{m_id}/eliminar', data={'confirm_nombre': 'Bases de Datos I'}, follow_redirects=True)
        self.assertIn(b'Solo el administrador de la plataforma puede eliminar materias', res.data)
        self.assertIsNotNone(db.session.get(Asignatura, m_id))

        # Docente intenta borrar -> Debe ser rechazado
        self._login('docente_test')
        res = self.client.post(f'/materias/{m_id}/eliminar', data={'confirm_nombre': 'Bases de Datos I'}, follow_redirects=True)
        self.assertIn(b'Solo el administrador de la plataforma puede eliminar materias', res.data)
        self.assertIsNotNone(db.session.get(Asignatura, m_id))

    def test_eliminar_materia_confirmacion_fuerte(self):
        materia = Asignatura(carrera_id=self.carrera.id, anio_cursada=1, cuatrimestre=1, nombre='Programacion Web I', carga_horaria_semanal=8)
        db.session.add(materia)
        db.session.commit()
        m_id = materia.id

        self._login('admin_test')

        # Confirmación incorrecta -> Debe fallar
        res = self.client.post(f'/materias/{m_id}/eliminar', data={'confirm_nombre': 'Programacion Web'}, follow_redirects=True)
        self.assertIn(b'no coincide con el nombre exacto', res.data)
        self.assertIsNotNone(db.session.get(Asignatura, m_id))

        # Confirmación exacta -> Éxito
        res = self.client.post(f'/materias/{m_id}/eliminar', data={'confirm_nombre': 'Programacion Web I'}, follow_redirects=True)
        self.assertIn(b'fueron eliminadas con', res.data)
        self.assertIsNone(db.session.get(Asignatura, m_id))

        # Auditoría registrada
        aud = Auditoria.query.filter_by(accion='eliminar_materia').first()
        self.assertIsNotNone(aud)
        self.assertIn('Programacion Web I', aud.detalles)

    def test_eliminar_materia_con_bloques_y_solicitudes(self):
        prof = Profesor(nombre_completo='Prof. Juan Perez', categoria_habitual='PAD')
        db.session.add(prof)
        db.session.commit()

        materia = Asignatura(carrera_id=self.carrera.id, anio_cursada=1, cuatrimestre=1, nombre='Algoritmos', carga_horaria_semanal=4, profesor_pad_id=prof.id)
        db.session.add(materia)
        db.session.commit()

        bloque = BloqueHorario(asignatura_id=materia.id, profesor_id=prof.id, dia_semana=1, hora_inicio=time(9,0), hora_fin=time(12,0), duracion_horas=3.0, modalidad='Presencial', tipo='Teoría', es_sincronico=True)
        db.session.add(bloque)
        db.session.commit()

        sol = SolicitudCambio(bloque_id=bloque.id, profesor_id=prof.id, solicitado_por_id=self.docente.id, descripcion='Cambio de horario')
        db.session.add(sol)
        db.session.commit()

        self._login('admin_test')
        res = self.client.post(f'/materias/{materia.id}/eliminar', data={'confirm_nombre': 'Algoritmos'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(db.session.get(Asignatura, materia.id))
        self.assertIsNone(db.session.get(BloqueHorario, bloque.id))
        self.assertEqual(SolicitudCambio.query.filter_by(bloque_id=bloque.id).count(), 0)

    def test_eliminar_profesor_solo_admin(self):
        prof = Profesor(nombre_completo='Prof. Maria Rodriguez', categoria_habitual='PAD')
        db.session.add(prof)
        db.session.commit()
        p_id = prof.id

        # Gestor intenta borrar -> Rechazado
        self._login('gestor_test')
        res = self.client.post(f'/profesores/{p_id}/eliminar', data={'confirm_nombre': 'Prof. Maria Rodriguez'}, follow_redirects=True)
        self.assertIn(b'Solo el administrador de la plataforma puede dar de baja profesores', res.data)
        self.assertIsNotNone(db.session.get(Profesor, p_id))

    def test_eliminar_profesor_confirmacion_fuerte(self):
        prof = Profesor(nombre_completo='Prof. Carlos Gomez', categoria_habitual='AYP')
        db.session.add(prof)
        db.session.commit()
        p_id = prof.id

        self._login('admin_test')

        # Nombre incorrecto -> Rechazado
        res = self.client.post(f'/profesores/{p_id}/eliminar', data={'confirm_nombre': 'Carlos Gomez'}, follow_redirects=True)
        self.assertIn(b'no coincide con el nombre exacto', res.data)
        self.assertIsNotNone(db.session.get(Profesor, p_id))

        # Nombre exacto -> Éxito
        res = self.client.post(f'/profesores/{p_id}/eliminar', data={'confirm_nombre': 'Prof. Carlos Gomez'}, follow_redirects=True)
        self.assertIn(b'dado de baja con', res.data)
        self.assertIsNone(db.session.get(Profesor, p_id))

        # Auditoría registrada
        aud = Auditoria.query.filter_by(accion='eliminar_profesor').first()
        self.assertIsNotNone(aud)
        self.assertIn('Prof. Carlos Gomez', aud.detalles)

    def test_eliminar_profesor_limpia_referencias(self):
        prof = Profesor(nombre_completo='Prof. Ana Lopez', categoria_habitual='PAD')
        db.session.add(prof)
        db.session.commit()

        # Vincular usuario
        self.docente.profesor_id = prof.id
        # Vincular materia PAD
        materia = Asignatura(carrera_id=self.carrera.id, anio_cursada=2, cuatrimestre=1, nombre='Redes', carga_horaria_semanal=4, profesor_pad_id=prof.id)
        # Vincular bloque
        db.session.add(materia)
        db.session.commit()

        bloque = BloqueHorario(asignatura_id=materia.id, profesor_id=prof.id, dia_semana=2, hora_inicio=time(10,0), hora_fin=time(12,0), duracion_horas=2.0, modalidad='Presencial', tipo='Teoría', es_sincronico=True)
        db.session.add(bloque)
        db.session.commit()

        self._login('admin_test')
        res = self.client.post(f'/profesores/{prof.id}/eliminar', data={'confirm_nombre': 'Prof. Ana Lopez'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Profesor eliminado
        self.assertIsNone(db.session.get(Profesor, prof.id))

        # Referencias desvinculadas sin error
        db.session.refresh(self.docente)
        self.assertIsNone(self.docente.profesor_id)

        db.session.refresh(materia)
        self.assertIsNone(materia.profesor_pad_id)

        db.session.refresh(bloque)
        self.assertIsNone(bloque.profesor_id)

    def test_sistema_congelado_impide_eliminaciones(self):
        config = ConfiguracionSistema.get_config()
        config.congelado = True
        db.session.commit()

        materia = Asignatura(carrera_id=self.carrera.id, anio_cursada=1, cuatrimestre=1, nombre='Sistemas', carga_horaria_semanal=4)
        prof = Profesor(nombre_completo='Prof. Congelado', categoria_habitual='PAD')
        db.session.add_all([materia, prof])
        db.session.commit()

        self._login('admin_test')

        res1 = self.client.post(f'/materias/{materia.id}/eliminar', data={'confirm_nombre': 'Sistemas'}, follow_redirects=True)
        self.assertIn(b'El sistema est\xc3\xa1 congelado', res1.data)
        self.assertIsNotNone(db.session.get(Asignatura, materia.id))

        res2 = self.client.post(f'/profesores/{prof.id}/eliminar', data={'confirm_nombre': 'Prof. Congelado'}, follow_redirects=True)
        self.assertIn(b'El sistema est\xc3\xa1 congelado', res2.data)
        self.assertIsNotNone(db.session.get(Profesor, prof.id))

    def test_editar_aula_gestor_y_admin(self):
        aula = EspacioFisico(
            nombre='Aula 101',
            capacidad=25,
            es_laboratorio=False,
            equipamiento='Pizarrón',
            activa=True
        )
        db.session.add(aula)
        db.session.commit()
        a_id = aula.id

        # Alumno intenta editar -> Rechazado
        self._login('alumno_test')
        res = self.client.post(f'/aulas/{a_id}/editar', data={
            'nombre': 'Aula 101 Modificada',
            'tipo_espacio': 'laboratorio',
            'capacidad': '50',
            'equipamiento': '50 PCs con Linux',
            'activa': '1'
        }, follow_redirects=True)
        self.assertIn(b'No tienes permisos para editar espacios', res.data)

        # Gestor edita aula -> Éxito
        self._login('gestor_test')
        res_get = self.client.get(f'/aulas/{a_id}/editar')
        self.assertEqual(res_get.status_code, 200)

        res_post = self.client.post(f'/aulas/{a_id}/editar', data={
            'nombre': 'Laboratorio 101',
            'tipo_espacio': 'laboratorio',
            'capacidad': '45',
            'equipamiento': '45 PCs con Linux/Windows, Proyector 4K',
            'activa': '1'
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b'actualizado con', res_post.data)

        # Verificar cambios en base de datos
        db.session.refresh(aula)
        self.assertEqual(aula.nombre, 'Laboratorio 101')
        self.assertTrue(aula.es_laboratorio)
        self.assertEqual(aula.capacidad, 45)
        self.assertEqual(aula.equipamiento, '45 PCs con Linux/Windows, Proyector 4K')
        self.assertTrue(aula.activa)

        # Auditoría registrada
        aud = Auditoria.query.filter_by(accion='editar_aula').first()
        self.assertIsNotNone(aud)
        self.assertIn('Laboratorio 101', aud.detalles)


if __name__ == '__main__':
    unittest.main()

