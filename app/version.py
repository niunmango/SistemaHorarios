import os

VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VERSION')
DEFAULT_VERSION = '0.1.20260813130743'

def get_version():
    """Retorna la versión actual del sistema."""
    env_version = os.environ.get('APP_VERSION') or os.environ.get('VERSION')
    if env_version:
        return env_version.strip()
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                v = f.read().strip()
                if v:
                    return v
        except Exception:
            pass
    return DEFAULT_VERSION

__version__ = get_version()
