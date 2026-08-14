# 📊 Esquema de Base de Datos — Sistema de Gestión de Horarios y Aulas

**Versión del esquema:** 0.1.20260814  
**Última actualización:** 2026-08-14  
**Motor:** MariaDB 11.4 / MySQL 8 (compatible) — SQLite 3 en desarrollo local

---

## 🗂️ Diagrama Entidad-Relación

```
┌─────────────────┐       ┌────────────────────────┐
│  users          │       │  configuracion_sistema │
│  (auth/roles)   │       │  (estado congelado)    │
└──────┬──────────┘       └────────────────────────┘
       │
       │ 1:1 opcional (profesor_id)
       ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  profesores     │◄──────│  asignaturas     │       │  espacios_       │
│  (docentes)     │  1:N  │  (materias)      │       │  fisicos         │
└──────┬──────────┘(PAD)  └───┬──────┬────────┘       │  (aulas/labs)   │
       │                      │      │                └────────┬────────┘
       │                      │      │                         │ 1:N
       │ N:M                  │      │                         ▼
       │ (asignatura_ayps)    │      │                ┌─────────────────┐
       ├──────────────────────┘      └───────────────►│  bloques_       │
       │                                              │  horarios       │
       │ 1:N                                          └────────┬────────┘
       ▼                                                       │
┌─────────────────┐       ┌─────────────────┐                  │ 1:1
│  auditoria      │       │  solicitudes_   │◄─────────────────┘
│  (log cambios)  │       │  cambio         │
└─────────────────┘       └─────────────────┘
```

---

## 📋 Detalle de Tablas

### 1. `configuracion_sistema` — Configuración Global del Sistema

| Columna              | Tipo            | Restricciones            | Descripción                                              |
|----------------------|-----------------|--------------------------|----------------------------------------------------------|
| `id`                 | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                      |
| `congelado`          | BOOLEAN         | NOT NULL, DEFAULT FALSE  | Indica si el sistema está congelado (sin ediciones)     |
| `motivo_congelacion` | VARCHAR(250)    | NULL                     | Motivo textual de la congelación                         |
| `congelado_por`      | INTEGER         | FK → users.id, NULL      | ID del usuario administrador que congeló el sistema      |
| `congelado_fecha`    | DATETIME        | NULL                     | Fecha/hora de la congelación                            |
| `actualizado_fecha`  | DATETIME        | DEFAULT now(), on update | Última fecha de actualización de la fila                |

---

### 2. `users` — Usuarios y Roles de Autenticación

| Columna             | Tipo           | Restricciones              | Descripción                                               |
|---------------------|----------------|----------------------------|-----------------------------------------------------------|
| `id`                | INTEGER        | PK, AUTO_INCREMENT         | Identificador único                                       |
| `username`          | VARCHAR(64)    | UNIQUE, NOT NULL, INDEX    | Nombre de usuario para login local                        |
| `email`             | VARCHAR(120)   | UNIQUE, NOT NULL           | Correo electrónico (utilizado en Google OAuth 2.0)        |
| `password_hash`     | VARCHAR(256)   | NOT NULL                   | Hash de contraseña (Werkzeug)                             |
| `nombre_completo`   | VARCHAR(120)   | NOT NULL                   | Nombre y apellido del usuario                             |
| `role`              | VARCHAR(20)    | NOT NULL, DEFAULT 'alumno' | Rol: `admin`, `gestor_aulas`, `gestor`, `docente`, `alumno`|
| `profesor_id`       | INTEGER        | FK → profesores.id, NULL   | Vinculación opcional a entidad Profesor                   |
| `created_at`        | DATETIME       | DEFAULT UTC now()          | Fecha de creación de la cuenta                            |

**Relaciones:**
- `profesor_id` → `profesores.id` (1:1 opcional)
- `id` → `auditoria.usuario_id` (1:N)

---

### 3. `profesores` — Catálogo de Docentes

| Columna                | Tipo           | Restricciones           | Descripción                                              |
|------------------------|----------------|-------------------------|----------------------------------------------------------|
| `id`                   | INTEGER        | PK, AUTO_INCREMENT      | Identificador único                                      |
| `nombre_completo`      | VARCHAR(120)   | NOT NULL                | Nombre completo del docente                              |
| `categoria_habitual`   | VARCHAR(20)    | DEFAULT 'PAD'           | Categoría habitual: `PAD` (Adjunto) o `AYP` (Ayudante)  |
| `email`                | VARCHAR(120)   | NULL                    | Correo institucional (para auto-vinculación con OAuth)   |

**Relaciones:**
- `id` → `users.profesor_id` (1:1, inversa)
- `id` → `asignaturas.profesor_pad_id` (1:N, como PAD de la materia)
- `id` → `asignatura_ayps.profesor_id` (N:M, como AYP de la materia)
- `id` → `bloques_horarios.profesor_id` (1:N)

---

### 4. `carreras` — Carreras / Planes de Estudio

| Columna          | Tipo            | Restricciones            | Descripción                                              |
|------------------|-----------------|--------------------------|----------------------------------------------------------|
| `id`             | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                      |
| `codigo`         | VARCHAR(10)     | UNIQUE, NOT NULL         | Código: `TUASSL`, `TUDW`, `EXTERNA`                      |
| `nombre`         | VARCHAR(150)    | NOT NULL                 | Nombre oficial de la carrera                             |
| `descripcion`    | TEXT            | NULL                     | Descripción u ordenanza ministerial                       |

**Relaciones:**
- `id` → `asignaturas.carrera_id` (1:N, cascade delete)

---

### 5. `asignaturas` — Materias y Asignaturas

| Columna                    | Tipo           | Restricciones               | Descripción                                                  |
|----------------------------|----------------|-----------------------------|--------------------------------------------------------------|
| `id`                       | INTEGER        | PK, AUTO_INCREMENT          | Identificador único                                          |
| `carrera_id`               | INTEGER        | FK → carreras.id, NOT NULL  | Carrera a la que pertenece                                   |
| `anio_cursada`             | INTEGER        | NOT NULL                    | Año de cursada (1, 2, 3)                                    |
| `cuatrimestre`             | INTEGER        | NOT NULL                    | 1 o 2 Cuatrimestre                                           |
| `codigo`                   | VARCHAR(20)    | NULL                        | Código identificador de la materia                           |
| `nombre`                   | VARCHAR(150)   | NOT NULL                    | Nombre de la asignatura                                      |
| `carga_horaria_semanal`    | INTEGER        | NOT NULL, DEFAULT 8         | Carga horaria total semanal (reloj)                         |
| `profesor_cargo`           | VARCHAR(150)   | NULL                        | Texto libre / legacy del cargo                               |
| `es_externa`               | BOOLEAN        | NOT NULL, DEFAULT FALSE     | Indica si es materia externa (bloqueo externo de aula)       |
| `profesor_pad_id`          | INTEGER        | FK → profesores.id, NULL    | Profesor Adjunto / Titular (PAD) asignado                    |

**Relaciones:**
- `carrera_id` → `carreras.id` (N:1)
- `profesor_pad_id` → `profesores.id` (N:1, único PAD)
- N:M con `profesores` vía tabla intermedia `asignatura_ayps` (múltiples AYPs)
- `id` → `bloques_horarios.asignatura_id` (1:N, cascade delete)

---

### 6. `asignatura_ayps` — Tabla Intermedia PAD/AYP (M:N)

Tabla de unión para la relación N:M entre `asignaturas` y `profesores` en rol de Ayudantes de Primera (`AYP`).

| Columna          | Tipo       | Restricciones                         | Descripción                           |
|------------------|------------|---------------------------------------|---------------------------------------|
| `asignatura_id`  | INTEGER    | FK → asignaturas.id, PK Compuesta     | Identificador de la Materia           |
| `profesor_id`    | INTEGER    | FK → profesores.id, PK Compuesta      | Identificador del Docente AYP         |

**Clave primaria compuesta:** `(asignatura_id, profesor_id)`

---

### 7. `espacios_fisicos` — Aulas y Laboratorios de Informática

| Columna          | Tipo            | Restricciones            | Descripción                                              |
|------------------|-----------------|--------------------------|----------------------------------------------------------|
| `id`             | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                      |
| `nombre`         | VARCHAR(80)     | UNIQUE, NOT NULL         | Ej: *"Sala 1 (JCBrocca)"*, *"Sala 2 (JColombo)"*         |
| `capacidad`      | INTEGER         | DEFAULT 30               | Capacidad máxima de estudiantes                          |
| `es_laboratorio` | BOOLEAN         | DEFAULT FALSE            | Indica si es laboratorio de computación                  |
| `equipamiento`   | VARCHAR(200)    | DEFAULT 'Computadoras…'  | Descripción del equipamiento y conectividad              |
| `activa`         | BOOLEAN         | DEFAULT TRUE             | Estado operativo del espacio (Activa / Inactiva)         |

**Relaciones:**
- `id` → `bloques_horarios.espacio_fisico_id` (1:N)

---

### 8. `bloques_horarios` — Bloques Horarios de Clases y Reservas

| Columna               | Tipo           | Restricciones                | Descripción                                                  |
|-----------------------|----------------|------------------------------|--------------------------------------------------------------|
| `id`                  | INTEGER        | PK, AUTO_INCREMENT           | Identificador único                                          |
| `asignatura_id`       | INTEGER        | FK → asignaturas.id, NOT NULL | Materia a la que corresponde la clase                        |
| `espacio_fisico_id`   | INTEGER        | FK → espacios_fisicos.id, NULL | Aula física (NULL para modalidad Virtual o PEDCO)            |
| `profesor_id`         | INTEGER        | FK → profesores.id, NULL      | Docente a cargo en esta clase                                |
| `rol_docente`         | VARCHAR(20)    | NOT NULL, DEFAULT 'PAD'      | Rol docente en este bloque: `PAD` (Teoría) o `AYP` (Práctica)|
| `dia_semana`          | INTEGER        | NOT NULL                     | 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes         |
| `hora_inicio`         | TIME           | NOT NULL                     | Hora de inicio (formato HH:MM:SS)                            |
| `hora_fin`            | TIME           | NOT NULL                     | Hora de finalización                                         |
| `duracion_horas`      | FLOAT          | NOT NULL                     | Duración en horas reloj                                      |
| `tipo`                | VARCHAR(50)    | NOT NULL, DEFAULT 'Teoría'   | Teoría, Práctica, Taller, Consulta, etc.                     |
| `modalidad`           | VARCHAR(50)    | NOT NULL, DEFAULT 'Presencial'| Presencial, Virtual, Híbrido, Asincrónico (PEDCO), Bloqueo Aula|
| `es_sincronico`       | BOOLEAN        | NOT NULL, DEFAULT TRUE       | Indica si computa como carga sincrónica (>50%)               |
| `es_bloqueo_externo`  | BOOLEAN        | NOT NULL, DEFAULT FALSE      | Si es reserva física externa sin afectar horas sincrónicas  |
| `observaciones`       | VARCHAR(250)   | NULL                         | Anotaciones pedagógicas o requerimientos áulicos             |

**Relaciones:**
- `asignatura_id` → `asignaturas.id` (N:1)
- `espacio_fisico_id` → `espacios_fisicos.id` (N:1, opcional)
- `profesor_id` → `profesores.id` (N:1, opcional)
- `id` → `solicitudes_cambio.bloque_id` (1:1, opcional)

---

### 9. `auditoria` — Registro Inmutable de Trazabilidad

| Columna          | Tipo            | Restricciones            | Descripción                                                  |
|------------------|-----------------|--------------------------|--------------------------------------------------------------|
| `id`             | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                          |
| `usuario_id`     | INTEGER         | FK → users.id, NOT NULL   | Usuario responsable de la acción                             |
| `accion`         | VARCHAR(50)     | NOT NULL                 | Ej: `crear_bloque`, `editar_bloque`, `congelar_sistema`…     |
| `entidad_tipo`   | VARCHAR(30)     | NULL                     | Tipo de entidad: `bloque`, `materia`, `profesor`, `usuario`  |
| `entidad_id`     | INTEGER         | NULL                     | ID del registro afectado                                     |
| `detalles`       | TEXT            | NULL                     | Estructura JSON con los valores anteriores y posteriores     |
| `ip_address`     | VARCHAR(45)     | NULL                     | Dirección IP de origen                                       |
| `created_at`     | DATETIME        | DEFAULT UTC now(), INDEX | Marca temporal UTC del evento                                |

**Índice:** `created_at` (optimización de consultas cronológicas y filtros de auditoría).

---

### 10. `solicitudes_cambio` — Workflow de Aprobación de Cambios

| Columna                | Tipo           | Restricciones                | Descripción                                                  |
|------------------------|----------------|------------------------------|--------------------------------------------------------------|
| `id`                   | INTEGER        | PK, AUTO_INCREMENT           | Identificador único                                          |
| `bloque_id`            | INTEGER        | FK → bloques_horarios.id, NOT NULL | Bloque horario objetivo del cambio                      |
| `profesor_id`          | INTEGER        | FK → profesores.id, NOT NULL  | Docente solicitante                                          |
| `descripcion`          | VARCHAR(500)   | NULL                         | Justificación o descripción del pedido                       |
| `estado`               | VARCHAR(20)    | NOT NULL, DEFAULT 'pendiente' | `pendiente`, `aprobada`, `rechazada`                         |
| `solicitado_por_id`    | INTEGER        | FK → users.id, NOT NULL       | Cuenta de usuario que inició la solicitud                   |
| `aprobado_por_id`      | INTEGER        | FK → users.id, NULL           | Administrador o Gestor que evaluó la solicitud               |
| `creada_en`            | DATETIME       | DEFAULT UTC now()             | Fecha/hora de creación                                       |
| `aprobada_en`          | DATETIME       | NULL                          | Fecha/hora de resolución                                     |
| `observaciones_admin`  | VARCHAR(500)   | NULL                          | Motivo de aprobación o rechazo                               |

---

## 🔗 Resumen de Relaciones y Cardinalidades

| Entidad Origen       | Cardinalidad | Entidad Destino        | Clave Foránea / Vínculo |
|:---------------------|:------------:|:-----------------------|:------------------------|
| `users`              | 1:1          | `profesores`           | `users.profesor_id`     |
| `users`              | N:1          | `configuracion_sistema`| `configuracion_sistema.congelado_por` |
| `carreras`           | 1:N          | `asignaturas`          | `asignaturas.carrera_id`|
| `profesores` (PAD)   | 1:N          | `asignaturas`          | `asignaturas.profesor_pad_id` |
| `profesores` (AYP)   | N:M          | `asignaturas`          | `asignatura_ayps`       |
| `asignaturas`        | 1:N          | `bloques_horarios`     | `bloques_horarios.asignatura_id` |
| `espacios_fisicos`   | 1:N          | `bloques_horarios`     | `bloques_horarios.espacio_fisico_id` |
| `profesores`         | 1:N          | `bloques_horarios`     | `bloques_horarios.profesor_id` |
| `users`              | 1:N          | `auditoria`            | `auditoria.usuario_id`  |
| `bloques_horarios`   | 1:1          | `solicitudes_cambio`   | `solicitudes_cambio.bloque_id` |

---

## 🔄 Notas para Migraciones de Esquema

1. **Evolución sin pérdidas**: Cualquier cambio de esquema en producción debe aplicar migraciones incrementales `ALTER TABLE ... ADD COLUMN ...`.
2. **Compatibilidad Dual**: El esquema está normalizado para funcionar idénticamente tanto en el motor de producción **MariaDB 11.4 / MySQL 8** como en entornos locales **SQLite 3** mediante SQLAlchemy ORM 2.0.

---

*Documento actualizado — Sistema de Gestión de Horarios y Aulas CURZAS (UNComa)*
