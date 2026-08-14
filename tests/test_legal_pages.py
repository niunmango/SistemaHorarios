import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import unittest
from app import create_app, db

class TestLegalPages(unittest.TestCase):

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'BASE_URL': 'horarios.curza.com.ar'
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_pagina_terminos_status_and_content(self):
        response = self.client.get('/terminos')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('Condiciones del Servicio', content)
        self.assertIn('CURZAS', content)
        self.assertIn('Universidad Nacional del Comahue', content)

    def test_pagina_terminos_alias(self):
        response = self.client.get('/condiciones-del-servicio')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('Condiciones del Servicio', content)

    def test_pagina_privacidad_status_and_content(self):
        response = self.client.get('/privacidad')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('Política de Privacidad', content)
        self.assertIn('Google OAuth 2.0', content)
        self.assertIn('Google API Services User Data Policy', content)

    def test_pagina_privacidad_alias(self):
        response = self.client.get('/politica-de-privacidad')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('Política de Privacidad', content)

    def test_footer_contains_legal_links(self):
        response = self.client.get('/horarios')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('/terminos', content)
        self.assertIn('/privacidad', content)

    def test_pagina_principal_nombre_y_proposito(self):
        response = self.client.get('/horarios')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('Horarios', content)
        self.assertIn('Propósito de la aplicación', content)
        self.assertIn('CURZAS', content)
        self.assertIn('Universidad Nacional del Comahue', content)
        self.assertIn('Google OAuth 2.0', content)
        self.assertIn('Consulta Pública', content)

    def test_login_page_nombre_y_proposito(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('Horarios', content)
        self.assertIn('Google', content)


if __name__ == '__main__':
    unittest.main()

