import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')
DEFAULT_VERSION = '0.1.20260813131306'

def get_git_version():
    """Obtiene la versión automáticamente basada en la fecha y hora del último commit de Git."""
    try:
        git_dir = os.path.join(BASE_DIR, '.git')
        if os.path.exists(git_dir):
            output = subprocess.check_output(
                ['git', 'log', '-1', '--format=%cd', '--date=format:%Y%m%d%H%M%S'],
                cwd=BASE_DIR,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            if output and len(output) == 14 and output.isdigit():
                return f"0.1.{output}"
    except Exception:
        pass
    return None

def get_version():
    """Retorna la versión actual del sistema."""
    env_version = os.environ.get('APP_VERSION') or os.environ.get('VERSION')
    if env_version:
        return env_version.strip()
    
    git_v = get_git_version()
    if git_v:
        # Sincronizar archivo VERSION opcionalmente
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'w', encoding='utf-8') as f:
                    f.write(f"{git_v}\n")
        except Exception:
            pass
        return git_v

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

