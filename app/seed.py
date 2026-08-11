from datetime import time
from app import db
from app.models import User, Carrera, Asignatura, EspacioFisico, BloqueHorario, Profesor

def seed_database():
    """Puebla la base de datos con los usuarios base, lista de profesores (con roles por materia) y los planes de estudio completos de TUASSL, TUDW y materias externas."""
    
    db.drop_all()
    db.create_all()

    print("🌱 Inicializando datos base del CURZA (Profesores, TUASSL, TUDW, Aulas)...")

    # 1. Plantel Docente (Personas)
    p_ramiro = Profesor(nombre_completo='Ramiro García Poggi', categoria_habitual='PAD', email='ramiro.garcia@fi.uncoma.edu.ar')
    p_fabian = Profesor(nombre_completo='Néstor Fabián Imberti', categoria_habitual='PAD', email='fabian.imberti@fi.uncoma.edu.ar')
    p_carolina = Profesor(nombre_completo='Carolina Juárez', categoria_habitual='PAD', email='carolina.juarez@fi.uncoma.edu.ar')
    p_manuel = Profesor(nombre_completo='Manuel Jove López', categoria_habitual='AYP', email='manuel.jove@fi.uncoma.edu.ar')
    p_lucas = Profesor(nombre_completo='Lucas Linquiman', categoria_habitual='AYP', email='lucas.linquiman@fi.uncoma.edu.ar')
    p_corujo = Profesor(nombre_completo='Enrique Corujo', categoria_habitual='PAD', email='enrique.corujo@fi.uncoma.edu.ar')
    p_guerra = Profesor(nombre_completo='Eduardo Guerra', categoria_habitual='PAD', email='eduardo.guerra@fi.uncoma.edu.ar')
    p_meloni = Profesor(nombre_completo='César Meloni', categoria_habitual='PAD', email='cesar.meloni@fi.uncoma.edu.ar')
    p_fede = Profesor(nombre_completo='Federico Blicharski', categoria_habitual='AYP', email='federico.b@fi.uncoma.edu.ar')
    p_daher = Profesor(nombre_completo='Prof. Daher', categoria_habitual='PAD', email='daher@fi.uncoma.edu.ar')

    db.session.add_all([p_ramiro, p_fabian, p_carolina, p_manuel, p_lucas, p_corujo, p_guerra, p_meloni, p_fede, p_daher])
    db.session.commit()

    # 2. Usuarios Base (con vinculación docente)
    admin = User(username='admin', email='admin@fi.uncoma.edu.ar', nombre_completo='Administrador del Sistema', role='admin')
    admin.set_password('admin123')

    gestor = User(username='gestor', email='gestor@fi.uncoma.edu.ar', nombre_completo='Coordinador de Horarios CURZA', role='gestor_aulas')
    gestor.set_password('gestor123')

    docente = User(username='docente', email='docente@fi.uncoma.edu.ar', nombre_completo='Ramiro García Poggi', role='docente', profesor=p_ramiro)
    docente.set_password('docente123')

    alumno = User(username='alumno', email='alumno@fi.uncoma.edu.ar', nombre_completo='Estudiante UNComa', role='alumno')
    alumno.set_password('alumno123')

    db.session.add_all([admin, gestor, docente, alumno])
    db.session.commit()

    # 3. Carreras
    tuassl = Carrera(codigo='TUASSL', nombre='Tecnicatura Universitaria en Administración de Sistemas y Software Libre', descripcion='Ordenanza 0895/12 CS - CURZA / FI')
    tudw = Carrera(codigo='TUDW', nombre='Tecnicatura Universitaria en Desarrollo Web', descripcion='Ordenanza 0885/12 CS - CURZA / FI')
    externa = Carrera(codigo='EXTERNA', nombre='Materias y Bloqueos Externos', descripcion='Materias de Exactas, otras carreras o eventos de reserva de aulas')
    
    db.session.add_all([tuassl, tudw, externa])
    db.session.commit()

    # 4. Espacios Físicos / Aulas Consolidados
    s1 = EspacioFisico(nombre='Sala 1 (JCBrocca)', capacidad=30, es_laboratorio=True, equipamiento='30 PCs con Linux/Windows, Sistema Híbrido Videoconferencia, Proyector')
    s2 = EspacioFisico(nombre='Sala 2 (JColombo)', capacidad=30, es_laboratorio=True, equipamiento='30 PCs con Linux, Pantalla Interactiva, Red dedicada')
    a18 = EspacioFisico(nombre='Aula 18', capacidad=40, es_laboratorio=False, equipamiento='Proyector, Pizarrón')
    a21 = EspacioFisico(nombre='Aula 21', capacidad=40, es_laboratorio=False, equipamiento='Proyector, Pizarrón')
    
    db.session.add_all([s1, s2, a18, a21])
    db.session.commit()

    # ------------------ TUASSL (Ord. 0895/12) ------------------
    # 1° Año - 1° Cuatri
    tuassl_ic = Asignatura(carrera=tuassl, anio_cursada=1, cuatrimestre=1, codigo='TUASSL-101', nombre='Introducción a la Computación', carga_horaria_semanal=8, profesor_cargo='Cátedra Introducción')
    tuassl_mg = Asignatura(carrera=tuassl, anio_cursada=1, cuatrimestre=1, codigo='TUASSL-102', nombre='Matemática General', carga_horaria_semanal=8, profesor_cargo='Cátedra Matemática')
    tuassl_it = Asignatura(carrera=tuassl, anio_cursada=1, cuatrimestre=1, codigo='TUASSL-103', nombre='Inglés Técnico', carga_horaria_semanal=4, profesor_cargo='Cátedra Idiomas')

    # 1° Año - 2° Cuatri
    tuassl_ip = Asignatura(carrera=tuassl, anio_cursada=1, cuatrimestre=2, codigo='TUASSL-104', nombre='Introducción a la Programación', carga_horaria_semanal=8, profesor_pad=p_carolina, profesores_ayp=[p_manuel])
    tuassl_ias = Asignatura(carrera=tuassl, anio_cursada=1, cuatrimestre=2, codigo='TUASSL-105', nombre='Introducción a la Administración de Sistemas', carga_horaria_semanal=4, profesor_pad=p_fabian)
    tuassl_rd = Asignatura(carrera=tuassl, anio_cursada=1, cuatrimestre=2, codigo='TUASSL-106', nombre='Redes de Datos', carga_horaria_semanal=8, profesor_pad=p_fabian)

    # 2° Año - 1° Cuatri
    tuassl_sl = Asignatura(carrera=tuassl, anio_cursada=2, cuatrimestre=1, codigo='TUASSL-201', nombre='Software Libre', carga_horaria_semanal=4, profesor_cargo='Cátedra Software Libre')
    tuassl_ths = Asignatura(carrera=tuassl, anio_cursada=2, cuatrimestre=1, codigo='TUASSL-202', nombre='Taller de Hardware y Software', carga_horaria_semanal=8, profesor_cargo='Cátedra Hardware')
    tuassl_as = Asignatura(carrera=tuassl, anio_cursada=2, cuatrimestre=1, codigo='TUASSL-203', nombre='Administración de Sistemas', carga_horaria_semanal=8, profesor_pad=p_fabian)

    # 2° Año - 2° Cuatri
    tuassl_ase = Asignatura(carrera=tuassl, anio_cursada=2, cuatrimestre=2, codigo='TUASSL-204', nombre='Administración de Servicios', carga_horaria_semanal=8, profesor_pad=p_ramiro)
    tuassl_si = Asignatura(carrera=tuassl, anio_cursada=2, cuatrimestre=2, codigo='TUASSL-205', nombre='Sistemas de Información', carga_horaria_semanal=8, profesor_pad=p_corujo)
    tuassl_ays = Asignatura(carrera=tuassl, anio_cursada=2, cuatrimestre=2, codigo='TUASSL-206', nombre='Automatización y Scripting', carga_horaria_semanal=4, profesor_pad=p_ramiro, profesores_ayp=[p_lucas])

    # 3° Año - 1° Cuatri
    tuassl_asa = Asignatura(carrera=tuassl, anio_cursada=3, cuatrimestre=1, codigo='TUASSL-301', nombre='Administración de Sistemas Avanzada', carga_horaria_semanal=8, profesor_cargo='Cátedra Avanzada')
    tuassl_al = Asignatura(carrera=tuassl, anio_cursada=3, cuatrimestre=1, codigo='TUASSL-302', nombre='Aplicaciones Libres', carga_horaria_semanal=8, profesor_cargo='Cátedra Aplicaciones')
    tuassl_el = Asignatura(carrera=tuassl, anio_cursada=3, cuatrimestre=1, codigo='TUASSL-303', nombre='Electiva: Implantación de Sistemas de Software Libre / Redes II', carga_horaria_semanal=4, profesor_cargo='Cátedra Electivas')

    db.session.add_all([
        tuassl_ic, tuassl_mg, tuassl_it, tuassl_ip, tuassl_ias, tuassl_rd,
        tuassl_sl, tuassl_ths, tuassl_as, tuassl_ase, tuassl_si, tuassl_ays,
        tuassl_asa, tuassl_al, tuassl_el
    ])
    db.session.commit()

    # ------------------ TUDW (Ord. 0885/12) ------------------
    # 1° Año - 1° Cuatri
    tudw_mg = Asignatura(carrera=tudw, anio_cursada=1, cuatrimestre=1, codigo='TUDW-101', nombre='Matemática General', carga_horaria_semanal=8, profesor_cargo='Cátedra Matemática')
    tudw_ip = Asignatura(carrera=tudw, anio_cursada=1, cuatrimestre=1, codigo='TUDW-102', nombre='Introducción a la Programación', carga_horaria_semanal=8, profesor_cargo='Cátedra Programación')
    tudw_it = Asignatura(carrera=tudw, anio_cursada=1, cuatrimestre=1, codigo='TUDW-103', nombre='Inglés Técnico', carga_horaria_semanal=4, profesor_cargo='Cátedra Idiomas')

    # 1° Año - 2° Cuatri
    tudw_pelw = Asignatura(carrera=tudw, anio_cursada=1, cuatrimestre=2, codigo='TUDW-104', nombre='Programación Estática y Laboratorio Web', carga_horaria_semanal=8, profesor_pad=p_ramiro)
    tudw_ipoo = Asignatura(carrera=tudw, anio_cursada=1, cuatrimestre=2, codigo='TUDW-105', nombre='Introducción a la Programación Orientada a Objetos', carga_horaria_semanal=8, profesor_pad=p_guerra)
    tudw_cbd = Asignatura(carrera=tudw, anio_cursada=1, cuatrimestre=2, codigo='TUDW-106', nombre='Conceptos de Bases de Datos', carga_horaria_semanal=4, profesor_pad=p_corujo)

    # 2° Año - 1° Cuatri
    tudw_pwd = Asignatura(carrera=tudw, anio_cursada=2, cuatrimestre=1, codigo='TUDW-201', nombre='Programación Web Dinámica', carga_horaria_semanal=10, profesor_cargo='Cátedra Web Dinámica')
    tudw_asc = Asignatura(carrera=tudw, anio_cursada=2, cuatrimestre=1, codigo='TUDW-202', nombre='Arquitectura y Seguridad de Computadoras', carga_horaria_semanal=8, profesor_cargo='Cátedra Seguridad')
    tudw_dg = Asignatura(carrera=tudw, anio_cursada=2, cuatrimestre=1, codigo='TUDW-203', nombre='Diseño Gráfico', carga_horaria_semanal=4, profesor_cargo='Cátedra Diseño')

    # 2° Año - 2° Cuatri
    tudw_pwa = Asignatura(carrera=tudw, anio_cursada=2, cuatrimestre=2, codigo='TUDW-204', nombre='Programación Web Avanzada', carga_horaria_semanal=10, profesor_pad=p_meloni)
    tudw_adds = Asignatura(carrera=tudw, anio_cursada=2, cuatrimestre=2, codigo='TUDW-205', nombre='Análisis, Diseño y Documentación de Sistemas', carga_horaria_semanal=8, profesores_ayp=[p_fede])

    # 3° Año - 1° Cuatri
    tudw_fi = Asignatura(carrera=tudw, anio_cursada=3, cuatrimestre=1, codigo='TUDW-301', nombre='Frameworks e Interoperabilidad', carga_horaria_semanal=10, profesor_cargo='Cátedra Frameworks')
    tudw_tf = Asignatura(carrera=tudw, anio_cursada=3, cuatrimestre=1, codigo='TUDW-302', nombre='Trabajo Final Tecnicatura en Desarrollo Web', carga_horaria_semanal=10, profesor_cargo='Comisión Trabajo Final')

    db.session.add_all([
        tudw_mg, tudw_ip, tudw_it, tudw_pelw, tudw_ipoo, tudw_cbd,
        tudw_pwd, tudw_asc, tudw_dg, tudw_pwa, tudw_adds, tudw_fi, tudw_tf
    ])
    db.session.commit()

    # ------------------ EXTERNA (BLOQUEOS DE AULA) ------------------
    ext_est = Asignatura(carrera=externa, anio_cursada=1, cuatrimestre=2, codigo='EXT-01', nombre='Estadística Aplicada', carga_horaria_semanal=6, profesor_pad=p_daher, es_externa=True)
    ext_eagr = Asignatura(carrera=externa, anio_cursada=1, cuatrimestre=2, codigo='EXT-02', nombre='Estadística Agropecuaria', carga_horaria_semanal=5, profesor_pad=p_daher, es_externa=True)
    ext_tec = Asignatura(carrera=externa, anio_cursada=1, cuatrimestre=2, codigo='EXT-03', nombre='Tecnología', carga_horaria_semanal=6, profesor_cargo='Prof. Cecilia (PAD)', es_externa=True)
    ext_mat1 = Asignatura(carrera=externa, anio_cursada=1, cuatrimestre=2, codigo='EXT-04', nombre='Matemática 1', carga_horaria_semanal=6, profesor_cargo='Prof. Ana (PAD)', es_externa=True)

    db.session.add_all([ext_est, ext_eagr, ext_tec, ext_mat1])
    db.session.commit()

    # 5. Carga de Bloques Horarios con rol especificado (PAD en Teoría, AYP en Práctica)
    b_ip1 = BloqueHorario(asignatura=tuassl_ip, espacio_fisico=s1, profesor=p_manuel, rol_docente='AYP', dia_semana=0, hora_inicio=time(15,0), hora_fin=time(17,0), duracion_horas=2.0, tipo='Taller', modalidad='Híbrido', es_sincronico=True, observaciones='Práctica / Taller - Ayudante Manuel Jove (AYP)')
    b_ip2 = BloqueHorario(asignatura=tuassl_ip, espacio_fisico=s1, profesor=p_manuel, rol_docente='AYP', dia_semana=2, hora_inicio=time(15,0), hora_fin=time(17,0), duracion_horas=2.0, tipo='Taller', modalidad='Híbrido', es_sincronico=True, observaciones='Práctica / Taller - Ayudante Manuel Jove (AYP)')
    b_ip3 = BloqueHorario(asignatura=tuassl_ip, espacio_fisico=None, profesor=p_carolina, rol_docente='PAD', dia_semana=3, hora_inicio=time(17,0), hora_fin=time(18,0), duracion_horas=1.0, tipo='Teoría', modalidad='Virtual', es_sincronico=True, observaciones='Teoría - Prof. Adjunta Carolina Juárez (PAD)')
    b_ip4 = BloqueHorario(asignatura=tuassl_ip, espacio_fisico=None, profesor=p_carolina, rol_docente='PAD', dia_semana=4, hora_inicio=time(0,0), hora_fin=time(0,0), duracion_horas=3.0, tipo='Plataforma Asincrónica', modalidad='Asincrónico (PEDCO)', es_sincronico=False)
    db.session.add_all([b_ip1, b_ip2, b_ip3, b_ip4])

    b_ias1 = BloqueHorario(asignatura=tuassl_ias, espacio_fisico=s1, profesor=p_fabian, rol_docente='PAD', dia_semana=1, hora_inicio=time(15,0), hora_fin=time(17,0), duracion_horas=2.0, tipo='Taller', modalidad='Híbrido', es_sincronico=True, observaciones='Taller - Prof. Adjunto Fabián Imberti (PAD)')
    b_ias2 = BloqueHorario(asignatura=tuassl_ias, espacio_fisico=None, profesor=p_fabian, rol_docente='PAD', dia_semana=3, hora_inicio=time(18,30), hora_fin=time(20,30), duracion_horas=2.0, tipo='Teoría', modalidad='Virtual', es_sincronico=True)
    db.session.add_all([b_ias1, b_ias2])

    b_rd1 = BloqueHorario(asignatura=tuassl_rd, espacio_fisico=s1, profesor=p_fabian, rol_docente='PAD', dia_semana=0, hora_inicio=time(17,0), hora_fin=time(19,0), duracion_horas=2.0, tipo='Taller', modalidad='Híbrido', es_sincronico=True, observaciones='Taller - Prof. Adjunto Fabián Imberti (PAD)')
    b_rd2 = BloqueHorario(asignatura=tuassl_rd, espacio_fisico=None, profesor=p_fabian, rol_docente='PAD', dia_semana=1, hora_inicio=time(17,0), hora_fin=time(19,0), duracion_horas=2.0, tipo='Teoría', modalidad='Virtual', es_sincronico=True)
    b_rd3 = BloqueHorario(asignatura=tuassl_rd, espacio_fisico=None, profesor=p_fabian, rol_docente='PAD', dia_semana=4, hora_inicio=time(0,0), hora_fin=time(0,0), duracion_horas=4.0, tipo='Plataforma Asincrónica', modalidad='Asincrónico (PEDCO)', es_sincronico=False)
    db.session.add_all([b_rd1, b_rd2, b_rd3])

    # Ejemplo de Ramiro: PAD en Programación Estática y AYP en Automatización y Scripting
    b_pelw1 = BloqueHorario(asignatura=tudw_pelw, espacio_fisico=s2, profesor=p_ramiro, rol_docente='PAD', dia_semana=0, hora_inicio=time(16,0), hora_fin=time(19,0), duracion_horas=3.0, tipo='Taller', modalidad='Presencial', es_sincronico=True, observaciones='Teoría / Taller - Prof. Ramiro García Poggi (PAD)')
    b_pelw2 = BloqueHorario(asignatura=tudw_pelw, espacio_fisico=s1, profesor=p_ramiro, rol_docente='PAD', dia_semana=3, hora_inicio=time(17,0), hora_fin=time(19,0), duracion_horas=2.0, tipo='Taller', modalidad='Presencial', es_sincronico=True, observaciones='Práctica - Prof. Ramiro García Poggi (PAD)')
    b_pelw3 = BloqueHorario(asignatura=tudw_pelw, espacio_fisico=None, profesor=p_ramiro, rol_docente='PAD', dia_semana=4, hora_inicio=time(0,0), hora_fin=time(0,0), duracion_horas=3.0, tipo='Plataforma Asincrónica', modalidad='Asincrónico (PEDCO)', es_sincronico=False)
    db.session.add_all([b_pelw1, b_pelw2, b_pelw3])

    b_ays1 = BloqueHorario(asignatura=tuassl_ays, espacio_fisico=s2, profesor=p_ramiro, rol_docente='AYP', dia_semana=2, hora_inicio=time(17,0), hora_fin=time(19,0), duracion_horas=2.0, tipo='Práctica', modalidad='Presencial', es_sincronico=True, observaciones='Práctica / Scripting - Ayudante Ramiro García Poggi (AYP)')
    db.session.add(b_ays1)

    b_cbd1 = BloqueHorario(asignatura=tudw_cbd, espacio_fisico=None, profesor=p_corujo, rol_docente='PAD', dia_semana=1, hora_inicio=time(18,0), hora_fin=time(20,0), duracion_horas=2.0, tipo='Teoría', modalidad='Virtual', es_sincronico=True)
    b_cbd2 = BloqueHorario(asignatura=tudw_cbd, espacio_fisico=s1, profesor=p_corujo, rol_docente='PAD', dia_semana=2, hora_inicio=time(19,0), hora_fin=time(21,0), duracion_horas=2.0, tipo='Práctica', modalidad='Híbrido', es_sincronico=True)
    db.session.add_all([b_cbd1, b_cbd2])

    b_ext1 = BloqueHorario(asignatura=ext_est, espacio_fisico=s1, profesor=p_daher, rol_docente='PAD', dia_semana=1, hora_inicio=time(13,0), hora_fin=time(15,0), duracion_horas=2.0, tipo='Bloqueo Externo', modalidad='Bloqueo Aula', es_sincronico=True, es_bloqueo_externo=True, observaciones='Reserva Externa: Estadística Aplicada')
    b_ext2 = BloqueHorario(asignatura=ext_est, espacio_fisico=s2, profesor=p_daher, rol_docente='PAD', dia_semana=3, hora_inicio=time(15,30), hora_fin=time(18,30), duracion_horas=3.0, tipo='Bloqueo Externo', modalidad='Bloqueo Aula', es_sincronico=True, es_bloqueo_externo=True, observaciones='Reserva Externa: Estadística Aplicada')
    b_ext3 = BloqueHorario(asignatura=ext_eagr, espacio_fisico=a18, profesor=p_daher, rol_docente='PAD', dia_semana=3, hora_inicio=time(18,0), hora_fin=time(21,0), duracion_horas=3.0, tipo='Bloqueo Externo', modalidad='Bloqueo Aula', es_sincronico=True, es_bloqueo_externo=True, observaciones='Reserva Externa: Estadística Agropecuaria')
    b_ext4 = BloqueHorario(asignatura=ext_mat1, espacio_fisico=a21, dia_semana=2, hora_inicio=time(15,0), hora_fin=time(18,0), duracion_horas=3.0, tipo='Bloqueo Externo', modalidad='Bloqueo Aula', es_sincronico=True, es_bloqueo_externo=True, observaciones='Reserva Externa: Matemática 1')
    b_ext5 = BloqueHorario(asignatura=ext_mat1, espacio_fisico=a21, dia_semana=4, hora_inicio=time(15,0), hora_fin=time(18,0), duracion_horas=3.0, tipo='Bloqueo Externo', modalidad='Bloqueo Aula', es_sincronico=True, es_bloqueo_externo=True, observaciones='Reserva Externa: Matemática 1')
    
    db.session.add_all([b_ext1, b_ext2, b_ext3, b_ext4, b_ext5])

    db.session.commit()
    print("✅ Base de datos poblada exitosamente con vinculaciones usuario-profesor.")
