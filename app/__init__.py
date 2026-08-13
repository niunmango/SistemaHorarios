import os
import threading
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

from app.version import get_version

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()
_db_init_lock = threading.Lock()

def _wait_for_db(app, attempts=30, delay=2):
    """Espera hasta que la base de datos esté disponible (útil al arrancar con MariaDB vía Podman Compose)."""
    from sqlalchemy import text
    for i in range(attempts):
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            return True
        except Exception:
            if i < attempts - 1:
                time.sleep(delay)
    return False

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    base_url_env = os.environ.get('BASE_URL', 'horarios.curza.com.ar').strip()
    if base_url_env.startswith(('http://', 'https://')):
        full_base_url = base_url_env
        base_url_domain = base_url_env.split('://', 1)[1].rstrip('/')
    else:
        base_url_domain = base_url_env.rstrip('/')
        full_base_url = f"https://{base_url_domain}"

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-curzas-horarios-2026'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(app.instance_path, 'sistema_horarios.db')}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TEMPLATES_AUTO_RELOAD=True,
        BASE_URL=base_url_domain,
        FULL_BASE_URL=full_base_url,
        VERSION=get_version(),
        OAUTH_CLIENT_ID=os.environ.get('OAUTH_CLIENT_ID', ''),
        OAUTH_CLIENT_SECRET=os.environ.get('OAUTH_CLIENT_SECRET', ''),
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    oauth.init_app(app)
    if app.config.get('OAUTH_CLIENT_ID'):
        oauth.register(
            name='google',
            client_id=app.config['OAUTH_CLIENT_ID'],
            client_secret=app.config['OAUTH_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth import auth_bp
    from app.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_system_config():
        base_url_val = app.config.get('BASE_URL', 'horarios.curza.com.ar')
        full_base_url_val = app.config.get('FULL_BASE_URL', 'https://horarios.curza.com.ar')
        version_val = app.config.get('VERSION', get_version())
        try:
            from app.models import ConfiguracionSistema
            config = ConfiguracionSistema.get_config()
            return dict(config=config, base_url=base_url_val, full_base_url=full_base_url_val, version=version_val)
        except Exception:
            return dict(config=None, base_url=base_url_val, full_base_url=full_base_url_val, version=version_val)

    with app.app_context():
        with _db_init_lock:
            if not _wait_for_db(app):
                raise RuntimeError('No se pudo conectar a la base de datos después de varios intentos.')

            db.create_all()

            try:
                if not app.config.get('TESTING') and User.query.count() == 0:
                    from app.seed import seed_database
                    seed_database()
            except Exception:
                pass

            try:
                from app.models import ConfiguracionSistema
                if ConfiguracionSistema.query.count() == 0:
                    config = ConfiguracionSistema(congelado=False)
                    db.session.add(config)
                    db.session.commit()
            except Exception:
                pass

    return app

# Exponer instancia por defecto para servidores WSGI que ejecutan 'gunicorn app:app'
app = create_app()
