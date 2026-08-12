# 📊 Esquema de Base de Datos — Sistema de Gestión de Horarios y Aulas

**Versión del esquema:** 0.1.20260812  
**Última actualización:** 2026-08-12  
**Motor:** MariaDB 11.4 / MySQL 8 (compatible) — SQLite 3 en desarrollo local

---

## 🗂️ Diagrama de Tablas

```
┌─────────────────┐       ┌─────────────────┐
│  users          │       │  configuracion   │
│  (auth/roles)   │       │  _sistema        │
└──────┬──────────┘       └──────────────────┘
       │
       │ 1:1 (profesor_id)
       ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  profesores     │◄──────│  asignaturas     │       │  espacios_       │
│  (docentes)     │  1:N  │  (materias)      │       │  fisicos         │
└──────┬──────────┘       └───┬──────┬────────┘       │  (aulas/labs)   │
       │                      │      │                └────────┬────────┘
       │                      │      │                         │ 1:N
       │                      │      │                         ▼
       │                      │      │                ┌─────────────────┐
       │                      │      └───────────────►│  bloques_       │
       │                      │                         │  horarios       │
       │                      │                         └─────────────────┘
       │                      │
       │                      │ N:M (asignatura_ayps)
       │                      │
       ▼                      ▼
┌─────────────────┐       ┌─────────────────┐
│  auditoria      │       │  solicitudes_   │
│  (log cambios)  │       │  cambio          │
└─────────────────┘       └─────────────────┘
```

---

## 📋 Detalle de Tablas

### 1. `configuracion_sistema` — Configuración Global del Sistema

| Columna              | Tipo            | Restricciones            | Descripción                                              |
|----------------------|-----------------|--------------------------|----------------------------------------------------------|
| `id`                 | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                      |
| `congelado`          | BOOLEAN         | NOT NULL, DEFAULT FALSE  | Indica si el sistema está congelado (sin ediciones)     |
| `motivo_congelacion` | VARCHAR(250)    | NULL                     | Motivo textuel de la congelación                         |
| `congelado_por`      | INTEGER         | FK → users.id, NULL      | ID del usuario que congeló el sistema                   |
| `congelado_fecha`    | DATETIME        | NULL                     | Fecha/hora de la congelación                            |
| `actualizado_fecha`  | DATETIME        | DEFAULT now(), on update | Última fecha de actualización de la fila                |

---

### 2. `users` — Usuarios y Roles de Autenticación

| Columna             | Tipo           | Restricciones              | Descripción                                               |
|---------------------|----------------|----------------------------|-----------------------------------------------------------|
| `id`                | INTEGER        | PK, AUTO_INCREMENT         | Identificador único                                       |
| `username`          | VARCHAR(64)    | UNIQUE, NOT NULL, INDEX    | Nombre de usuario                                         |
| `email`             | VARCHAR(120)   | UNIQUE, NOT NULL           | Correo electrónico                                        |
| `password_hash`     | VARCHAR(256)   | NOT NULL                   | Hash de contraseña (Werkzeug)                             |
| `nombre_completo`   | VARCHAR(120)   | NOT NULL                   | Nombre y apellido                                         |
| `role`              | VARCHAR(20)    | NOT NULL, DEFAULT 'alumno' | Rol: `admin`, `gestor_aulas`, `docente`, `alumno`        |
| `profesor_id`       | INTEGER        | FK → profesores.id, NULL   | Vinculación opcional a entidad Profesor                   |
| `created_at`        | DATETIME       | DEFAULT UTC now()          | Fecha de creación                                         |

**Relaciones:**
- `profesor_id` → `profesores.id` (1:1 opcional)

---

### 3. `profesores` — Catálogo de Docentes

| Columna                | Tipo           | Restricciones           | Descripción                                              |
|------------------------|----------------|-------------------------|----------------------------------------------------------|
| `id`                   | INTEGER        | PK, AUTO_INCREMENT      | Identificador único                                      |
| `nombre_completo`      | VARCHAR(120)   | NOT NULL                | Nombre completo del docente                              |
| `categoria_habitual`   | VARCHAR(20)    | DEFAULT 'PAD'           | Categoría habitual: `PAD` o `AYP`                        |
| `email`                | VARCHAR(120)   | NULL                    | Correo institucional (para auto-vinculación OAuth)       |

**Relaciones:**
- `id` → `users.profesor_id` (1:1, inversa)
- `id` → `asignaturas.profesor_pad_id` (1:N, como PAD)
- `id` → `asignatura_ayps.profesor_id` (N:M, como AYP)
- `id` → `bloques_horarios.profesor_id` (1:N)

---

### 4. `carreras` — Carreras / Planes de Estudio

| Columna          | Tipo            | Restricciones            | Descripción                                              |
|------------------|-----------------|--------------------------|----------------------------------------------------------|
| `id`             | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                      |
| `codigo`         | VARCHAR(10)     | UNIQUE, NOT NULL         | Código: TUASSL, TUDW, EXTERNA                            |
| `nombre`         | VARCHAR(150)    | NOT NULL                 | Nombre de la carrera                                     |
| `descripcion`    | TEXT            | NULL                     | Descripción libre                                         |

**Relaciones:**
- `id` → `asignaturas.carrera_id` (1:N)

---

### 5. `asignaturas` — Materias / Asignaturas

| Columna                    | Tipo           | Restricciones               | Descripción                                                  |
|----------------------------|----------------|-----------------------------|--------------------------------------------------------------|
| `id`                       | INTEGER        | PK, AUTO_INCREMENT          | Identificador único                                          |
| `carrera_id`               | INTEGER        | FK → carreras.id, NOT NULL  | Carrera a la que pertenece                                   |
| `anio_cursada`             | INTEGER        | NOT NULL                    | Año de cursada (1, 2, 3)                                    |
| `cuatrimestre`             | INTEGER        | NOT NULL                    | 1 o 2                                                        |
| `codigo`                   | VARCHAR(20)    | NULL                        | Código de la materia                                         |
| `nombre`                   | VARCHAR(150)   | NOT NULL                    | Nombre de la asignatura                                      |
| `carga_horaria_semanal`    | INTEGER        | NOT NULL, DEFAULT 8         | Carga horaria total semanal                                  |
| `profesor_cargo`           | VARCHAR(150)   | NULL                        | Texto libre / legacy del cargo                               |
| `es_externa`               | BOOLEAN        | NOT NULL, DEFAULT FALSE     | Si es materia externa (bloqueo externo)                     |

**Relaciones:**
- `carrera_id` → `carreras.id` (N:1)
- `profesor_pad_id` → `profesores.id` (N:1, único PAD)
- M:N con `profesores` vía tabla `asignatura_ayps` (múltiples AYPs)
- `id` → `bloques_horarios.asignatura_id` (1:N)

---

### 6. `asignatura_ayps` — Tabla Intermedia PAD/AYP

Tabla de unión para la relación N:M entre `asignaturas` y `profesores` (AYPs).

| Columna          | Tipo       | Restricciones                         | Descripción                           |
|------------------|------------|---------------------------------------|---------------------------------------|
| `asignatura_id`  | INTEGER    | FK → asignaturas.id, PK Parte         | Materia                               |
| `profesor_id`    | INTEGER    | FK → profesores.id, PK Parte          | Profesor AYP                          |

**Clave primaria compuesta:** `(asignatura_id, profesor_id)`

---

### 7. `espacios_fisicos` — Aulas y Laboratorios

| Columna          | Tipo            | Restricciones            | Descripción                                              |
|------------------|-----------------|--------------------------|----------------------------------------------------------|
| `id`             | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                      |
| `nombre`         | VARCHAR(80)     | UNIQUE, NOT NULL         | Nombre: Ej "Sala 1 (JCBrocca)"                          |
| `capacidad`      | INTEGER         | DEFAULT 30               | Capacidad de personas                                    |
| `es_laboratorio` | BOOLEAN         | DEFAULT FALSE            | Indica si es laboratorio de computación                  |
| `equipamiento`   | VARCHAR(200)    | DEFAULT 'Computadoras…'  | Descripción del equipamiento                             |
| `activa`         | BOOLEAN         | DEFAULT TRUE             | Si el espacio está disponible                           |

**Relaciones:**
- `id` → `bloques_horarios.espacio_fisico_id` (1:N)

---

### 8. `bloques_horarios` — Bloques de Horario (Clases/Reservas)

| Columna               | Tipo           | Restricciones                | Descripción                                                  |
|-----------------------|----------------|------------------------------|--------------------------------------------------------------|
| `id`                  | INTEGER        | PK, AUTO_INCREMENT           | Identificador único                                          |
| `asignatura_id`       | INTEGER        | FK → asignaturas.id, NOT NULL | Materia asociada                                            |
| `espacio_fisico_id`   | INTEGER        | FK → espacios_fisicos.id, NULL | Aula/sala (NULL si es virtual/PEDCO)                       |
| `profesor_id`         | INTEGER        | FK → profesores.id, NULL      | Docente asignado a esta clase                               |
| `rol_docente`         | VARCHAR(20)    | NOT NULL, DEFAULT 'PAD'      | Rol del docente en esta clase: `PAD` o `AYP`               |
| `dia_semana`          | INTEGER        | NOT NULL                     | 0=Lunes … 4=Viernes                                         |
| `hora_inicio`         | TIME           | NOT NULL                     | Hora de inicio (formato HH:MM:SS)                          |
| `hora_fin`            | TIME           | NOT NULL                     | Hora de fin                                                  |
| `duracion_horas`      | FLOAT          | NOT NULL                     | Duración en horas (calculado)                              |
| `tipo`                | VARCHAR(50)    | NOT NULL, DEFAULT 'Teoría'   | Tipo: Teoría, Práctica, Taller, Consulta, etc.             |
| `modalidad`           | VARCHAR(50)    | NOT NULL, DEFAULT 'Presencial' | Presencial, Virtual, Híbrido, Asincrónico, Bloqueo Aula |
| `es_sincronico`       | BOOLEAN        | NOT NULL, DEFAULT TRUE       | Si la clase es sincrónica (presencial/videoconferencia)   |
| `es_bloqueo_externo`  | BOOLEAN        | NOT NULL, DEFAULT FALSE      | Si es bloqueo de aula externo                              |
| `observaciones`       | VARCHAR(250)   | NULL                         | Notas adicionales                                            |

**Relaciones:**
- `asignatura_id` → `asignaturas.id` (N:1)
- `espacio_fisico_id` → `espacios_fisicos.id` (N:1, opcional)
- `profesor_id` → `profesores.id` (N:1, opcional)
- `id` → `solicitudes_cambio.bloque_id` (1:1, opcional)

---

### 9. `auditoria` — Log de Auditoría

| Columna          | Tipo            | Restricciones            | Descripción                                                  |
|------------------|-----------------|--------------------------|--------------------------------------------------------------|
| `id`             | INTEGER         | PK, AUTO_INCREMENT       | Identificador único                                          |
| `usuario_id`     | INTEGER         | FK → users.id, NOT NULL   | Usuario que realizó la acción                               |
| `accion`         | VARCHAR(50)     | NOT NULL                 | Ej: `crear_bloque`, `editar_bloque`, `eliminar_bloque`…    |
| `entidad_tipo`   | VARCHAR(30)     | NULL                     | Tipo de entidad: `bloque`, `materia`, `profesor`, `usuario`|
| `entidad_id`     | INTEGER         | NULL                     | ID de la entidad afectada                                   |
| `detalles`       | TEXT            | NULL                     | JSON con los cambios detallados                             |
| `ip_address`     | VARCHAR(45)     | NULL                     | Dirección IP del cliente                                    |
| `created_at`     | DATETIME        | DEFAULT UTC now(), INDEX   | Fecha/hora de la acción                                     |

**Índice:** `created_at` (para consultas de logs recientes)

---

### 10. `solicitudes_cambio` — Workflow de Aprobación

| Columna                | Tipo           | Restricciones                | Descripción                                                  |
|------------------------|----------------|------------------------------|--------------------------------------------------------------|
| `id`                   | INTEGER        | PK, AUTO_INCREMENT           | Identificador único                                          |
| `bloque_id`            | INTEGER        | FK → bloques_horarios.id, NOT NULL | Bloque asociado a la solicitud                          |
| `profesor_id`          | INTEGER        | FK → profesores.id, NOT NULL  | Profesor que solicita el cambio                            |
| `descripcion`          | VARCHAR(500)   | NULL                         | Descripción del cambio solicitado                          |
| `estado`               | VARCHAR(20)    | NOT NULL, DEFAULT 'pendiente' | `pendiente`, `aprobada`, `rechazada`                      |
| `solicitado_por_id`    | INTEGER        | FK → users.id, NOT NULL       | Usuario que solicitó                                       |
| `aprobado_por_id`      | INTEGER        | FK → users.id, NULL           | Administrador que aprobó/rechazó                          |
| `creada_en`            | DATETIME       | DEFAULT UTC now()             | Fecha de creación                                          |
| `aprobada_en`          | DATETIME       | NULL                          | Fecha de aprobación/rechazo                               |
| `observaciones_admin`  | VARCHAR(500)   | NULL                          | Observaciones del administrador                           |

---

## 🔗 Relaciones Resumidas

| Tabla A              | Relación | Tabla B              | Tipo        |
|----------------------|----------|----------------------|-------------|
| `users`              | →        | `profesores`         | 1:1 (opcional) |
| `users`              | →        | `configuracion_sistema` | N:1 (congelado_por) |
| `profesores`         | →        | `asignaturas`        | 1:N (como PAD) |
| `profesores` ⋈ `asignatura_ayps` ⋈ `asignaturas` | → | — | N:M (como AYP) |
| `carreras`           | →        | `asignaturas`        | 1:N        |
| `asignaturas`        | →        | `bloques_horarios`  | 1:N        |
| `espacios_fisicos`   | →        | `bloques_horarios`  | 1:N        |
| `bloques_horarios`   | →        | `solicitudes_cambio`| 1:1 (opcional) |
| `users`              | →        | `auditoria`         | 1:N        |

---

## 🔄 Notas para Migraciones de Versiones

### 0.1.20260812 → Próxima versión

**Tablas existentes (sin modificar):**  
Todas las tablas listadas arriba son estables. Para agregar columnas:
1. Usar `ALTER TABLE ... ADD COLUMN ...` en migraciones upward.
2. Proveer un script downward reverso para rollback.
3. Nunca eliminar columnas sin migrar datos primero.

**Migraciones recomendadas:**
- SQL schema exportable desde MariaDB: `mysqldump --no-data sistema_horarios > schema_v01.sql`
- Para SQLite en desarrollo: `sqlite3 instance/sistema_horarios.db .schema > schema_v01.sql`
- Mantener un historial de cambios en `migrations/` con archivos `V001__descripición.sql`, `V002__...`, etc.

**Checkpoint de versión:**  
Al lanzar una nueva versión, exportar el esquema completo y actualizar este documento. El objetivo es poder reconstruir la base desde cero o migrar datos preservando la estructura.

---

## 📎 Anexo: Scripts Útiles

### Exportar esquema (MariaDB)
```bash
mysqldump -h localhost -P 3306 -u horarios -p --no-data sistema_horarios > db_schema_v01.sql
```

### Exportar esquema (SQLite — desarrollo)
```bash
sqlite3 instance/sistema_horarios.db .schema > db_schema_v01.sql
```

### Ver tablas y columnas (MariaDB)
```sql
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'sistema_horarios'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

### Ver foreign keys (MariaDB)
```sql
SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'sistema_horarios' AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, COLUMN_NAME;
```

---

*Documento generado para el Issue #4 — Sistema de Gestión de Horarios CURZAS (UNComa)*
