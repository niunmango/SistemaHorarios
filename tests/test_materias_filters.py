import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import unittest
from app import create_app, db
from app.models import User, Carrera, Asignatura, Profesor, ConfiguracionSistema


class TestMateriasFilters(unittest.TestCase):

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

        ConfiguracionSistema.get_config()

        # Usuario gestor
        self.gestor = User(username='gestor_test', email='gestor@curza.com.ar', nombre_completo='Gestor Test', role='gestor')
        self.gestor.set_password('pass123')
        db.session.add(self.gestor)

        # Carreras
        self.c1 = Carrera(codigo='TUASSL', nombre='Tecnicatura en Software Libre')
        self.c2 = Carrera(codigo='TUDW', nombre='Tecnicatura en Desarrollo Web')
        self.c_ext = Carrera(codigo='EXTERNA', nombre='Materias Externas')
        db.session.add_all([self.c1, self.c2, self.c_ext])
        db.session.commit()

        # Docentes
        self.p1 = Profesor(nombre_completo='Docente Uno', categoria_habitual='PAD', email='uno@curza.com.ar')
        self.p2 = Profesor(nombre_completo='Docente Dos', categoria_habitual='PAD', email='dos@curza.com.ar')
        db.session.add_all([self.p1, self.p2])
        db.session.commit()

        # Materias
        # TUASSL, 1er año, 1er cuatri
        self.m1 = Asignatura(carrera_id=self.c1.id, anio_cursada=1, cuatrimestre=1, nombre='Intro SL', carga_horaria_semanal=8, profesor_pad_id=self.p1.id)
        # TUASSL, 1er año, 2do cuatri
        self.m2 = Asignatura(carrera_id=self.c1.id, anio_cursada=1, cuatrimestre=2, nombre='Redes SL', carga_horaria_semanal=8, profesor_pad_id=self.p2.id)
        # TUDW, 1er año, 1er cuatri
        self.m3 = Asignatura(carrera_id=self.c2.id, anio_cursada=1, cuatrimestre=1, nombre='Prog Web 1', carga_horaria_semanal=8, profesor_pad_id=self.p1.id)
        # TUDW, 2do año, 2do cuatri
        self.m4 = Asignatura(carrera_id=self.c2.id, anio_cursada=2, cuatrimestre=2, nombre='Prog Web 2', carga_horaria_semanal=8, profesor_pad_id=self.p2.id)
        # Externa, 1er cuatri
        self.m_ext = Asignatura(carrera_id=self.c_ext.id, anio_cursada=1, cuatrimestre=1, nombre='Física Exactas', carga_horaria_semanal=4, es_externa=True)

        db.session.add_all([self.m1, self.m2, self.m3, self.m4, self.m_ext])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self):
        return self.client.post('/login', data={'username': 'gestor_test', 'password': 'pass123'}, follow_redirects=True)

    def test_filtro_combinado_carrera_y_cuatrimestre(self):
        """Filtrar por carrera TUASSL Y 1° cuatrimestre debe mostrar solo Intro SL."""
        self._login()
        res = self.client.get(f'/materias?carrera_id={self.c1.id}&cuatrimestre=1')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Intro SL', html)
        self.assertNotIn('Redes SL', html)
        self.assertNotIn('Prog Web 1', html)
        self.assertNotIn('Prog Web 2', html)
        self.assertNotIn('Física Exactas', html)

    def test_filtro_cuatrimestre_solo(self):
        """Filtrar por 2° cuatrimestre debe mostrar Redes SL y Prog Web 2."""
        self._login()
        res = self.client.get('/materias?cuatrimestre=2')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Redes SL', html)
        self.assertIn('Prog Web 2', html)
        self.assertNotIn('Intro SL', html)
        self.assertNotIn('Prog Web 1', html)

    def test_filtro_combinado_carrera_anio_cuatrimestre(self):
        """Filtrar por TUDW, 2° Año, 2° Cuatrimestre debe mostrar solo Prog Web 2."""
        self._login()
        res = self.client.get(f'/materias?carrera_id={self.c2.id}&anio=2&cuatrimestre=2')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Prog Web 2', html)
        self.assertNotIn('Intro SL', html)
        self.assertNotIn('Redes SL', html)
        self.assertNotIn('Prog Web 1', html)

    def test_filtro_externos(self):
        """Filtrar por 'externas' debe mostrar materias externas."""
        self._login()
        res = self.client.get('/materias?carrera_id=externas')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('Física Exactas', html)
        self.assertNotIn('Intro SL', html)
        self.assertNotIn('Prog Web 1', html)

    def test_renderizado_tres_selects_desplegables(self):
        """Verifica que se rendericen exactamente los select desplegables de carrera, cuatrimestre y anio."""
        self._login()
        res = self.client.get('/materias')
        html = res.get_data(as_text=True)

        self.assertIn('select id="carrera_id"', html)
        self.assertIn('select id="cuatrimestre"', html)
        self.assertIn('select id="anio"', html)
        self.assertNotIn('select id="profesor_id"', html)
        self.assertIn('Externos', html)


if __name__ == '__main__':
    unittest.main()
