import math
from datetime import datetime, time
from app import db
from app.models import Asignatura, BloqueHorario, EspacioFisico, Carrera, Profesor

def calcular_minimo_sincronico(carga_horaria_total):
    if not carga_horaria_total or carga_horaria_total <= 0:
        return 0
    return math.floor(carga_horaria_total / 2) + 1


def time_to_minutes(t):
    if isinstance(t, str):
        parts = t.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    return t.hour * 60 + t.minute


def hay_solapamiento_horario(inicio1, fin1, inicio2, fin2):
    m_ini1 = time_to_minutes(inicio1)
    m_fin1 = time_to_minutes(fin1)
    m_ini2 = time_to_minutes(inicio2)
    m_fin2 = time_to_minutes(fin2)
    return max(m_ini1, m_ini2) < min(m_fin1, m_fin2)


def validar_bloque_nuevo(asignatura_id, dia_semana, hora_inicio, hora_fin, modalidad, espacio_fisico_id=None, profesor_id=None, bloque_id_actual=None):
    errores = []
    advertencias = []
    
    asignatura = db.session.get(Asignatura, asignatura_id)
    if not asignatura:
        return False, ["La asignatura especificada no existe."], []

    m_ini = time_to_minutes(hora_inicio)
    m_fin = time_to_minutes(hora_fin)
    if m_fin <= m_ini:
        errores.append("La hora de fin debe ser posterior a la hora de inicio.")

    # 1. Colisión de Aula (Solo si requiere aula física: Presencial, Híbrido o Bloqueo Aula)
    if modalidad in ['Presencial', 'Híbrido', 'Bloqueo Aula'] and espacio_fisico_id:
        bloques_aula = BloqueHorario.query.filter(
            BloqueHorario.espacio_fisico_id == espacio_fisico_id,
            BloqueHorario.dia_semana == dia_semana,
            BloqueHorario.modalidad.in_(['Presencial', 'Híbrido', 'Bloqueo Aula'])
        ).all()

        for b in bloques_aula:
            if bloque_id_actual and b.id == bloque_id_actual:
                continue
            if hay_solapamiento_horario(hora_inicio, hora_fin, b.hora_inicio, b.hora_fin):
                aula = db.session.get(EspacioFisico, espacio_fisico_id)
                nombre_aula = aula.nombre if aula else f"ID {espacio_fisico_id}"
                
                if b.asignatura.es_externa or b.es_bloqueo_externo:
                    errores.append(
                        f"Bloqueo de Aula Físico: El espacio '{nombre_aula}' está bloqueado el {b.dia_nombre} "
                        f"de {b.hora_inicio.strftime('%H:%M')} a {b.hora_fin.strftime('%H:%M')} por una materia/actividad externa ('{b.asignatura.nombre}')."
                    )
                else:
                    errores.append(
                        f"Conflicto de Aula: El espacio '{nombre_aula}' ya se encuentra ocupado el {b.dia_nombre} "
                        f"de {b.hora_inicio.strftime('%H:%M')} a {b.hora_fin.strftime('%H:%M')} por '{b.asignatura.nombre}'."
                    )

    # 2. Colisión de Docente / Profesor (Si el mismo profesor tiene asignada otra clase sincrónica)
    if profesor_id and modalidad != 'Asincrónico (PEDCO)':
        bloques_profesor = BloqueHorario.query.filter(
            BloqueHorario.profesor_id == profesor_id,
            BloqueHorario.dia_semana == dia_semana,
            BloqueHorario.es_sincronico == True
        ).all()

        profesor_obj = db.session.get(Profesor, profesor_id)
        prof_nombre = profesor_obj.nombre_completo if profesor_obj else f"ID {profesor_id}"

        for b in bloques_profesor:
            if bloque_id_actual and b.id == bloque_id_actual:
                continue
            if hay_solapamiento_horario(hora_inicio, hora_fin, b.hora_inicio, b.hora_fin):
                errores.append(
                    f"Conflicto de Docente: El profesor/a '{prof_nombre}' ya tiene asignado el dictado de "
                    f"'{b.asignatura.nombre}' ({b.rol_docente_label}) el {b.dia_nombre} de {b.hora_inicio.strftime('%H:%M')} a {b.hora_fin.strftime('%H:%M')}."
                )

    # 3. Colisión de Cohorte (Mismo año y cuatrimestre de la misma carrera)
    if not asignatura.es_externa and modalidad != 'Asincrónico (PEDCO)':
        bloques_cohorte = BloqueHorario.query.join(Asignatura).filter(
            Asignatura.carrera_id == asignatura.carrera_id,
            Asignatura.anio_cursada == asignatura.anio_cursada,
            Asignatura.cuatrimestre == asignatura.cuatrimestre,
            BloqueHorario.dia_semana == dia_semana,
            BloqueHorario.es_sincronico == True,
            Asignatura.id != asignatura.id
        ).all()

        for b in bloques_cohorte:
            if bloque_id_actual and b.id == bloque_id_actual:
                continue
            if hay_solapamiento_horario(hora_inicio, hora_fin, b.hora_inicio, b.hora_fin):
                advertencias.append(
                    f"Advertencia de Cohorte: Solapamiento horaria para estudiantes de {asignatura.anio_cursada}° Año "
                    f"({asignatura.cuatrimestre}° Cuatrimestre) de {asignatura.carrera.codigo} con la materia '{b.asignatura.nombre}' "
                    f"({b.hora_inicio.strftime('%H:%M')} - {b.hora_fin.strftime('%H:%M')})."
                )

    es_valido = len(errores) == 0
    return es_valido, errores, advertencias


def obtener_ids_bloques_en_conflicto():
    """Retorna un conjunto de IDs de bloques horarios que tienen conflicto de aula física o conflicto de docente."""
    ids_conflictos = set()
    
    # 1. Conflictos de Aula
    bloques_fisicos = BloqueHorario.query.filter(
        BloqueHorario.modalidad.in_(['Presencial', 'Híbrido', 'Bloqueo Aula']),
        BloqueHorario.espacio_fisico_id.isnot(None)
    ).all()

    for i in range(len(bloques_fisicos)):
        for j in range(i + 1, len(bloques_fisicos)):
            b1 = bloques_fisicos[i]
            b2 = bloques_fisicos[j]
            if b1.espacio_fisico_id == b2.espacio_fisico_id and b1.dia_semana == b2.dia_semana:
                if hay_solapamiento_horario(b1.hora_inicio, b1.hora_fin, b2.hora_inicio, b2.hora_fin):
                    ids_conflictos.add(b1.id)
                    ids_conflictos.add(b2.id)

    # 2. Conflictos de Docentes
    bloques_docentes = BloqueHorario.query.filter(
        BloqueHorario.profesor_id.isnot(None),
        BloqueHorario.es_sincronico == True
    ).all()

    for i in range(len(bloques_docentes)):
        for j in range(i + 1, len(bloques_docentes)):
            b1 = bloques_docentes[i]
            b2 = bloques_docentes[j]
            if b1.profesor_id == b2.profesor_id and b1.dia_semana == b2.dia_semana:
                if hay_solapamiento_horario(b1.hora_inicio, b1.hora_fin, b2.hora_inicio, b2.hora_fin):
                    ids_conflictos.add(b1.id)
                    ids_conflictos.add(b2.id)

    return ids_conflictos


def auditar_sistema_completo():
    asignaturas = Asignatura.query.filter_by(es_externa=False).all()
    reporte = {
        'total_asignaturas': len(asignaturas),
        'cumplen_sincronico': 0,
        'incumplen_sincronico': [],
        'conflictos_aulas': [],
        'conflictos_docentes': [],
        'bloqueos_externos_activos': 0,
        'detalles_asignaturas': []
    }

    for asig in asignaturas:
        min_sinc = asig.min_horas_sincronicas
        prog_sinc = asig.total_horas_sincronicas_programadas
        prog_asin = asig.total_horas_asincronicas_programadas
        cumple = asig.cumple_regla_sincronica

        if cumple:
            reporte['cumplen_sincronico'] += 1
        else:
            reporte['incumplen_sincronico'].append({
                'id': asig.id,
                'nombre': asig.nombre,
                'carrera': asig.carrera.codigo,
                'anio': asig.anio_cursada,
                'cuatrimestre': asig.cuatrimestre,
                'carga_total': asig.carga_horaria_semanal,
                'min_sincronico': min_sinc,
                'prog_sincronico': prog_sinc,
                'deficit': min_sinc - prog_sinc
            })

        reporte['detalles_asignaturas'].append({
            'id': asig.id,
            'nombre': asig.nombre,
            'carrera': asig.carrera.codigo,
            'anio': asig.anio_cursada,
            'cuatrimestre': asig.cuatrimestre,
            'carga_total': asig.carga_horaria_semanal,
            'min_sincronico': min_sinc,
            'prog_sincronico': prog_sinc,
            'prog_asincronico': prog_asin,
            'cumple': cumple
        })

    # Detección de Conflictos de Aula
    bloques_fisicos = BloqueHorario.query.filter(
        BloqueHorario.modalidad.in_(['Presencial', 'Híbrido', 'Bloqueo Aula']),
        BloqueHorario.espacio_fisico_id.isnot(None)
    ).all()

    for b in bloques_fisicos:
        if b.es_bloqueo_externo or b.asignatura.es_externa:
            reporte['bloqueos_externos_activos'] += 1

    for i in range(len(bloques_fisicos)):
        for j in range(i + 1, len(bloques_fisicos)):
            b1 = bloques_fisicos[i]
            b2 = bloques_fisicos[j]
            if b1.espacio_fisico_id == b2.espacio_fisico_id and b1.dia_semana == b2.dia_semana:
                if hay_solapamiento_horario(b1.hora_inicio, b1.hora_fin, b2.hora_inicio, b2.hora_fin):
                    aula = db.session.get(EspacioFisico, b1.espacio_fisico_id)
                    reporte['conflictos_aulas'].append({
                        'b1_id': b1.id,
                        'b2_id': b2.id,
                        'aula': aula.nombre if aula else 'Desconocida',
                        'dia': b1.dia_nombre,
                        'materia1': b1.asignatura.nombre,
                        'carrera1': b1.asignatura.carrera.codigo,
                        'horario1': f"{b1.hora_inicio.strftime('%H:%M')}-{b1.hora_fin.strftime('%H:%M')}",
                        'materia2': b2.asignatura.nombre,
                        'carrera2': b2.asignatura.carrera.codigo,
                        'horario2': f"{b2.hora_inicio.strftime('%H:%M')}-{b2.hora_fin.strftime('%H:%M')}"
                    })

    # Detección de Conflictos de Docentes
    bloques_docentes = BloqueHorario.query.filter(
        BloqueHorario.profesor_id.isnot(None),
        BloqueHorario.es_sincronico == True
    ).all()

    for i in range(len(bloques_docentes)):
        for j in range(i + 1, len(bloques_docentes)):
            b1 = bloques_docentes[i]
            b2 = bloques_docentes[j]
            if b1.profesor_id == b2.profesor_id and b1.dia_semana == b2.dia_semana:
                if hay_solapamiento_horario(b1.hora_inicio, b1.hora_fin, b2.hora_inicio, b2.hora_fin):
                    prof = db.session.get(Profesor, b1.profesor_id)
                    reporte['conflictos_docentes'].append({
                        'profesor': prof.nombre_completo if prof else 'Desconocido',
                        'categoria': b1.rol_docente_label,
                        'dia': b1.dia_nombre,
                        'materia1': b1.asignatura.nombre,
                        'horario1': f"{b1.hora_inicio.strftime('%H:%M')}-{b1.hora_fin.strftime('%H:%M')}",
                        'materia2': b2.asignatura.nombre,
                        'horario2': f"{b2.hora_inicio.strftime('%H:%M')}-{b2.hora_fin.strftime('%H:%M')}"
                    })

    return reporte
