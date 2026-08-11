from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

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
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')

        flash(f'¡Bienvenido/a, {user.nombre_completo}!', 'success')
        return redirect(next_page)

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        nombre_completo = request.form.get('nombre_completo', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'alumno')

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
