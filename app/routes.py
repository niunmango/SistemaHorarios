from datetime import datetime, time
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Carrera, Asignatura, EspacioFisico, BloqueHorario, Profesor, DIAS_SEMANA, MODALIDADES, TIPOS_CLASE
from app.rules import auditar_sistema_completo, validar_bloque_nuevo, calcular_minimo_sincronico, obtener_ids_bloques_en_conflicto, obtener_mapa_explicacion_conflictos

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.horarios'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    reporte = auditar_sistema_completo()
    total_carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').count()
    total_materias = Asignatura.query.filter_by(es_externa=False).count()
    total_aulas = EspacioFisico.query.count()
    total_bloques = BloqueHorario.query.count()

    carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').all()
    aulas = EspacioFisico.query.all()
    profesores = Profesor.query.all()

    return render_template('dashboard.html',
                           reporte=reporte,
                           total_carreras=total_carreras,
                           total_materias=total_materias,
                           total_aulas=total_aulas,
                           total_bloques=total_bloques,
                           carreras=carreras,
                           aulas=aulas,
                           profesores=profesores)


# VISTA DE HORARIOS: PÚBLICA PARA ALUMNOS & INTERACTIVA PARA DOCENTES/GESTORES
@main_bp.route('/horarios')
def horarios():
    carrera_id = request.args.get('carrera_id', type=int)
    anio = request.args.get('anio', type=int)
    cuatrimestre = request.args.get('cuatrimestre', type=int, default=2)
    espacio_id = request.args.get('espacio_id', type=int)
    profesor_id = request.args.get('profesor_id', type=int)
    modalidad = request.args.get('modalidad', type=str)
    solo_conflictos = bool(request.args.get('solo_conflictos', type=int))

    query = BloqueHorario.query.join(Asignatura)

    if carrera_id:
        query = query.filter(Asignatura.carrera_id == carrera_id)
    if anio:
        query = query.filter(Asignatura.anio_cursada == anio)
    if cuatrimestre:
        query = query.filter(Asignatura.cuatrimestre == cuatrimestre)
    if espacio_id:
        query = query.filter(BloqueHorario.espacio_fisico_id == espacio_id)
    if profesor_id:
        query = query.filter(BloqueHorario.profesor_id == profesor_id)
    if modalidad:
        query = query.filter(BloqueHorario.modalidad == modalidad)

    ids_conflictos = obtener_ids_bloques_en_conflicto(cuatrimestre=cuatrimestre)
    mapa_conflictos = obtener_mapa_explicacion_conflictos(cuatrimestre=cuatrimestre)

    if solo_conflictos:
        query = query.filter(BloqueHorario.id.in_(ids_conflictos if ids_conflictos else [-1]))

    # Ordenar por día de la semana, hora de inicio y por número de espacio físico
    bloques = query.order_by(
        BloqueHorario.dia_semana,
        BloqueHorario.hora_inicio,
        BloqueHorario.espacio_fisico_id.asc().nulls_last()
    ).all()

    carreras = Carrera.query.all()
    aulas = EspacioFisico.query.all()
    profesores = Profesor.query.all()

    # Horas de 08:00 a 21:00 hs
    horas_lista = [f"{h:02d}:00" for h in range(8, 22)]

    return render_template('horarios.html',
                           bloques=bloques,
                           carreras=carreras,
                           aulas=aulas,
                           profesores=profesores,
                           dias_semana=DIAS_SEMANA,
                           modalidades=MODALIDADES,
                           horas_lista=horas_lista,
                           carrera_id=carrera_id,
                           anio=anio,
                           cuatrimestre=cuatrimestre,
                           espacio_id=espacio_id,
                           profesor_id=profesor_id,
                           modalidad=modalidad,
                           solo_conflictos=solo_conflictos,
                           ids_conflictos=ids_conflictos,
                           mapa_conflictos=mapa_conflictos)


@main_bp.route('/profesores')
@login_required
def profesores():
    lista_profesores = Profesor.query.order_by(Profesor.nombre_completo).all()
    return render_template('profesores.html', profesores=lista_profesores)


@main_bp.route('/profesores/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_profesor():
    if not current_user.is_gestor:
        flash('No tienes permisos para dar de alta profesores.', 'danger')
        return redirect(url_for('main.profesores'))

    if request.method == 'POST':
        nombre_completo = request.form.get('nombre_completo', '').strip()
        categoria_habitual = request.form.get('categoria_habitual', 'PAD')
        email = request.form.get('email', '').strip()

        if not nombre_completo:
            flash('Por favor ingrese el nombre del profesor/a.', 'warning')
            return render_template('profesor_form.html', profesor=None)

        profesor = Profesor(
            nombre_completo=nombre_completo,
            categoria_habitual=categoria_habitual,
            email=email
        )
        db.session.add(profesor)
        db.session.commit()

        flash(f'Profesor/a "{nombre_completo}" registrado/a correctamente.', 'success')
        return redirect(url_for('main.profesores'))

    return render_template('profesor_form.html', profesor=None)


@main_bp.route('/profesores/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_profesor(id):
    if not current_user.is_gestor:
        flash('No tienes permisos para editar profesores.', 'danger')
        return redirect(url_for('main.profesores'))

    profesor = db.session.get(Profesor, id)
    if not profesor:
        flash('Profesor no encontrado.', 'danger')
        return redirect(url_for('main.profesores'))

    if request.method == 'POST':
        profesor.nombre_completo = request.form.get('nombre_completo', '').strip()
        profesor.categoria_habitual = request.form.get('categoria_habitual', 'PAD')
        profesor.email = request.form.get('email', '').strip()

        db.session.commit()
        flash(f'Profesor/a "{profesor.nombre_completo}" actualizado/a correctamente.', 'success')
        return redirect(url_for('main.profesores'))

    return render_template('profesor_form.html', profesor=profesor)


@main_bp.route('/profesores/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_profesor(id):
    if not current_user.is_admin:
        flash('Solo los administradores pueden dar de baja profesores.', 'danger')
        return redirect(url_for('main.profesores'))

    profesor = db.session.get(Profesor, id)
    if profesor:
        nombre = profesor.nombre_completo
        db.session.delete(profesor)
        db.session.commit()
        flash(f'Profesor/a "{nombre}" dado/a de baja correctamente.', 'info')
    return redirect(url_for('main.profesores'))


@main_bp.route('/materias')
@login_required
def materias():
    carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').all()
    carrera_id = request.args.get('carrera_id', type=int)
    cuatrimestre = request.args.get('cuatrimestre', type=int)
    
    query = Asignatura.query.filter_by(es_externa=False)
    if carrera_id:
        query = query.filter_by(carrera_id=carrera_id)
    if cuatrimestre:
        query = query.filter_by(cuatrimestre=cuatrimestre)

    asignaturas = query.order_by(Asignatura.carrera_id, Asignatura.anio_cursada, Asignatura.cuatrimestre).all()

    return render_template('materias.html', asignaturas=asignaturas, carreras=carreras, carrera_id=carrera_id, cuatrimestre=cuatrimestre)


@main_bp.route('/materias/nueva', methods=['GET', 'POST'])
@login_required
def nueva_materia():
    if not current_user.is_gestor:
        flash('No tienes permisos para agregar materias.', 'danger')
        return redirect(url_for('main.materias'))

    carreras = Carrera.query.all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        carrera_id = request.form.get('carrera_id', type=int)
        anio_cursada = request.form.get('anio_cursada', type=int)
        cuatrimestre = request.form.get('cuatrimestre', type=int)
        codigo = request.form.get('codigo', '').strip()
        nombre = request.form.get('nombre', '').strip()
        carga_horaria = request.form.get('carga_horaria_semanal', type=int)
        profesor_pad_id = request.form.get('profesor_pad_id', type=int) or None
        profesores_ayp_ids = request.form.getlist('profesores_ayp_ids', type=int)
        es_externa = bool(request.form.get('es_externa'))

        if not carrera_id or not nombre or not carga_horaria:
            flash('Por favor complete los campos obligatorios.', 'warning')
            return render_template('materia_form.html', carreras=carreras, profesores=profesores, materia=None)

        pad_obj = db.session.get(Profesor, profesor_pad_id) if profesor_pad_id else None
        prof_cargo_txt = pad_obj.nombre_completo if pad_obj else ""

        materia = Asignatura(
            carrera_id=carrera_id,
            anio_cursada=anio_cursada,
            cuatrimestre=cuatrimestre,
            codigo=codigo,
            nombre=nombre,
            carga_horaria_semanal=carga_horaria,
            profesor_pad_id=profesor_pad_id,
            profesor_cargo=prof_cargo_txt,
            es_externa=es_externa
        )

        if profesores_ayp_ids:
            ayp_objs = Profesor.query.filter(Profesor.id.in_(profesores_ayp_ids)).all()
            materia.profesores_ayp = ayp_objs

        db.session.add(materia)
        db.session.commit()

        flash(f'Asignatura "{nombre}" creada con éxito.', 'success')
        return redirect(url_for('main.materias'))

    return render_template('materia_form.html', carreras=carreras, profesores=profesores, materia=None)


@main_bp.route('/materias/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_materia(id):
    if not current_user.is_gestor:
        flash('No tienes permisos para editar materias.', 'danger')
        return redirect(url_for('main.materias'))

    materia = db.session.get(Asignatura, id)
    if not materia:
        flash('Materia no encontrada.', 'danger')
        return redirect(url_for('main.materias'))

    carreras = Carrera.query.all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        materia.carrera_id = request.form.get('carrera_id', type=int)
        materia.anio_cursada = request.form.get('anio_cursada', type=int)
        materia.cuatrimestre = request.form.get('cuatrimestre', type=int)
        materia.codigo = request.form.get('codigo', '').strip()
        materia.nombre = request.form.get('nombre', '').strip()
        materia.carga_horaria_semanal = request.form.get('carga_horaria_semanal', type=int)
        
        profesor_pad_id = request.form.get('profesor_pad_id', type=int) or None
        profesores_ayp_ids = request.form.getlist('profesores_ayp_ids', type=int)
        
        materia.profesor_pad_id = profesor_pad_id
        if profesor_pad_id:
            pad_obj = db.session.get(Profesor, profesor_pad_id)
            materia.profesor_cargo = pad_obj.nombre_completo if pad_obj else ""

        if profesores_ayp_ids:
            ayp_objs = Profesor.query.filter(Profesor.id.in_(profesores_ayp_ids)).all()
            materia.profesores_ayp = ayp_objs
        else:
            materia.profesores_ayp = []

        materia.es_externa = bool(request.form.get('es_externa'))

        db.session.commit()
        flash(f'Asignatura "{materia.nombre}" actualizada correctamente (PAD asignado + {len(materia.profesores_ayp)} AYPs).', 'success')
        return redirect(url_for('main.materias'))

    return render_template('materia_form.html', carreras=carreras, profesores=profesores, materia=materia)


@main_bp.route('/materias/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_materia(id):
    if not current_user.is_admin:
        flash('Solo los administradores pueden eliminar materias.', 'danger')
        return redirect(url_for('main.materias'))

    materia = db.session.get(Asignatura, id)
    if materia:
        nombre = materia.nombre
        db.session.delete(materia)
        db.session.commit()
        flash(f'La asignatura "{nombre}" y sus bloques horarios han sido eliminados.', 'info')
    return redirect(url_for('main.materias'))


@main_bp.route('/bloques/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_bloque():
    if not current_user.is_gestor:
        flash('No tienes permisos para crear bloques horarios.', 'danger')
        return redirect(url_for('main.horarios'))

    asignatura_id = request.args.get('asignatura_id', type=int)
    asignaturas = Asignatura.query.all()
    aulas = EspacioFisico.query.filter_by(activa=True).all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        asig_id = request.form.get('asignatura_id', type=int)
        espacio_id = request.form.get('espacio_fisico_id', type=int) or None
        profesor_id = request.form.get('profesor_id', type=int) or None
        rol_docente = request.form.get('rol_docente', 'PAD')
        dia_semana = request.form.get('dia_semana', type=int)
        h_ini_str = request.form.get('hora_inicio')
        h_fin_str = request.form.get('hora_fin')
        tipo = request.form.get('tipo')
        modalidad = request.form.get('modalidad')
        observaciones = request.form.get('observaciones', '').strip()

        if not asig_id or dia_semana is None or not h_ini_str or not h_fin_str:
            flash('Por favor complete los datos del horario.', 'warning')
            return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=None, asignatura_id=asignatura_id)

        try:
            h_ini = datetime.strptime(h_ini_str, '%H:%M').time()
            h_fin = datetime.strptime(h_fin_str, '%H:%M').time()
        except ValueError:
            flash('Formato de hora inválido. Use HH:MM', 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=None, asignatura_id=asignatura_id)

        m_ini = h_ini.hour * 60 + h_ini.minute
        m_fin = h_fin.hour * 60 + h_fin.minute
        duracion = (m_fin - m_ini) / 60.0 if m_fin > m_ini else 0

        es_sincronico = (modalidad not in ['Asincrónico (PEDCO)'])
        asig = db.session.get(Asignatura, asig_id)
        es_bloqueo = (modalidad == 'Bloqueo Aula' or (asig and asig.es_externa))

        valido, errores, advertencias = validar_bloque_nuevo(asig_id, dia_semana, h_ini, h_fin, modalidad, espacio_id, profesor_id)

        if not valido:
            for err in errores:
                flash(err, 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=None, asignatura_id=asignatura_id)

        for adv in advertencias:
            flash(adv, 'warning')

        bloque = BloqueHorario(
            asignatura_id=asig_id,
            espacio_fisico_id=espacio_id if modalidad in ['Presencial', 'Híbrido', 'Bloqueo Aula'] else None,
            profesor_id=profesor_id,
            rol_docente=rol_docente,
            dia_semana=dia_semana,
            hora_inicio=h_ini,
            hora_fin=h_fin,
            duracion_horas=duracion,
            tipo=tipo,
            modalidad=modalidad,
            es_sincronico=es_sincronico,
            es_bloqueo_externo=es_bloqueo,
            observaciones=observaciones
        )
        db.session.add(bloque)
        db.session.commit()

        flash(f'Reserva de clase guardada correctamente (Rol Docente: {rol_docente}).', 'success')
        return redirect(url_for('main.horarios'))

    return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=None, asignatura_id=asignatura_id)


# EDICIÓN / REUBICACIÓN DE CLASE (PERMITIDO A GESTORES O AL PROFESOR DE LA MATERIA SI NO HAY CONFLICTO)
@main_bp.route('/bloques/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_bloque(id):
    bloque = db.session.get(BloqueHorario, id)
    if not bloque:
        flash('Bloque de horario no encontrado.', 'danger')
        return redirect(url_for('main.horarios'))

    if not current_user.puede_editar_bloque(bloque):
        flash('No tienes permisos para modificar esta clase. Solo el profesor/a asignado o los gestores pueden reubicarla.', 'danger')
        return redirect(url_for('main.horarios'))

    asignaturas = Asignatura.query.all()
    aulas = EspacioFisico.query.filter_by(activa=True).all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        asig_id = request.form.get('asignatura_id', type=int)
        espacio_id = request.form.get('espacio_fisico_id', type=int) or None
        profesor_id = request.form.get('profesor_id', type=int) or None
        rol_docente = request.form.get('rol_docente', 'PAD')
        dia_semana = request.form.get('dia_semana', type=int)
        h_ini_str = request.form.get('hora_inicio')
        h_fin_str = request.form.get('hora_fin')
        tipo = request.form.get('tipo')
        modalidad = request.form.get('modalidad')
        observaciones = request.form.get('observaciones', '').strip()

        if not asig_id or dia_semana is None or not h_ini_str or not h_fin_str:
            flash('Por favor complete los datos requeridos.', 'warning')
            return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=bloque, asignatura_id=bloque.asignatura_id)

        try:
            h_ini = datetime.strptime(h_ini_str, '%H:%M').time()
            h_fin = datetime.strptime(h_fin_str, '%H:%M').time()
        except ValueError:
            flash('Formato de hora inválido. Use HH:MM', 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=bloque, asignatura_id=bloque.asignatura_id)

        m_ini = h_ini.hour * 60 + h_ini.minute
        m_fin = h_fin.hour * 60 + h_fin.minute
        duracion = (m_fin - m_ini) / 60.0 if m_fin > m_ini else 0

        # Validar colisiones (excluyendo este bloque_id de la comparación)
        valido, errores, advertencias = validar_bloque_nuevo(asig_id, dia_semana, h_ini, h_fin, modalidad, espacio_id, profesor_id, bloque_id_actual=bloque.id)

        if not valido:
            for err in errores:
                flash(err, 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=bloque, asignatura_id=bloque.asignatura_id)

        for adv in advertencias:
            flash(adv, 'warning')

        bloque.asignatura_id = asig_id
        bloque.espacio_fisico_id = espacio_id if modalidad in ['Presencial', 'Híbrido', 'Bloqueo Aula'] else None
        bloque.profesor_id = profesor_id
        bloque.rol_docente = rol_docente
        bloque.dia_semana = dia_semana
        bloque.hora_inicio = h_ini
        bloque.hora_fin = h_fin
        bloque.duracion_horas = duracion
        bloque.tipo = tipo
        bloque.modalidad = modalidad
        bloque.es_sincronico = (modalidad not in ['Asincrónico (PEDCO)'])
        bloque.observaciones = observaciones

        db.session.commit()

        flash(f'La clase de "{bloque.asignatura.nombre}" fue reubicada con éxito ({bloque.dia_nombre} {h_ini_str}-{h_fin_str}).', 'success')
        return redirect(url_for('main.horarios'))

    return render_template('bloque_form.html', asignaturas=asignaturas, aulas=aulas, profesores=profesores, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, dias_semana=DIAS_SEMANA, bloque=bloque, asignatura_id=bloque.asignatura_id)


@main_bp.route('/bloques/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_bloque(id):
    bloque = db.session.get(BloqueHorario, id)
    if not bloque:
        flash('Bloque no encontrado.', 'danger')
        return redirect(url_for('main.horarios'))

    if not current_user.puede_editar_bloque(bloque):
        flash('No tienes permisos para eliminar esta clase.', 'danger')
        return redirect(url_for('main.horarios'))

    db.session.delete(bloque)
    db.session.commit()
    flash('El bloque horario fue eliminado.', 'info')
    return redirect(url_for('main.horarios'))


# GESTIÓN DE USUARIOS (ALTA, EDICIÓN Y BAJA POR ADMINISTRADOR)
@main_bp.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin:
        flash('Acceso restringido a administradores.', 'danger')
        return redirect(url_for('main.dashboard'))

    lista_usuarios = User.query.order_by(User.id).all()
    return render_template('usuarios.html', usuarios=lista_usuarios)


@main_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    if not current_user.is_admin:
        flash('Solo los administradores pueden dar de alta usuarios.', 'danger')
        return redirect(url_for('main.usuarios'))

    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        nombre_completo = request.form.get('nombre_completo', '').strip()
        role = request.form.get('role', 'alumno')
        profesor_id = request.form.get('profesor_id', type=int) or None
        password = request.form.get('password', '').strip()

        if not username or not email or not nombre_completo or not password:
            flash('Por favor complete los campos obligatorios.', 'warning')
            return render_template('usuario_form.html', profesores=profesores, usuario=None)

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está registrado.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=None)

        usuario = User(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            role=role,
            profesor_id=profesor_id
        )
        usuario.set_password(password)

        db.session.add(usuario)
        db.session.commit()

        flash(f'Usuario "{username}" creado con éxito con rol [{role}].', 'success')
        return redirect(url_for('main.usuarios'))

    return render_template('usuario_form.html', profesores=profesores, usuario=None)


@main_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if not current_user.is_admin:
        flash('Solo los administradores pueden editar usuarios.', 'danger')
        return redirect(url_for('main.usuarios'))

    usuario = db.session.get(User, id)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('main.usuarios'))

    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        usuario.username = request.form.get('username', '').strip()
        usuario.email = request.form.get('email', '').strip()
        usuario.nombre_completo = request.form.get('nombre_completo', '').strip()
        usuario.role = request.form.get('role', 'alumno')
        usuario.profesor_id = request.form.get('profesor_id', type=int) or None
        
        password = request.form.get('password', '').strip()
        if password:
            usuario.set_password(password)

        db.session.commit()
        flash(f'Usuario "{usuario.username}" actualizado con éxito.', 'success')
        return redirect(url_for('main.usuarios'))

    return render_template('usuario_form.html', profesores=profesores, usuario=usuario)


@main_bp.route('/usuarios/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_usuario(id):
    if not current_user.is_admin:
        flash('Solo los administradores pueden eliminar usuarios.', 'danger')
        return redirect(url_for('main.usuarios'))

    if id == current_user.id:
        flash('No puede eliminar su propia cuenta de administrador.', 'warning')
        return redirect(url_for('main.usuarios'))

    usuario = db.session.get(User, id)
    if usuario:
        username = usuario.username
        db.session.delete(usuario)
        db.session.commit()
        flash(f'El usuario "{username}" fue eliminado.', 'info')
    return redirect(url_for('main.usuarios'))


# VISTA PÚBLICA DE AULAS (ACCESO LIBRE)
@main_bp.route('/aulas')
def aulas():
    aulas_lista = EspacioFisico.query.all()
    return render_template('aulas.html', aulas=aulas_lista)


# VISTA PÚBLICA DE BLOQUEOS DE AULA
@main_bp.route('/bloqueos_externos')
def bloqueos_externos():
    bloqueos = BloqueHorario.query.filter((BloqueHorario.es_bloqueo_externo == True) | (BloqueHorario.modalidad == 'Bloqueo Aula')).all()
    aulas_lista = EspacioFisico.query.filter_by(activa=True).all()
    materias_externas = Asignatura.query.filter_by(es_externa=True).all()
    return render_template('bloqueos_externos.html', bloqueos=bloqueos, aulas=aulas_lista, materias_externas=materias_externas, dias_semana=DIAS_SEMANA)


@main_bp.route('/api/validar_bloque', methods=['POST'])
def api_validar_bloque():
    data = request.json or {}
    asig_id = data.get('asignatura_id')
    dia_semana = data.get('dia_semana')
    h_ini_str = data.get('hora_inicio')
    h_fin_str = data.get('hora_fin')
    modalidad = data.get('modalidad')
    espacio_id = data.get('espacio_fisico_id')
    profesor_id = data.get('profesor_id')
    bloque_id = data.get('bloque_id')

    if not asig_id or dia_semana is None or not h_ini_str or not h_fin_str:
        return jsonify({'valido': False, 'errores': ['Faltan datos requeridos'], 'advertencias': []})

    try:
        h_ini = datetime.strptime(h_ini_str, '%H:%M').time()
        h_fin = datetime.strptime(h_fin_str, '%H:%M').time()
    except ValueError:
        return jsonify({'valido': False, 'errores': ['Formato de hora inválido'], 'advertencias': []})

    valido, errores, advertencias = validar_bloque_nuevo(asig_id, int(dia_semana), h_ini, h_fin, modalidad, espacio_id, profesor_id, bloque_id_actual=bloque_id)
    return jsonify({'valido': valido, 'errores': errores, 'advertencias': advertencias})


@main_bp.route('/api/auditoria')
def api_auditoria():
    reporte = auditar_sistema_completo()
    return jsonify(reporte)
