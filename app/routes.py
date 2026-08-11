from datetime import datetime, time, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import User, Carrera, Asignatura, EspacioFisico, BloqueHorario, Profesor, ConfiguracionSistema, DIAS_SEMANA, MODALIDADES, TIPOS_CLASE
from app.rules import auditar_sistema_completo, validar_bloque_nuevo, calcular_minimo_sincronico, obtener_ids_bloques_en_conflicto, obtener_mapa_explicacion_conflictos

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_alumno:
            return redirect(url_for('main.horarios'))
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.horarios'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_alumno:
        flash('No tienes permisos para acceder al dashboard.', 'danger')
        return redirect(url_for('main.horarios'))
    reporte = auditar_sistema_completo()
    total_carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').count()
    total_materias = Asignatura.query.filter_by(es_externa=False).count()
    total_aulas = EspacioFisico.query.count()
    total_bloques = BloqueHorario.query.count()

    carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').all()
    aulas = EspacioFisico.query.all()
    profesores = Profesor.query.all()
    config = ConfiguracionSistema.get_config()

    return render_template('dashboard.html',
                           reporte=reporte,
                           total_carreras=total_carreras,
                           total_materias=total_materias,
                           total_aulas=total_aulas,
                           total_bloques=total_bloques,
                           carreras=carreras,
                           aulas=aulas,
                           profesores=profesores,
                           config=config)


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
        BloqueHorario.espacio_fisico_id.is_(None),
        BloqueHorario.espacio_fisico_id.asc()
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


# API DRAG & DROP PARA REUBICAR CLASES INTERACTIVAMENTE
@main_bp.route('/api/bloque/<int:id>/mover', methods=['POST'])
@login_required
def api_mover_bloque(id):
    if ConfiguracionSistema.esta_congelado():
        return jsonify({'success': False, 'error': 'El sistema está congelado. No se permiten cambios.'}), 403
    
    bloque = db.session.get(BloqueHorario, id)
    if not bloque:
        return jsonify({'success': False, 'error': 'Bloque de clase no encontrado.'}), 404

    if not current_user.puede_editar_bloque(bloque):
        return jsonify({'success': False, 'error': 'No tienes permisos para reubicar esta clase.'}), 403

    data = request.get_json() or {}
    nuevo_dia = data.get('dia_semana')
    nueva_hora_ini_str = data.get('hora_inicio')

    if nuevo_dia is None or not nueva_hora_ini_str:
        return jsonify({'success': False, 'error': 'Datos de ubicación incompletos.'}), 400

    try:
        nuevo_dia = int(nuevo_dia)
        h_parts = [int(p) for p in nueva_hora_ini_str.split(':')]
        if not (0 <= h_parts[0] <= 23 and 0 <= h_parts[1] <= 59):
            return jsonify({'success': False, 'error': 'Hora de inicio no válida.'}), 400
        nueva_hora_ini = time(h_parts[0], h_parts[1])
        
        duracion_min = int(bloque.duracion_horas * 60)
        fin_min = (h_parts[0] * 60 + h_parts[1]) + duracion_min
        fin_h = fin_min // 60
        fin_m = fin_min % 60
        if fin_h >= 24 or fin_m >= 60:
            return jsonify({'success': False, 'error': 'La clase excede el horario permitido del día.'}), 400
        nueva_hora_fin = time(fin_h, fin_m)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Horario no válido: {str(e)}'}), 400

    valido, errores, adv = validar_bloque_nuevo(
        asignatura_id=bloque.asignatura_id,
        dia_semana=nuevo_dia,
        hora_inicio=nueva_hora_ini,
        hora_fin=nueva_hora_fin,
        modalidad=bloque.modalidad,
        espacio_fisico_id=bloque.espacio_fisico_id,
        profesor_id=bloque.profesor_id,
        bloque_id_actual=bloque.id
    )

    if not valido:
        return jsonify({
            'success': False,
            'error': errores[0] if errores else 'Conflicto detectado al reubicar la clase.'
        }), 400

    bloque.dia_semana = nuevo_dia
    bloque.hora_inicio = nueva_hora_ini
    bloque.hora_fin = nueva_hora_fin
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"¡Clase '{bloque.asignatura.nombre}' movida al {bloque.dia_nombre} de {nueva_hora_ini.strftime('%H:%M')} a {nueva_hora_fin.strftime('%H:%M')}!"
    })


@main_bp.route('/profesores')
@login_required
def profesores():
    if current_user.is_alumno:
        flash('No tienes permisos para acceder a profesores.', 'danger')
        return redirect(url_for('main.horarios'))
    lista_profesores = Profesor.query.order_by(Profesor.nombre_completo).all()
    return render_template('profesores.html', profesores=lista_profesores)


@main_bp.route('/profesores/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_profesor():
    if not current_user.is_gestor:
        flash('No tienes permisos para dar de alta profesores.', 'danger')
        return redirect(url_for('main.profesores'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.profesores'))

    if request.method == 'POST':
        nombre_completo = request.form.get('nombre_completo', '').strip()
        categoria_habitual = request.form.get('categoria_habitual', 'PAD')
        email = request.form.get('email', '').strip()

        if not nombre_completo:
            flash('Por favor complete el nombre completo del profesor.', 'warning')
            return render_template('profesor_form.html', profesor=None)

        prof = Profesor(nombre_completo=nombre_completo, categoria_habitual=categoria_habitual, email=email)
        db.session.add(prof)
        db.session.commit()

        flash(f'Profesor/a "{nombre_completo}" dado de alta con éxito.', 'success')
        return redirect(url_for('main.profesores'))

    return render_template('profesor_form.html', profesor=None)


@main_bp.route('/profesores/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_profesor(id):
    if not current_user.is_gestor:
        flash('No tienes permisos para editar profesores.', 'danger')
        return redirect(url_for('main.profesores'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.profesores'))

    prof = db.session.get(Profesor, id)
    if not prof:
        flash('Profesor no encontrado.', 'danger')
        return redirect(url_for('main.profesores'))

    if request.method == 'POST':
        prof.nombre_completo = request.form.get('nombre_completo', '').strip()
        prof.categoria_habitual = request.form.get('categoria_habitual', 'PAD')
        prof.email = request.form.get('email', '').strip()

        db.session.commit()
        flash(f'Profesor/a "{prof.nombre_completo}" actualizado con éxito.', 'success')
        return redirect(url_for('main.profesores'))

    return render_template('profesor_form.html', profesor=prof)


@main_bp.route('/profesores/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_profesor(id):
    if not current_user.is_gestor:
        flash('No tienes permisos para eliminar profesores.', 'danger')
        return redirect(url_for('main.profesores'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.profesores'))

    prof = db.session.get(Profesor, id)
    if prof:
        db.session.delete(prof)
        db.session.commit()
        flash(f'Profesor/a "{prof.nombre_completo}" eliminado con éxito.', 'success')

    return redirect(url_for('main.profesores'))


@main_bp.route('/materias')
@login_required
def materias():
    if current_user.is_alumno:
        flash('No tienes permisos para acceder a materias.', 'danger')
        return redirect(url_for('main.horarios'))
    carrera_id = request.args.get('carrera_id', type=int)
    cuatrimestre = request.args.get('cuatrimestre', type=int)
    solo_externas = request.args.get('externas', type=int)

    query = Asignatura.query
    if solo_externas:
        query = query.filter_by(es_externa=True)
    else:
        query = query.filter_by(es_externa=False)

    if carrera_id:
        query = query.filter_by(carrera_id=carrera_id)
    if cuatrimestre:
        query = query.filter_by(cuatrimestre=cuatrimestre)

    lista_materias = query.order_by(Asignatura.carrera_id, Asignatura.anio_cursada, Asignatura.cuatrimestre).all()
    carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').all()

    reporte = auditar_sistema_completo()

    return render_template('materias.html',
                           materias=lista_materias,
                           asignaturas=lista_materias,
                           carreras=carreras,
                           carrera_id=carrera_id,
                           cuatrimestre=cuatrimestre,
                           solo_externas=solo_externas,
                           reporte=reporte)


@main_bp.route('/materias/nueva', methods=['GET', 'POST'])
@login_required
def nueva_materia():
    if not current_user.is_gestor:
        flash('No tienes permisos para crear materias.', 'danger')
        return redirect(url_for('main.materias'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.materias'))

    carreras = Carrera.query.all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        carrera_id = request.form.get('carrera_id', type=int)
        codigo = request.form.get('codigo', '').strip()
        nombre = request.form.get('nombre', '').strip()
        anio_cursada = request.form.get('anio_cursada', type=int, default=1)
        cuatrimestre = request.form.get('cuatrimestre', type=int, default=1)
        carga_horaria_semanal = request.form.get('carga_horaria_semanal', type=int, default=8)
        profesor_pad_id = request.form.get('profesor_pad_id', type=int) or None
        ayps_selected = request.form.getlist('profesores_ayp_ids', type=int)
        es_externa = request.form.get('es_externa') == '1'

        if not carrera_id or not codigo or not nombre:
            flash('Por favor complete los campos requeridos.', 'warning')
            return render_template('materia_form.html', carreras=carreras, profesores=profesores, materia=None)

        asig = Asignatura(
            carrera_id=carrera_id,
            codigo=codigo,
            nombre=nombre,
            anio_cursada=anio_cursada,
            cuatrimestre=cuatrimestre,
            carga_horaria_semanal=carga_horaria_semanal,
            profesor_pad_id=profesor_pad_id,
            es_externa=es_externa
        )

        if ayps_selected:
            asig.profesores_ayp = Profesor.query.filter(Profesor.id.in_(ayps_selected)).all()

        db.session.add(asig)
        db.session.commit()

        flash(f'Materia "{nombre}" creada con éxito.', 'success')
        return redirect(url_for('main.materias'))

    return render_template('materia_form.html', carreras=carreras, profesores=profesores, materia=None)


@main_bp.route('/materias/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_materia(id):
    if not current_user.is_gestor:
        flash('No tienes permisos para editar materias.', 'danger')
        return redirect(url_for('main.materias'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.materias'))

    asig = db.session.get(Asignatura, id)
    if not asig:
        flash('Materia no encontrada.', 'danger')
        return redirect(url_for('main.materias'))

    carreras = Carrera.query.all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        asig.carrera_id = request.form.get('carrera_id', type=int)
        asig.codigo = request.form.get('codigo', '').strip()
        asig.nombre = request.form.get('nombre', '').strip()
        asig.anio_cursada = request.form.get('anio_cursada', type=int, default=1)
        asig.cuatrimestre = request.form.get('cuatrimestre', type=int, default=1)
        asig.carga_horaria_semanal = request.form.get('carga_horaria_semanal', type=int, default=4)
        asig.profesor_pad_id = request.form.get('profesor_pad_id', type=int) or None
        asig.es_externa = request.form.get('es_externa') == '1'

        ayps_selected = request.form.getlist('profesores_ayp_ids', type=int)
        asig.profesores_ayp = Profesor.query.filter(Profesor.id.in_(ayps_selected)).all() if ayps_selected else []

        db.session.commit()
        flash(f'Materia "{asig.nombre}" actualizada con éxito.', 'success')
        return redirect(url_for('main.materias'))

    return render_template('materia_form.html', carreras=carreras, profesores=profesores, materia=asig)


@main_bp.route('/materias/<int:id>/clases')
@login_required
def materia_clases(id):
    asig = db.session.get(Asignatura, id)
    if not asig:
        flash('Materia no encontrada.', 'danger')
        return redirect(url_for('main.materias'))

    bloques = BloqueHorario.query.filter_by(asignatura_id=asig.id).order_by(BloqueHorario.dia_semana, BloqueHorario.hora_inicio).all()
    return render_template('materia_clases.html', materia=asig, bloques=bloques)


@main_bp.route('/bloques/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_bloque():
    if not current_user.is_gestor:
        flash('No tienes permisos para programar nuevas clases.', 'danger')
        return redirect(url_for('main.horarios'))

    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.horarios'))

    asignaturas = Asignatura.query.order_by(Asignatura.nombre).all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()
    aulas = EspacioFisico.query.order_by(EspacioFisico.nombre).all()

    if request.method == 'POST':
        asignatura_id = request.form.get('asignatura_id', type=int)
        profesor_id = request.form.get('profesor_id', type=int) or None
        rol_docente = request.form.get('rol_docente', 'PAD')
        dia_semana = request.form.get('dia_semana', type=int)
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fin_str = request.form.get('hora_fin')
        tipo = request.form.get('tipo', 'Teoría')
        modalidad = request.form.get('modalidad', 'Presencial')
        espacio_fisico_id = request.form.get('espacio_fisico_id', type=int) or None
        observaciones = request.form.get('observaciones', '').strip()

        if not asignatura_id or dia_semana is None or not hora_inicio_str or not hora_fin_str:
            flash('Por favor complete todos los campos obligatorios del horario.', 'warning')
            return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=None, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)

        try:
            h_ini = time.fromisoformat(hora_inicio_str)
            h_fin = time.fromisoformat(hora_fin_str)
        except (ValueError, TypeError):
            flash('Formato de hora no válido. Use HH:MM.', 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=None, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)

        valido, errores, advertencias = validar_bloque_nuevo(
            asignatura_id, dia_semana, h_ini, h_fin, modalidad, espacio_fisico_id, profesor_id
        )

        if not valido:
            for err in errores:
                flash(err, 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=None, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)

        for adv in advertencias:
            flash(adv, 'warning')

        es_sincronico = (modalidad != 'Asincrónico (PEDCO)')
        es_bloqueo_externo = (modalidad == 'Bloqueo Aula')
        duracion_horas = (h_fin.hour * 60 + h_fin.minute - (h_ini.hour * 60 + h_ini.minute)) / 60.0

        bloque = BloqueHorario(
            asignatura_id=asignatura_id,
            espacio_fisico_id=espacio_fisico_id if modalidad in ['Presencial', 'Híbrido', 'Bloqueo Aula'] else None,
            profesor_id=profesor_id,
            rol_docente=rol_docente,
            dia_semana=dia_semana,
            hora_inicio=h_ini,
            hora_fin=h_fin,
            duracion_horas=duracion_horas,
            tipo=tipo,
            modalidad=modalidad,
            es_sincronico=es_sincronico,
            es_bloqueo_externo=es_bloqueo_externo,
            observaciones=observaciones
        )

        db.session.add(bloque)
        db.session.commit()

        flash('Clase / Reserva programada con éxito.', 'success')
        return redirect(url_for('main.horarios'))

    return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=None, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)


@main_bp.route('/bloques/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_bloque(id):
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.horarios'))
    
    bloque = db.session.get(BloqueHorario, id)
    if not bloque:
        flash('Bloque de clase no encontrado.', 'danger')
        return redirect(url_for('main.horarios'))

    if not current_user.puede_editar_bloque(bloque):
        flash('No tienes permisos para modificar este bloque de clase.', 'danger')
        return redirect(url_for('main.horarios'))

    asignaturas = Asignatura.query.order_by(Asignatura.nombre).all()
    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()
    aulas = EspacioFisico.query.order_by(EspacioFisico.nombre).all()

    if request.method == 'POST':
        asignatura_id = request.form.get('asignatura_id', type=int)
        profesor_id = request.form.get('profesor_id', type=int) or None
        rol_docente = request.form.get('rol_docente', 'PAD')
        dia_semana = request.form.get('dia_semana', type=int)
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fin_str = request.form.get('hora_fin')
        tipo = request.form.get('tipo', 'Teoría')
        modalidad = request.form.get('modalidad', 'Presencial')
        espacio_fisico_id = request.form.get('espacio_fisico_id', type=int) or None
        observaciones = request.form.get('observaciones', '').strip()

        try:
            h_ini = time.fromisoformat(hora_inicio_str)
            h_fin = time.fromisoformat(hora_fin_str)
        except (ValueError, TypeError):
            flash('Formato de hora no válido. Use HH:MM.', 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=bloque, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)

        valido, errores, advertencias = validar_bloque_nuevo(
            asignatura_id, dia_semana, h_ini, h_fin, modalidad, espacio_fisico_id, profesor_id, bloque_id_actual=bloque.id
        )

        if not valido:
            for err in errores:
                flash(err, 'danger')
            return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=bloque, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)

        for adv in advertencias:
            flash(adv, 'warning')

        bloque.asignatura_id = asignatura_id
        bloque.profesor_id = profesor_id
        bloque.rol_docente = rol_docente
        bloque.dia_semana = dia_semana
        bloque.hora_inicio = h_ini
        bloque.hora_fin = h_fin
        bloque.duracion_horas = (h_fin.hour * 60 + h_fin.minute - (h_ini.hour * 60 + h_ini.minute)) / 60.0
        bloque.tipo = tipo
        bloque.modalidad = modalidad
        bloque.espacio_fisico_id = espacio_fisico_id if modalidad in ['Presencial', 'Híbrido', 'Bloqueo Aula'] else None
        bloque.es_sincronico = (modalidad != 'Asincrónico (PEDCO)')
        bloque.es_bloqueo_externo = (modalidad == 'Bloqueo Aula')
        bloque.observaciones = observaciones

        db.session.commit()
        flash('Clase / Reserva reubicada con éxito.', 'success')
        return redirect(url_for('main.horarios'))

    return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=bloque, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE)


@main_bp.route('/bloques/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_bloque(id):
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.horarios'))
    
    bloque = db.session.get(BloqueHorario, id)
    if bloque and current_user.puede_editar_bloque(bloque):
        db.session.delete(bloque)
        db.session.commit()
        flash('Clase eliminada del cronograma.', 'info')
    return redirect(url_for('main.horarios'))


@main_bp.route('/aulas')
def aulas():
    lista_aulas = EspacioFisico.query.order_by(EspacioFisico.nombre).all()
    return render_template('aulas.html', aulas=lista_aulas)


@main_bp.route('/bloqueos_externos')
@login_required
def bloqueos_externos():
    if current_user.is_alumno:
        flash('No tienes permisos para acceder a bloqueos externos.', 'danger')
        return redirect(url_for('main.horarios'))
    bloqueos = BloqueHorario.query.filter(
        (BloqueHorario.es_bloqueo_externo == True) | (BloqueHorario.asignatura.has(es_externa=True))
    ).order_by(BloqueHorario.dia_semana, BloqueHorario.hora_inicio).all()
    
    return render_template('bloqueos_externos.html', bloqueos=bloqueos)


@main_bp.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin:
        flash('Solo los administradores pueden gestionar usuarios.', 'danger')
        return redirect(url_for('main.dashboard'))

    lista_usuarios = User.query.order_by(User.username).all()
    return render_template('usuarios.html', usuarios=lista_usuarios)


@main_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    if not current_user.is_admin:
        flash('Solo los administradores pueden crear usuarios.', 'danger')
        return redirect(url_for('main.usuarios'))

    profesores = Profesor.query.order_by(Profesor.nombre_completo).all()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        nombre_completo = request.form.get('nombre_completo', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'alumno')
        profesor_id = request.form.get('profesor_id', type=int) or None

        if not username or not email or not password or not nombre_completo:
            flash('Por favor complete todos los campos obligatorios.', 'warning')
            return render_template('usuario_form.html', profesores=profesores, usuario=None)

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está registrado.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=None)

        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=None)

        usuario = User(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            role=role,
            profesor_id=profesor_id
        )
        usuario.set_password(password)

        try:
            db.session.add(usuario)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Error de integridad: el nombre de usuario o email ya está en uso.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=None)

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
        new_username = request.form.get('username', '').strip()
        new_email = request.form.get('email', '').strip()

        if User.query.filter(User.username == new_username, User.id != usuario.id).first():
            flash('El nombre de usuario ya está en uso por otro usuario.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=usuario)

        if User.query.filter(User.email == new_email, User.id != usuario.id).first():
            flash('El correo electrónico ya está en uso por otro usuario.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=usuario)

        usuario.username = new_username
        usuario.email = new_email
        usuario.nombre_completo = request.form.get('nombre_completo', '').strip()
        usuario.role = request.form.get('role', 'alumno')
        usuario.profesor_id = request.form.get('profesor_id', type=int) or None
        
        password = request.form.get('password', '').strip()
        if password:
            usuario.set_password(password)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Error al actualizar usuario: nombre de usuario o email duplicado.', 'danger')
            return render_template('usuario_form.html', profesores=profesores, usuario=usuario)

        flash(f'Usuario "{usuario.username}" actualizado con éxito.', 'success')
        return redirect(url_for('main.usuarios'))

    return render_template('usuario_form.html', profesores=profesores, usuario=usuario)


@main_bp.route('/usuarios/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_usuario(id):
    if not current_user.is_admin:
        flash('Solo los administradores pueden eliminar usuarios.', 'danger')
        return redirect(url_for('main.usuarios'))

    usuario = db.session.get(User, id)
    if usuario:
        if usuario.id == current_user.id:
            flash('No puedes eliminar tu propia cuenta de usuario en uso.', 'danger')
            return redirect(url_for('main.usuarios'))
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario "{usuario.username}" eliminado con éxito.', 'success')

    return redirect(url_for('main.usuarios'))


@main_bp.route('/sistema/congelar', methods=['POST'])
@login_required
def congelar_sistema():
    if not current_user.is_admin:
        flash('Solo los administradores pueden congelar el sistema.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    config = ConfiguracionSistema.get_config()
    motivo = request.form.get('motivo', '').strip()
    
    config.congelado = True
    config.motivo_congelacion = motivo if motivo else 'Sin motivo especificado'
    config.congelado_por = current_user.id
    config.congelado_fecha = datetime.now(timezone.utc)
    db.session.commit()
    
    flash('Sistema CONGELADO. No se permiten cambios hasta que un administrador lo descongele.', 'warning')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/sistema/descongelar', methods=['POST'])
@login_required
def descongelar_sistema():
    if not current_user.is_admin:
        flash('Solo los administradores pueden descongelar el sistema.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    config = ConfiguracionSistema.get_config()
    config.congelado = False
    config.motivo_congelacion = None
    config.congelado_por = None
    config.congelado_fecha = None
    db.session.commit()
    
    flash('Sistema DESCONGELADO. Ahora se permiten cambios nuevamente.', 'success')
    return redirect(url_for('main.dashboard'))
