import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import unittest
from app import create_app, db
from app.models import User, Carrera, Asignatura, Profesor, EspacioFisico, BloqueHorario, ConfiguracionSistema


class TestFrozenBannerVisibility(unittest.TestCase):

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

        # Configuración inicial
        self.config = ConfiguracionSistema.get_config()

        # Usuarios de prueba con cada rol
        self.admin = User(username='admin_test', email='admin@curza.com.ar', nombre_completo='Admin User', role='admin')
        self.admin.set_password('pass123')

        self.gestor = User(username='gestor_test', email='gestor@curza.com.ar', nombre_completo='Gestor User', role='gestor')
        self.gestor.set_password('pass123')

        self.docente = User(username='docente_test', email='docente@curza.com.ar', nombre_completo='Docente User', role='docente')
        self.docente.set_password('pass123')

        self.alumno = User(username='alumno_test', email='alumno@curza.com.ar', nombre_completo='Alumno User', role='alumno')
        self.alumno.set_password('pass123')

        db.session.add_all([self.admin, self.gestor, self.docente, self.alumno])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self, username, password='pass123'):
        self.client.get('/logout', follow_redirects=True)
        return self.client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_banner_no_se_muestra_cuando_sistema_descongelado(self):
        """Si el sistema no está congelado, nadie debe ver el banner de congelamiento."""
        self.config.congelado = False
        db.session.commit()

        # Visitante anónimo
        res_anon = self.client.get('/horarios')
        self.assertNotIn('Sistema Congelado', res_anon.get_data(as_text=True))

        # Docente
        self._login('docente_test')
        res_docente = self.client.get('/horarios')
        self.assertNotIn('Sistema Congelado', res_docente.get_data(as_text=True))

        # Alumno
        self._login('alumno_test')
        res_alumno = self.client.get('/horarios')
        self.assertNotIn('Sistema Congelado', res_alumno.get_data(as_text=True))

    def test_banner_se_muestra_a_docentes_gestores_y_admin_cuando_congelado(self):
        """
        Cuando el sistema está congelado:
        - Docente: DEBE ver el banner
        - Gestor: DEBE ver el banner
        - Admin: DEBE ver el banner
        """
        self.config.congelado = True
        self.config.motivo_congelacion = 'Cierre de planificación del cuatrimestre'
        db.session.commit()

        # Docente
        self._login('docente_test')
        res_docente = self.client.get('/horarios')
        html_docente = res_docente.get_data(as_text=True)
        self.assertIn('Sistema Congelado', html_docente)
        self.assertIn('Cierre de planificación del cuatrimestre', html_docente)

        # Gestor
        self._login('gestor_test')
        res_gestor = self.client.get('/horarios')
        html_gestor = res_gestor.get_data(as_text=True)
        self.assertIn('Sistema Congelado', html_gestor)

        # Admin
        self._login('admin_test')
        res_admin = self.client.get('/horarios')
        html_admin = res_admin.get_data(as_text=True)
        self.assertIn('Sistema Congelado', html_admin)

    def test_banner_NO_se_muestra_a_alumnos_ni_publico_cuando_congelado(self):
        """
        Cuando el sistema está congelado:
        - Alumnos: NO deben ver el cartel de congelamiento
        - Público anónimo: NO debe ver el cartel de congelamiento
        """
        self.config.congelado = True
        self.config.motivo_congelacion = 'Cierre de planificación'
        db.session.commit()

        # Público anónimo (sin login)
        self.client.get('/logout', follow_redirects=True)
        res_anon = self.client.get('/horarios')
        html_anon = res_anon.get_data(as_text=True)
        self.assertNotIn('Sistema Congelado — No se permiten cambios', html_anon)

        # Alumno logueado
        self._login('alumno_test')
        res_alumno = self.client.get('/horarios')
        html_alumno = res_alumno.get_data(as_text=True)
        self.assertNotIn('Sistema Congelado — No se permiten cambios', html_alumno)

    def test_menu_opciones_alumno_solo_horarios_y_aulas(self):
        """
        Un usuario con rol Alumno debe ver en su menú únicamente Horarios y Aulas.
        No debe ver enlaces a Dashboard, Materias, Profesores, Bloqueos, Solicitudes, Auditoría ni Usuarios.
        """
        self._login('alumno_test')
        res = self.client.get('/horarios')
        html = res.get_data(as_text=True)

        # Debe ver Horarios y Aulas
        self.assertIn('/horarios', html)
        self.assertIn('/aulas', html)

        # No debe ver opciones de gestión ni administración
        self.assertNotIn('href="/dashboard"', html)
        self.assertNotIn('href="/materias"', html)
        self.assertNotIn('href="/profesores"', html)
        self.assertNotIn('href="/bloqueos_externos"', html)
        self.assertNotIn('href="/solicitudes"', html)
        self.assertNotIn('href="/auditoria"', html)
        self.assertNotIn('href="/usuarios"', html)

    def test_menu_opciones_docente(self):
        """
        Un usuario con rol Docente debe ver Mis Horarios, Mis Cátedras y Aulas.
        No debe ver Dashboard, Profesores, Bloqueos ni Usuarios.
        """
        self._login('docente_test')
        res = self.client.get('/horarios')
        html = res.get_data(as_text=True)

        self.assertIn('/horarios', html)
        self.assertIn('/materias', html)
        self.assertIn('/aulas', html)

        self.assertNotIn('href="/dashboard"', html)
        self.assertNotIn('href="/profesores"', html)
        self.assertNotIn('href="/bloqueos_externos"', html)
        self.assertNotIn('href="/usuarios"', html)

    def test_menu_opciones_gestor_y_admin(self):
        """
        Gestor ve Dashboard, Horarios, Materias, Profesores, Bloqueos, Aulas, Solicitudes, Auditoría.
        Admin además ve Usuarios.
        """
        # Gestor
        self._login('gestor_test')
        res_g = self.client.get('/horarios')
        html_g = res_g.get_data(as_text=True)
        self.assertIn('href="/dashboard"', html_g)
        self.assertIn('href="/materias"', html_g)
        self.assertIn('href="/profesores"', html_g)
        self.assertIn('href="/auditoria"', html_g)
        self.assertNotIn('href="/usuarios"', html_g)

        # Admin
        self._login('admin_test')
        res_a = self.client.get('/horarios')
        html_a = res_a.get_data(as_text=True)
        self.assertIn('href="/dashboard"', html_a)
        self.assertIn('href="/usuarios"', html_a)


if __name__ == '__main__':
    unittest.main()
