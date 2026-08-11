import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-curzas-horarios-2026'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(app.instance_path, 'sistema_horarios.db')}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
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

    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

        try:
            if not app.config.get('TESTING') and User.query.count() == 0:
                from app.seed import seed_database
                seed_database()
        except Exception:
            pass

    return app
