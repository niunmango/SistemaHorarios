import json
from datetime import datetime, time, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import User, Carrera, Asignatura, EspacioFisico, BloqueHorario, Profesor, ConfiguracionSistema, DIAS_SEMANA, MODALIDADES, TIPOS_CLASE, Auditoria, SolicitudCambio
from app.rules import auditar_sistema_completo, validar_bloque_nuevo, calcular_minimo_sincronico, obtener_ids_bloques_en_conflicto, obtener_mapa_explicacion_conflictos
from app.audit_helpers import es_solicitar_aprobacion, crear_solicitud_aprobacion

main_bp = Blueprint('main', __name__)

def guardar_auditoria(accion, entidad_tipo=None, entidad_id=None, detalles=None, ip=None):
    """Registra una entrada en la tabla de auditoría."""
    ip_address = ip or request.remote_addr if request else '127.0.0.1'
    audit_entry = Auditoria(
        usuario_id=current_user.id,
        accion=accion,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        detalles=json.dumps(detalles) if detalles else None,
        ip_address=ip_address
    )
    db.session.add(audit_entry)
    db.session.commit()


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_alumno:
            return redirect(url_for('main.horarios'))
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.horarios'))


@main_bp.route('/condiciones-del-servicio')
@main_bp.route('/terminos')
def terminos():
    """Página pública de Condiciones del Servicio (requerida por Google OAuth)."""
    return render_template('terminos.html')


@main_bp.route('/politica-de-privacidad')
@main_bp.route('/privacidad')
def privacidad():
    """Página pública de Política de Privacidad (requerida por Google OAuth)."""
    return render_template('privacidad.html')


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

    # Guardar valores anteriores para auditoría y permitir deshacer (undo)
    dia_semana_anterior = bloque.dia_semana
    hora_inicio_anterior = bloque.hora_inicio.strftime('%H:%M')
    hora_fin_anterior = bloque.hora_fin.strftime('%H:%M')

    bloque.dia_semana = nuevo_dia
    bloque.hora_inicio = nueva_hora_ini
    bloque.hora_fin = nueva_hora_fin
    db.session.commit()
    
    # Logging de auditoria
    guardar_auditoria(
        accion='editar_bloque_api',
        entidad_tipo='bloque',
        entidad_id=bloque.id,
        detalles={
            'bloque_id': bloque.id,
            'nuevo_dia': nuevo_dia,
            'nueva_hora_inicio': str(nueva_hora_ini),
            'nueva_hora_fin': str(nueva_hora_fin),
            'dia_semana_anterior': dia_semana_anterior,
            'hora_inicio_anterior': hora_inicio_anterior,
            'hora_fin_anterior': hora_fin_anterior,
            'metodo': 'api_mover_bloque'
        }
    )

    return jsonify({
        'success': True,
        'message': f"¡Clase '{bloque.asignatura.nombre}' movida al {bloque.dia_nombre} de {nueva_hora_ini.strftime('%H:%M')} a {nueva_hora_fin.strftime('%H:%M')}!"
    })


@main_bp.route('/api/bloque/<int:id>/deshacer', methods=['POST'])
@login_required
def api_deshacer_bloque(id):
    if ConfiguracionSistema.esta_congelado():
        return jsonify({'success': False, 'error': 'El sistema está congelado. No se permiten cambios.'}), 403

    bloque = db.session.get(BloqueHorario, id)
    if not bloque:
        return jsonify({'success': False, 'error': 'Bloque de clase no encontrado.'}), 404

    if not current_user.puede_editar_bloque(bloque):
        return jsonify({'success': False, 'error': 'No tienes permisos para deshacer cambios en esta clase.'}), 403

    # Buscar el registro de auditoría más reciente de modificación para este bloque
    audit_log = Auditoria.query.filter(
        Auditoria.entidad_tipo == 'bloque',
        Auditoria.entidad_id == id,
        Auditoria.accion.in_(['editar_bloque', 'editar_bloque_api'])
    ).order_by(Auditoria.created_at.desc()).first()

    if not audit_log or not audit_log.detalles:
        return jsonify({'success': False, 'error': 'No hay cambios previos registrados para esta clase.'}), 400

    try:
        detalles = json.loads(audit_log.detalles)
    except (json.JSONDecodeError, TypeError):
        return jsonify({'success': False, 'error': 'No se pudo leer los datos previos del cambio.'}), 400

    # Extraer valores previos
    anterior = detalles.get('anterior', {})
    dia_ant = detalles.get('dia_semana_anterior') if 'dia_semana_anterior' in detalles else anterior.get('dia_semana')
    h_ini_ant_str = detalles.get('hora_inicio_anterior') if 'hora_inicio_anterior' in detalles else anterior.get('hora_inicio')
    h_fin_ant_str = detalles.get('hora_fin_anterior') if 'hora_fin_anterior' in detalles else anterior.get('hora_fin')

    if dia_ant is None or not h_ini_ant_str or not h_fin_ant_str:
        return jsonify({'success': False, 'error': 'No hay un estado anterior válido para deshacer.'}), 400

    try:
        h_ini_ant = time.fromisoformat(h_ini_ant_str)
        h_fin_ant = time.fromisoformat(h_fin_ant_str)
        dia_ant = int(dia_ant)
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': f'Horario anterior no válido: {str(e)}'}), 400

    # Campos opcionales si fueron modificados en formulario de edición completa
    espacio_ant_id = anterior.get('espacio_fisico_id', bloque.espacio_fisico_id)
    profesor_ant_id = anterior.get('profesor_id', bloque.profesor_id)
    modalidad_ant = anterior.get('modalidad', bloque.modalidad)
    tipo_ant = anterior.get('tipo', bloque.tipo)
    rol_ant = anterior.get('rol_docente', bloque.rol_docente)
    asignatura_ant_id = anterior.get('asignatura_id', bloque.asignatura_id)
    observaciones_ant = anterior.get('observaciones', bloque.observaciones)

    # Validar que al restaurar no existan conflictos
    valido, errores, adv = validar_bloque_nuevo(
        asignatura_id=asignatura_ant_id,
        dia_semana=dia_ant,
        hora_inicio=h_ini_ant,
        hora_fin=h_fin_ant,
        modalidad=modalidad_ant,
        espacio_fisico_id=espacio_ant_id,
        profesor_id=profesor_ant_id,
        bloque_id_actual=bloque.id
    )

    if not valido:
        return jsonify({
            'success': False,
            'error': f"No se puede deshacer debido a un conflicto: {errores[0]}"
        }), 400

    # Guardar estado actual previo al revert
    dia_actual = bloque.dia_semana
    h_ini_actual = bloque.hora_inicio.strftime('%H:%M')

    # Restaurar datos del bloque
    bloque.dia_semana = dia_ant
    bloque.hora_inicio = h_ini_ant
    bloque.hora_fin = h_fin_ant
    bloque.duracion_horas = (h_fin_ant.hour * 60 + h_fin_ant.minute - (h_ini_ant.hour * 60 + h_ini_ant.minute)) / 60.0
    bloque.asignatura_id = asignatura_ant_id
    bloque.profesor_id = profesor_ant_id
    bloque.rol_docente = rol_ant
    bloque.modalidad = modalidad_ant
    bloque.tipo = tipo_ant
    bloque.espacio_fisico_id = espacio_ant_id if modalidad_ant in ['Presencial', 'Híbrido', 'Bloqueo Aula'] else None
    bloque.es_sincronico = (modalidad_ant != 'Asincrónico (PEDCO)')
    bloque.es_bloqueo_externo = (modalidad_ant == 'Bloqueo Aula')
    bloque.observaciones = observaciones_ant

    db.session.commit()

    # Registrar evento de deshacer en auditoría
    guardar_auditoria(
        accion='deshacer_bloque',
        entidad_tipo='bloque',
        entidad_id=bloque.id,
        detalles={
            'bloque_id': bloque.id,
            'restaurado_a_dia': dia_ant,
            'restaurado_a_hora_inicio': h_ini_ant_str,
            'restaurado_a_hora_fin': h_fin_ant_str,
            'dia_deshecho': dia_actual,
            'hora_deshecha': h_ini_actual,
            'audit_log_origen_id': audit_log.id
        }
    )

    return jsonify({
        'success': True,
        'message': f"¡Cambio deshecho! Clase '{bloque.asignatura.nombre}' restaurada al {bloque.dia_nombre} de {h_ini_ant.strftime('%H:%M')} a {h_fin_ant.strftime('%H:%M')}."
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
        
        # Logging de auditoría
        guardar_auditoria(
            accion="crear_profesor",
            entidad_tipo="profesor",
            entidad_id=prof.id,
            detalles={"nombre_completo": nombre_completo, "categoria": categoria_habitual, "email": email}
        )
        
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
        old_nombre = prof.nombre_completo
        old_categoria = prof.categoria_habitual
        old_email = prof.email
        
        prof.nombre_completo = request.form.get('nombre_completo', '').strip()
        prof.categoria_habitual = request.form.get('categoria_habitual', 'PAD')
        prof.email = request.form.get('email', '').strip()

        db.session.commit()
        
        # Logging de auditoría
        if (prof.nombre_completo != old_nombre or prof.categoria_habitual != old_categoria or prof.email != old_email):
            guardar_auditoria(
                accion="editar_profesor",
                entidad_tipo="profesor",
                entidad_id=prof.id,
                detalles={
                    "id": prof.id,
                    "nombre_completo": prof.nombre_completo,
                    "anterior_nombre": old_nombre,
                    "categoria": prof.categoria_habitual,
                    "anterior_categoria": old_categoria,
                    "email": prof.email,
                    "anterior_email": old_email
                }
            )
        
        flash(f'Profesor/a "{prof.nombre_completo}" actualizado con éxito.', 'success')
        return redirect(url_for('main.profesores'))

    return render_template('profesor_form.html', profesor=prof)


@main_bp.route('/profesores/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_profesor(id):
    if not current_user.is_admin:
        flash('Solo el administrador de la plataforma puede dar de baja profesores.', 'danger')
        return redirect(url_for('main.profesores'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.profesores'))

    prof = db.session.get(Profesor, id)
    if not prof:
        flash('Profesor no encontrado.', 'danger')
        return redirect(url_for('main.profesores'))

    confirm_nombre = request.form.get('confirm_nombre', '').strip()
    if confirm_nombre != prof.nombre_completo.strip():
        flash('El nombre ingresado no coincide con el nombre exacto del profesor/a. Eliminación cancelada.', 'danger')
        return redirect(url_for('main.profesores'))

    # Logging de auditoría
    guardar_auditoria(
        accion="eliminar_profesor",
        entidad_tipo="profesor",
        entidad_id=prof.id,
        detalles={
            "id": prof.id,
            "nombre_completo": prof.nombre_completo,
            "categoria": prof.categoria_habitual,
            "email": prof.email
        }
    )

    # Limpiar referencias para mantener integridad de base de datos
    User.query.filter_by(profesor_id=prof.id).update({'profesor_id': None})
    SolicitudCambio.query.filter_by(profesor_id=prof.id).delete(synchronize_session=False)
    Asignatura.query.filter_by(profesor_pad_id=prof.id).update({'profesor_pad_id': None})
    BloqueHorario.query.filter_by(profesor_id=prof.id).update({'profesor_id': None})
    prof.asignaturas_ayp = []

    db.session.delete(prof)
    db.session.commit()
    flash(f'Profesor/a "{prof.nombre_completo}" dado de baja con éxito.', 'success')

    return redirect(url_for('main.profesores'))


@main_bp.route('/materias')
@login_required
def materias():
    if current_user.is_alumno:
        flash('No tienes permisos para acceder a materias.', 'danger')
        return redirect(url_for('main.horarios'))
    
    carrera_val = request.args.get('carrera_id', '').strip()
    cuatrimestre = request.args.get('cuatrimestre', type=int)
    anio = request.args.get('anio', type=int)

    query = Asignatura.query
    solo_externas = False
    carrera_id = None

    if carrera_val in ['externas', 'externos', 'EXTERNA']:
        solo_externas = True
        query = query.filter((Asignatura.es_externa == True) | (Asignatura.carrera.has(codigo='EXTERNA')))
    elif carrera_val.isdigit():
        c_id = int(carrera_val)
        c_obj = db.session.get(Carrera, c_id)
        if c_obj and c_obj.codigo == 'EXTERNA':
            solo_externas = True
            query = query.filter((Asignatura.es_externa == True) | (Asignatura.carrera_id == c_id))
        else:
            carrera_id = c_id
            query = query.filter(Asignatura.carrera_id == c_id, Asignatura.es_externa == False)
    elif carrera_val:
        # Intento de búsqueda por código (ej: TUASSL o TUDW)
        c_obj = Carrera.query.filter_by(codigo=carrera_val.upper()).first()
        if c_obj:
            if c_obj.codigo == 'EXTERNA':
                solo_externas = True
                query = query.filter((Asignatura.es_externa == True) | (Asignatura.carrera_id == c_obj.id))
            else:
                carrera_id = c_obj.id
                query = query.filter(Asignatura.carrera_id == c_obj.id, Asignatura.es_externa == False)
    else:
        # "Todas las Carreras" regulares por defecto
        query = query.filter_by(es_externa=False)

    if cuatrimestre:
        query = query.filter_by(cuatrimestre=cuatrimestre)
    if anio:
        query = query.filter_by(anio_cursada=anio)

    lista_materias = query.order_by(Asignatura.carrera_id, Asignatura.anio_cursada, Asignatura.cuatrimestre).all()
    carreras = Carrera.query.filter(Carrera.codigo != 'EXTERNA').all()

    reporte = auditar_sistema_completo()

    return render_template('materias.html',
                           materias=lista_materias,
                           asignaturas=lista_materias,
                           carreras=carreras,
                           carrera_id=carrera_id,
                           carrera_val=carrera_val,
                           cuatrimestre=cuatrimestre,
                           anio=anio,
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

        # Logging de auditoria
        guardar_auditoria(
            accion='crear_materia',
            entidad_tipo='materia',
            entidad_id=asig.id,
            detalles={
                'nombre': nombre,
                'codigo': codigo,
                'carrera': carrera_id,
                'anio_cursada': anio_cursada,
                'cuatrimestre': cuatrimestre,
                'carga_horaria': carga_horaria_semanal,
                'es_externa': es_externa,
                'profesor_pad_id': profesor_pad_id
            }
        )

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
        old_nombre = asig.nombre
        old_codigo = asig.codigo
        old_carrera = asig.carrera_id
        old_anio = asig.anio_cursada
        old_cuatrimestre = asig.cuatrimestre
        old_carga = asig.carga_horaria_semanal
        old_pad = asig.profesor_pad_id
        old_externa = asig.es_externa
        
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
        
        # Logging de auditoria
        guardar_auditoria(
            accion='editar_materia',
            entidad_tipo='materia',
            entidad_id=asig.id,
            detalles={
                'nombre': asig.nombre,
                'anterior_nombre': old_nombre,
                'codigo': asig.codigo,
                'anterior_codigo': old_codigo,
                'carrera_id': asig.carrera_id,
                'anterior_carrera': old_carrera,
                'anio_cursada': asig.anio_cursada,
                'anterior_anio': old_anio,
                'cuatrimestre': asig.cuatrimestre,
                'anterior_cuatrimestre': old_cuatrimestre,
                'carga_horaria': asig.carga_horaria_semanal,
                'anterior_carga': old_carga,
                'profesor_pad_id': asig.profesor_pad_id,
                'anterior_pad': old_pad,
                'es_externa': asig.es_externa
            }
        )
        
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


@main_bp.route('/materias/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_materia(id):
    if not current_user.is_admin:
        flash('Solo el administrador de la plataforma puede eliminar materias.', 'danger')
        return redirect(url_for('main.materias'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.materias'))

    asig = db.session.get(Asignatura, id)
    if not asig:
        flash('Materia no encontrada.', 'danger')
        return redirect(url_for('main.materias'))

    confirm_nombre = request.form.get('confirm_nombre', '').strip()
    if confirm_nombre != asig.nombre.strip():
        flash('El nombre ingresado no coincide con el nombre exacto de la materia. Eliminación cancelada.', 'danger')
        return redirect(url_for('main.materias'))

    # Limpiar solicitudes de cambio vinculadas a los bloques de esta materia
    bloque_ids = [b.id for b in asig.bloques_horarios]
    if bloque_ids:
        SolicitudCambio.query.filter(SolicitudCambio.bloque_id.in_(bloque_ids)).delete(synchronize_session=False)

    # Logging de auditoría
    guardar_auditoria(
        accion='eliminar_materia',
        entidad_tipo='materia',
        entidad_id=asig.id,
        detalles={
            'id': asig.id,
            'nombre': asig.nombre,
            'codigo': asig.codigo,
            'carrera_id': asig.carrera_id,
            'anio_cursada': asig.anio_cursada,
            'cuatrimestre': asig.cuatrimestre,
            'carga_horaria': asig.carga_horaria_semanal,
            'bloques_eliminados': len(bloque_ids)
        }
    )

    # Limpiar ayudantes de la materia
    asig.profesores_ayp = []

    db.session.delete(asig)
    db.session.commit()
    flash(f'Materia "{asig.nombre}" y sus clases asociadas fueron eliminadas con éxito.', 'success')

    return redirect(url_for('main.materias'))


@main_bp.route('/bloques/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_bloque():
    if not current_user.is_gestor:
        flash('No tienes permisos para programar nuevas clases.', 'danger')
        return redirect(url_for('main.horarios'))

    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.horarios'))

    # Si se proporciona un asignatura_id por URL, precargar esa materia como seleccionada
    asignatura_id_pre = request.args.get('asignatura_id', type=int)

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
        
        # Obtener nombre de asignatura para el log
        asig_nombre = Asignatura.query.get(asignatura_id).nombre if asignatura_id else None
        
        # Logging de auditoria
        guardar_auditoria(
            accion='crear_bloque',
            entidad_tipo='bloque',
            entidad_id=bloque.id,
            detalles={
                'asignatura_id': asignatura_id,
                'asignatura_nombre': asig_nombre,
                'profesor_id': profesor_id,
                'rol_docente': rol_docente,
                'dia_semana': dia_semana,
                'hora_inicio': hora_inicio_str,
                'hora_fin': hora_fin_str,
                'modalidad': modalidad,
                'tipo': tipo,
                'espacio_fisico_id': espacio_fisico_id,
                'es_sincronico': es_sincronico,
                'es_bloqueo_externo': es_bloqueo_externo,
                'observaciones': observaciones
            }
        )
        
        flash('Clase / Reserva programada con éxito.', 'success')
        return redirect(url_for('main.horarios'))

    return render_template('bloque_form.html', asignaturas=asignaturas, profesores=profesores, aulas=aulas, bloque=None, dias_semana=DIAS_SEMANA, modalidades=MODALIDADES, tipos_clase=TIPOS_CLASE, DIAS_SEMANA=DIAS_SEMANA, MODALIDADES=MODALIDADES, TIPOS_CLASE=TIPOS_CLASE, asignatura_id=asignatura_id_pre)


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

        anterior = {
            'dia_semana': bloque.dia_semana,
            'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
            'hora_fin': bloque.hora_fin.strftime('%H:%M'),
            'asignatura_id': bloque.asignatura_id,
            'profesor_id': bloque.profesor_id,
            'rol_docente': bloque.rol_docente,
            'modalidad': bloque.modalidad,
            'tipo': bloque.tipo,
            'espacio_fisico_id': bloque.espacio_fisico_id,
            'observaciones': bloque.observaciones
        }

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
        
        # Logging de auditoria
        guardar_auditoria(
            accion='editar_bloque',
            entidad_tipo='bloque',
            entidad_id=bloque.id,
            detalles={
                'bloque_id': bloque.id,
                'asignatura_id': asignatura_id,
                'profesor_id': profesor_id,
                'rol_docente': rol_docente,
                'dia_semana': dia_semana,
                'hora_inicio': hora_inicio_str,
                'hora_fin': hora_fin_str,
                'modalidad': modalidad,
                'tipo': tipo,
                'espacio_fisico_id': espacio_fisico_id,
                'es_sincronico': bloque.es_sincronico,
                'es_bloqueo_externo': bloque.es_bloqueo_externo,
                'observaciones': observaciones,
                'anterior': anterior
            }
        )
        
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
        # Limpiar solicitudes asociadas para evitar conflictos de integridad
        SolicitudCambio.query.filter_by(bloque_id=bloque.id).delete(synchronize_session=False)

        # Logging de auditoria
        guardar_auditoria(
            accion='eliminar_bloque',
            entidad_tipo='bloque',
            entidad_id=bloque.id,
            detalles={
                'bloque_id': bloque.id,
                'asignatura_id': bloque.asignatura_id,
                'profesor_id': bloque.profesor_id,
                'dia_semana': bloque.dia_semana,
                'hora_inicio': str(bloque.hora_inicio),
                'hora_fin': str(bloque.hora_fin)
            }
        )
        db.session.delete(bloque)
        db.session.commit()
        flash('Clase eliminada del cronograma.', 'info')
    return redirect(url_for('main.horarios'))


@main_bp.route('/aulas')
def aulas():
    lista_aulas = EspacioFisico.query.order_by(EspacioFisico.nombre).all()
    return render_template('aulas.html', aulas=lista_aulas)


@main_bp.route('/aulas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_aula():
    if not current_user.is_gestor:
        flash('No tienes permisos para crear espacios físicos o aulas.', 'danger')
        return redirect(url_for('main.aulas'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.aulas'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo_espacio = request.form.get('tipo_espacio', 'aula_comun')
        es_laboratorio = (tipo_espacio == 'laboratorio')
        capacidad = request.form.get('capacidad', type=int, default=30)
        equipamiento = request.form.get('equipamiento', '').strip()
        activa = request.form.get('activa') == '1'

        if not nombre:
            flash('El nombre del aula es obligatorio.', 'warning')
            return render_template('aula_form.html', aula=None)

        # Verificar unicidad de nombre
        existente = EspacioFisico.query.filter_by(nombre=nombre).first()
        if existente:
            flash(f'Ya existe un espacio físico con el nombre "{nombre}".', 'danger')
            return render_template('aula_form.html', aula=None)

        aula = EspacioFisico(
            nombre=nombre,
            es_laboratorio=es_laboratorio,
            capacidad=capacidad,
            equipamiento=equipamiento,
            activa=activa
        )
        db.session.add(aula)
        db.session.commit()

        # Logging de auditoría
        guardar_auditoria(
            accion='crear_aula',
            entidad_tipo='aula',
            entidad_id=aula.id,
            detalles={
                'id': aula.id,
                'nombre': aula.nombre,
                'es_laboratorio': aula.es_laboratorio,
                'capacidad': aula.capacidad,
                'equipamiento': aula.equipamiento,
                'activa': aula.activa
            }
        )

        flash(f'Espacio físico "{aula.nombre}" creado con éxito.', 'success')
        return redirect(url_for('main.aulas'))

    return render_template('aula_form.html', aula=None)


@main_bp.route('/aulas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_aula(id):
    if not current_user.is_gestor:
        flash('No tienes permisos para editar espacios físicos o aulas.', 'danger')
        return redirect(url_for('main.aulas'))
    
    if ConfiguracionSistema.esta_congelado():
        flash('El sistema está congelado. No se permiten cambios.', 'warning')
        return redirect(url_for('main.aulas'))

    aula = db.session.get(EspacioFisico, id)
    if not aula:
        flash('Espacio físico no encontrado.', 'danger')
        return redirect(url_for('main.aulas'))

    if request.method == 'POST':
        old_nombre = aula.nombre
        old_tipo = aula.es_laboratorio
        old_capacidad = aula.capacidad
        old_equip = aula.equipamiento
        old_activa = aula.activa

        nombre = request.form.get('nombre', '').strip()
        tipo_espacio = request.form.get('tipo_espacio', 'aula_comun')
        es_laboratorio = (tipo_espacio == 'laboratorio')
        capacidad = request.form.get('capacidad', type=int, default=30)
        equipamiento = request.form.get('equipamiento', '').strip()
        activa = request.form.get('activa') == '1'

        if not nombre:
            flash('El nombre del aula es obligatorio.', 'warning')
            return render_template('aula_form.html', aula=aula)

        # Verificar unicidad si cambió el nombre
        if nombre != aula.nombre:
            existente = EspacioFisico.query.filter_by(nombre=nombre).first()
            if existente:
                flash(f'Ya existe otro espacio físico con el nombre "{nombre}".', 'danger')
                return render_template('aula_form.html', aula=aula)

        aula.nombre = nombre
        aula.es_laboratorio = es_laboratorio
        aula.capacidad = capacidad
        aula.equipamiento = equipamiento
        aula.activa = activa

        db.session.commit()

        # Logging de auditoría
        guardar_auditoria(
            accion='editar_aula',
            entidad_tipo='aula',
            entidad_id=aula.id,
            detalles={
                'id': aula.id,
                'nombre': aula.nombre,
                'anterior_nombre': old_nombre,
                'es_laboratorio': aula.es_laboratorio,
                'anterior_es_laboratorio': old_tipo,
                'capacidad': aula.capacidad,
                'anterior_capacidad': old_capacidad,
                'equipamiento': aula.equipamiento,
                'anterior_equipamiento': old_equip,
                'activa': aula.activa,
                'anterior_activa': old_activa
            }
        )

        flash(f'Espacio físico "{aula.nombre}" actualizado con éxito.', 'success')
        return redirect(url_for('main.aulas'))

    return render_template('aula_form.html', aula=aula)


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
        
        # Logging de auditoria
        guardar_auditoria(
            accion='crear_usuario',
            entidad_tipo='usuario',
            entidad_id=usuario.id,
            detalles={
                'username': username,
                'email': email,
                'nombre_completo': nombre_completo,
                'role': role,
                'profesor_id': profesor_id
            }
        )

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
        
        # Logging de auditoria
        guardar_auditoria(
            accion='editar_usuario',
            entidad_tipo='usuario',
            entidad_id=usuario.id,
            detalles={
                'username': usuario.username,
                'email': usuario.email,
                'nombre_completo': usuario.nombre_completo,
                'role': usuario.role,
                'profesor_id': usuario.profesor_id
            }
        )

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
    
    # Logging de auditoria
    guardar_auditoria(
        accion='congelar_sistema',
        entidad_tipo='configuracion',
        entidad_id=config.id,
        detalles={'motivo': config.motivo_congelacion}
    )

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
    
    # Logging de auditoria
    guardar_auditoria(
        accion='descongelar_sistema',
        entidad_tipo='configuracion',
        entidad_id=config.id,
        detalles={'motivo_anterior': None}
    )

    flash('Sistema DESCONGELADO. Ahora se permiten cambios nuevamente.', 'success')
    return redirect(url_for('main.dashboard'))


# ============================================
# RUTAS DE AUDITORIA
# ============================================

@main_bp.route('/auditoria')
@login_required
def auditoria():
    """Vista de registro de auditoría - acceso para admin y gestores."""
    if not current_user.is_gestor:
        flash('No tienes permisos para acceder al registro de auditoría.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Parámetros de filtro
    accion_filter = request.args.get('accion', '')
    entidad_filter = request.args.get('entidad', '')
    usuario_filter = request.args.get('usuario', '')
    
    query = Auditoria.query
    
    if accion_filter:
        query = query.filter(Auditoria.accion == accion_filter)
    if entidad_filter:
        query = query.filter(Auditoria.entidad_tipo == entidad_filter)
    if usuario_filter:
        query = query.filter(Auditoria.usuario_id == int(usuario_filter))
    
    registros = query.order_by(Auditoria.created_at.desc()).limit(500).all()
    
    # Estadísticas
    total_registros = Auditoria.query.count()
    acciones_distintas = db.session.query(Auditoria.accion, db.func.count(Auditoria.id)).group_by(Auditoria.accion).all()
    
    usuarios = User.query.order_by(User.username).all() if current_user.is_admin else []
    
    acciones_disponibles = [
        ('crear_profesor', 'Crear Profesor'),
        ('editar_profesor', 'Editar Profesor'),
        ('eliminar_profesor', 'Eliminar Profesor'),
        ('crear_materia', 'Crear Materia'),
        ('editar_materia', 'Editar Materia'),
        ('eliminar_materia', 'Eliminar Materia'),
        ('crear_bloque', 'Crear Bloque'),
        ('editar_bloque', 'Editar Bloque'),
        ('eliminar_bloque', 'Eliminar Bloque'),
        ('crear_usuario', 'Crear Usuario'),
        ('editar_usuario', 'Editar Usuario'),
        ('crear_aula', 'Crear Aula / Espacio'),
        ('editar_aula', 'Editar Aula / Espacio'),
        ('congelar_sistema', 'Congelar Sistema'),
        ('descongelar_sistema', 'Descongelar Sistema'),
    ]
    
    entidades_disponibles = ['profesor', 'materia', 'bloque', 'usuario', 'aula', None]
    
    return render_template('auditoria.html',
                           registros=registros,
                           total=total_registros,
                           acciones_distintas=acciones_distintas,
                           usuarios=usuarios,
                           accion_filter=accion_filter,
                           entidad_filter=entidad_filter,
                           usuario_filter=usuario_filter,
                           acciones_disponibles=acciones_disponibles,
                           entidades_disponibles=entidades_disponibles)


# ============================================
# RUTAS DE SOLICITUDES DE CAMBIO
# ============================================

@main_bp.route('/solicitudes')
@login_required
def solicitudes():
    """Vista de solicitudes de aprobación de cambios pendientes."""
    if not current_user.is_gestor:
        flash('No tienes permisos para acceder a las solicitudes de cambio.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Mostrar solo pendientes
    pendientes = SolicitudCambio.query.filter_by(estado='pendiente').order_by(SolicitudCambio.creada_en.desc()).all()
    aprobadas = SolicitudCambio.query.filter_by(estado='aprobada').order_by(SolicitudCambio.aprobada_en.desc()).limit(50).all()
    rechazadas = SolicitudCambio.query.filter_by(estado='rechazada').order_by(SolicitudCambio.aprobada_en.desc()).limit(50).all()
    
    return render_template('solicitudes.html',
                           pendientes=pendientes,
                           aprobadas=aprobadas,
                           rechazadas=rechazadas)


@main_bp.route('/solicitudes/<int:solicitud_id>/aprobar', methods=['POST'])
@login_required
def aprobar_solicitud(solicitud_id):
    """Aprueba una solicitud de cambio. Aplica el cambio al bloque automáticamente."""
    if not current_user.is_gestor:
        return jsonify({'success': False, 'error': 'No tienes permisos para aprobar solicitudes.'}), 403
    
    solicitud = db.session.get(SolicitudCambio, solicitud_id)
    if not solicitud:
        return jsonify({'success': False, 'error': 'Solicitud no encontrada.'}), 404
    
    if solicitud.estado != 'pendiente':
        return jsonify({'success': False, 'error': 'La solicitud ya fue procesada.'}), 400
    
    # Obtener el bloque
    bloque = db.session.get(BloqueHorario, solicitud.bloque_id)
    if not bloque:
        return jsonify({'success': False, 'error': 'El bloque asociado no existe.'}), 404
    
    # Registrar la aprobación
    from app.audit_helpers import aprobar_solicitud as helper_aprobar
    result = helper_aprobar(solicitud_id, current_user)
    
    if result:
        # Registrar auditoría de la aprobación
        guardar_auditoria(
            accion='aprobacion_cambio',
            entidad_tipo='solicitud_cambio',
            entidad_id=solicitud_id,
            detalles={
                'solicitud_id': solicitud_id,
                'bloque_id': solicitud.bloque_id,
                'profesor_id': solicitud.profesor_id,
                'descripcion': solicitud.descripcion,
                'aprobado_por': current_user.username
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Solicitud #{solicitud_id} aprobada. El cambio fue aplicado al bloque.'
        })
    
    return jsonify({'success': False, 'error': 'Error al aprobar la solicitud.'}), 500


@main_bp.route('/solicitudes/<int:solicitud_id>/rechazar', methods=['POST'])
@login_required
def rechazar_solicitud_route(solicitud_id):
    """Rechaza una solicitud de cambio."""
    if not current_user.is_gestor:
        return jsonify({'success': False, 'error': 'No tienes permisos para rechazar solicitudes.'}), 403
    
    solicitud = db.session.get(SolicitudCambio, solicitud_id)
    if not solicitud:
        return jsonify({'success': False, 'error': 'Solicitud no encontrada.'}), 404
    
    if solicitud.estado != 'pendiente':
        return jsonify({'success': False, 'error': 'La solicitud ya fue procesada.'}), 400
    
    from app.audit_helpers import rechazar_solicitud as helper_rechazar
    result = helper_rechazar(solicitud_id, current_user)
    
    if result:
        guardar_auditoria(
            accion='rechazo_cambio',
            entidad_tipo='solicitud_cambio',
            entidad_id=solicitud_id,
            detalles={
                'solicitud_id': solicitud_id,
                'bloque_id': solicitud.bloque_id,
                'profesor_id': solicitud.profesor_id,
                'descripcion': solicitud.descripcion,
                'rechazado_por': current_user.username
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Solicitud #{solicitud_id} rechazada.'
        })
    
    return jsonify({'success': False, 'error': 'Error al rechazar la solicitud.'}), 500


@main_bp.route('/solicitudes/<int:solicitud_id>/detalle')
@login_required
def detalle_solicitud(solicitud_id):
    """Devuelve detalles JSON de una solicitud para mostrar en modal."""
    solicitud = db.session.get(SolicitudCambio, solicitud_id)
    if not solicitud:
        return jsonify({'error': 'No encontrada'}), 404
    
    bloque = db.session.get(BloqueHorario, solicitud.bloque_id)
    profesor = db.session.get(Profesor, solicitud.profesor_id)
    solicitante = db.session.get(User, solicitud.solicitado_por_id)
    
    return jsonify({
        'id': solicitud.id,
        'estado': solicitud.estado,
        'descripcion': solicitud.descripcion,
        'creada_en': solicitud.creada_en.isoformat() if solicitud.creada_en else None,
        'bloque': {
            'id': bloque.id if bloque else None,
            'asignatura_nombre': bloque.asignatura.nombre if bloque and bloque.asignatura else None,
            'dia_nombre': bloque.dia_nombre if bloque else None,
            'hora_inicio': str(bloque.hora_inicio) if bloque else None,
            'hora_fin': str(bloque.hora_fin) if bloque else None,
            'modalidad': bloque.modalidad if bloque else None,
        },
        'profesor': {
            'id': profesor.id if profesor else None,
            'nombre_completo': profesor.nombre_completo if profesor else None,
        },
        'solicitante': {
            'id': solicitante.id if solicitante else None,
            'username': solicitante.username if solicitante else None,
            'nombre_completo': solicitante.nombre_completo if solicitante else None,
        }
    })
