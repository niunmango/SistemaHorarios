# -*- coding: utf-8 -*-
"""Helpers para el sistema de auditoría y aprobación de cambios."""
import json
from datetime import datetime, timezone
from flask import request
from flask_login import current_user
from app import db


def guardar_auditoria(accion, entidad_tipo=None, entidad_id=None, detalles=None, ip=None):
    """Registra una entrada en la tabla de auditoría."""
    ip_address = ip or request.remote_addr if hasattr(request, 'remote_addr') else '127.0.0.1'
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


def obtener_profesor_usuario(user):
    """Devuelve el ID del profesor asociado al usuario, o None."""
    if user.profesor_id:
        return user.profesor_id
    if user.profesor:
        return user.profesor.id
    return None


def es_solicitar_aprobacion(user, bloque):
    """
    Determina si un docente PAD/AYP debe solicitar aprobación para editar este bloque.
    
    Regla:
    - Si es gestor (admin/gestor_aulas/gestor): NO necesita aprobación (puede editar todo directamente)
    - Si es docente:
        - Si el docente es PAD o AYP de la materia del bloque: puede editar SIN aprobación
        - Si el docente NO es PAD/AYP de la materia del bloque: debe solicitar aprobación
    """
    if user.is_gestor:
        return False
    
    if user.role != 'docente' or not bloque:
        return False
    
    my_prof_id = obtener_profesor_usuario(user)
    if my_prof_id is None:
        return False
    
    # Verificar si el profesor es PAD/AYP de la materia del bloque
    from app.models import Asignatura
    asig = db.session.get(Asignatura, bloque.asignatura_id)
    if not asig:
        return False
    
    # PAD de la materia
    if asig.profesor_pad_id == my_prof_id:
        return False
    
    # AYP de la materia
    for ayp in asig.profesores_ayp:
        if ayp.id == my_prof_id:
            return False
    
    # No es PAD ni AYP de esta materia -> requiere aprobación
    return True


def crear_solicitud_aprobacion(bloque, user, descripcion):
    """Crea una solicitud de aprobación para un bloque que requiere permiso."""
    from app.models import SolicitudCambio, Profesor
    my_prof_id = obtener_profesor_usuario(user)
    
    solicitud = SolicitudCambio(
        bloque_id=bloque.id,
        profesor_id=my_prof_id or 0,
        descripcion=descripcion,
        estado='pendiente',
        solicitado_por_id=user.id
    )
    db.session.add(solicitud)
    db.session.commit()
    return solicitud


def aprobar_solicitud(solicitud_id, user, approver_notes=None):
    """Aprueba una solicitud de cambio. El bloque se edita según lo solicitado."""
    from app.models import SolicitudCambio
    solicitud = db.session.get(SolicitudCambio, solicitud_id)
    if not solicitud:
        return None
    
    solicitud.estado = 'aprobada'
    solicitud.aprobado_por_id = user.id
    solicitud.aprobada_en = datetime.now(timezone.utc)
    if approver_notes:
        solicitud.observaciones_admin = approver_notes
    
    db.session.commit()
    return solicitud


def rechazar_solicitud(solicitud_id, user, notes=None):
    """Rechaza una solicitud de cambio."""
    from app.models import SolicitudCambio
    solicitud = db.session.get(SolicitudCambio, solicitud_id)
    if not solicitud:
        return None
    
    solicitud.estado = 'rechazada'
    solicitud.aprobado_por_id = user.id
    solicitud.aprobada_en = datetime.now(timezone.utc)
    if notes:
        solicitud.observaciones_admin = notes
    
    db.session.commit()
    return solicitud
