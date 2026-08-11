import os
from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import User, Profesor

auth_bp = Blueprint('auth', __name__)

def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    if test_url.scheme or test_url.netloc:
        return test_url.scheme == ref_url.scheme and test_url.netloc == ref_url.netloc
    return target.startswith('/') and not target.startswith('//') and not target.startswith('\\')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.horarios' if current_user.is_alumno else 'main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))

        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user is None or not user.check_password(password):
            flash('Usuario o contraseña incorrectos.', 'danger')
            return render_template('login.html')

        login_user(user, remember=remember_me)
        next_page = request.args.get('next')
        if not is_safe_url(next_page):
            next_page = url_for('main.horarios' if user.is_alumno else 'main.dashboard')

        flash(f'¡Bienvenido/a, {user.nombre_completo}!', 'success')
        return redirect(next_page)

    return render_template('login.html')


# RUTA INICIO DE AUTENTICACIÓN OAUTH 2.0
@auth_bp.route('/login/oauth')
def login_oauth():
    if current_user.is_authenticated:
        return redirect(url_for('main.horarios' if current_user.is_alumno else 'main.dashboard'))

    if hasattr(oauth, 'google') and current_app.config.get('OAUTH_CLIENT_ID'):
        redirect_uri = url_for('auth.auth_callback', _external=True)
        return oauth.google.authorize_redirect(redirect_uri)
    else:
        # En caso de no tener configurado OAUTH_CLIENT_ID en variables de entorno, demostración asistida
        flash('Inicio con OAuth 2.0 (Google/UNComa): Para conectar con un proveedor real configure OAUTH_CLIENT_ID y OAUTH_CLIENT_SECRET en las variables de entorno.', 'info')
        return redirect(url_for('auth.login'))


# CALLBACK OAUTH 2.0
@auth_bp.route('/auth/callback')
def auth_callback():
    if not hasattr(oauth, 'google'):
        flash('OAuth 2.0 no configurado.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo') if token else None
        if not user_info and token:
            user_info = oauth.google.userinfo()
    except Exception as e:
        flash(f'Error durante la autenticación OAuth 2.0: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))

    if not user_info:
        flash('No se obtuvo información de usuario desde el proveedor OAuth 2.0.', 'danger')
        return redirect(url_for('auth.login'))

    email = user_info.get('email')
    if not email:
        flash('No se pudo obtener el correo electrónico desde el proveedor OAuth 2.0.', 'danger')
        return redirect(url_for('auth.login'))

    nombre_completo = user_info.get('name') or email.split('@')[0]

    # Buscar usuario existente por email
    user = User.query.filter_by(email=email).first()

    if not user:
        # Auto-registro mediante OAuth 2.0 con sufijo si hay colisión de username
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{counter}"
            counter += 1
        
        # Verificar si coincide con un profesor registrado
        prof = Profesor.query.filter_by(email=email).first()
        role = 'docente' if prof else 'alumno'

        user = User(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            role=role,
            profesor=prof
        )
        user.set_password(os.urandom(16).hex()) # Contraseña aleatoria segura para cuentas OAuth
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash(f'¡Autenticación OAuth 2.0 exitosa! Bienvenido/a {user.nombre_completo}.', 'success')
    return redirect(url_for('main.horarios' if user.is_alumno else 'main.dashboard'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.horarios' if current_user.is_alumno else 'main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        nombre_completo = request.form.get('nombre_completo', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Seguridad: El autoregistro público SIEMPRE asigna el rol de alumno.
        # Los roles de gestión/admin son asignados exclusivamente por un Administrador en /usuarios/nuevo.
        role = 'alumno'

        if not username or not email or not password or not nombre_completo:
            flash('Por favor complete todos los campos requeridos.', 'warning')
            return render_template('register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya se encuentra registrado.', 'warning')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya se encuentra registrado.', 'warning')
            return render_template('register.html')

        user = User(username=username, email=email, nombre_completo=nombre_completo, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Cuenta creada con éxito. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')
