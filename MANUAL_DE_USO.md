# 📘 Manual de Uso y Guía del Usuario — Sistema de Gestión de Horarios y Aulas
**CURZAS — Universidad Nacional del Comahue (UNComa)**  
*Departamento de Ciencia y Tecnología*  
*Tecnicatura Universitaria en Administración de Sistemas y Software Libre (TUASSL)*  
*Tecnicatura Universitaria en Desarrollo Web (TUDW)*  
**Versión del Sistema:** v0.1 (Automatizada vía Git)

---

## 📌 1. Introducción y Propósito

El **Sistema de Gestión de Horarios y Aulas** es una plataforma web desarrollada especialmente para el Complejo Universitario Zona Atlántica y Sur (CURZAS) de la Universidad Nacional del Comahue.

Su objetivo principal es centralizar, planificar, validar y visualizar la distribución semanal de materias y el uso de los espacios físicos (laboratorios de informática y aulas comunes), garantizando el estricto cumplimiento de la reglamentación académica vigente (carga sincrónica >50%, aislamiento por cuatrimestre y prevención de colisiones) y optimizando la coordinación entre docentes, gestores de aulas, administradores y estudiantes.

---

## 🔑 2. Perfiles de Usuario, Credenciales e Inicio con OAuth 2.0

### 2.1. Matriz de Roles y Cuentas Locales de Demostración

| Rol / Perfil | Nombre de Usuario | Correo Institucional | Contraseña | Descripción de Permisos y Acceso |
| :--- | :--- | :--- | :--- | :--- |
| **Público / Estudiantes** | *(Sin login)* | *(Sin login)* | *(Sin login)* | **Consulta pública de solo lectura**. Acceso libre a la grilla semanal, filtros multicriterio, tarjetas flotantes informativas (*popovers*) y exportación/impresión ecológica en PDF. |
| **Alumno Autenticado** | `alumno` | `alumno@curza.com.ar` | `alumno123` | Consulta personalizada de horarios, materias y aulas de cursada. |
| **Profesor / Docente** | `docente` | `docente@curza.com.ar` | `docente123` | Consulta y **reubicación interactiva Drag & Drop de sus propias clases asignadas**, botón de deshacer (*Undo*) y visualización de planes de estudio. |
| **Gestor de Aulas** | `gestor` | `gestor.aulas@curza.com.ar` | `gestor123` | Control total de la grilla horaria (reubicación Drag & Drop de cualquier clase), ABM de materias, clases y bloqueos externos de aulas, administración de solicitudes y consulta de auditoría. |
| **Administrador** | `admin` | `admin@curza.com.ar` | `admin123` | **Acceso total y configuración del sistema**: Alta, edición y baja de usuarios y docentes, gestión completa del catálogo de aulas, **congelamiento y descongelamiento global del sistema** y acceso al registro inmutable de auditoría. |

---

### 2.2. Autenticación Institucional OAuth 2.0 (`@curza.com.ar`)

El sistema cuenta con integración nativa para **Inicio de Sesión Unificado con Google Workspace / OAuth 2.0** utilizando cuentas de correo institucional `@curza.com.ar`.

#### Configuración de OAuth 2.0 en Google Cloud / Workspace
Para habilitar el botón **`Google / UNComa`** en la pantalla de inicio de sesión (`/login`):

1. **Crear Credenciales en Google Cloud Console**:
   - Ingrese a la [Consola de Google Cloud](https://console.cloud.google.com/apis/credentials).
   - En **Pantalla de Consentimiento de OAuth**, configure el dominio institucional `curza.com.ar`.
   - En **Credenciales** $\rightarrow$ **ID de cliente de OAuth 2.0** $\rightarrow$ **Aplicación web**, configure las URIs de redireccionamiento autorizadas:
     - **Desarrollo local**: `http://localhost:5000/auth/callback`
     - **Servidor / Producción**: `https://horarios.curza.com.ar/auth/callback` (o según el valor de `BASE_URL`)

> [!IMPORTANT]
> **Coincidencia Exacta de URIs de Redireccionamiento (`redirect_uri_mismatch`)**:
> - Google exige una **coincidencia estricta** entre la URI enviada por la aplicación y la registrada en Google Cloud Console.
> - La URI obligatoria es: `https://horarios.curza.com.ar/auth/callback` (incluyendo `/auth/callback`).
> - El administrador debe registrar esta URI exacta en Google Cloud Console dentro de **“URIs de redireccionamiento autorizados”**. No basta con modificar variables locales o archivos JSON.
> - Para más detalles, consulte la [Documentación Oficial de Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2/web-server).

2. **Variables de Entorno en el Servidor (Docker / Podman / Linux)**:
   Configure las siguientes variables en su archivo de entorno (`.env` o compose):
   - `BASE_URL`: `horarios.curza.com.ar` (o la URL base configurada para la instancia).
   - `OAUTH_CLIENT_ID`: `xxxxxx-xxxxxx.apps.googleusercontent.com`
   - `OAUTH_CLIENT_SECRET`: `GOCSPX-xxxxxxxxxxxxxx`

3. **Auto-vinculación Automática de Docentes**:
   - Cuando un docente inicia sesión por primera vez con su correo institucional (`ej: docente@curza.com.ar`), el sistema detecta automáticamente la cuenta, la vincula con el registro del docente en la base de datos y le otorga permisos inmediatos de autogestión sobre sus clases asignadas.

---

## ❄️ 3. Guía de Uso: Módulo de Congelamiento del Sistema (*Sistema Congelado*)

El módulo de congelamiento permite bloquear de forma global la modificación de horarios, materias, docentes y aulas una vez finalizado el período de planificación o durante instancias de revisión oficial por parte de las autoridades académicas.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ❄️ SISTEMA CONGELADO — No se permiten cambios                              │
│ Congelado por: admin (admin@curza.com.ar) | Motivo: Cierre de planificación │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1. Propósito y Alcance
- **Protección de la Planificación**: Evita alteraciones no autorizadas, movimientos accidentales por Drag & Drop o borrados durante el período lectivo en curso.
- **Transparencia**: El sistema continúa plenamente accesible en **modo de solo lectura** para que docentes y alumnos consulten la grilla, descarguen horarios o impriman en PDF.

### 3.2. ¿Quién puede Congelar y Descongelar?
- **Exclusivo para Administradores**: Únicamente los usuarios con rol `admin` disponen de los controles y permisos necesarios para cambiar el estado de congelación.

### 3.3. Cómo Congelar el Sistema
1. Inicie sesión con una cuenta de **Administrador** (`admin`).
2. Diríjase al **Dashboard** (`/dashboard`).
3. En la barra superior de acciones, haga clic en el botón **`❄️ CONGELAR SISTEMA`**.
4. Se abrirá una ventana modal de confirmación solicitando un **Motivo de Congelación** (ej: *"Publicación oficial de horarios 2° Cuatrimestre 2026"*).
5. Presione **Confirmar Congelamiento**.

### 3.4. Efectos Inmediatos del Congelamiento en la Aplicación
Al activarse el congelamiento:
- **Banner Global de Alerta**: Se muestra un banner distintivo color ámbar/dorado en la parte superior de todas las páginas para usuarios autenticados indicando quién congeló el sistema, la fecha/hora y el motivo especificado.
- **Grilla Horaria (`/horarios`)**: La función de arrastrar y soltar (*Drag & Drop*) y el botón de deshacer quedan automáticamente deshabilitados.
- **Bloqueo en Clases y Horarios (`/bloques/*`)**: Se impide crear nuevos bloques, editar existentes o eliminarlos.
- **Bloqueo en Materias (`/materias/*`)**: Se bloquea el alta, edición, eliminación y modificación de clases asociadas.
- **Bloqueo en Plantel Docente (`/profesores/*`)**: Se inhabilitan las altas, bajas y modificaciones de docentes.
- **Bloqueo en Aulas (`/aulas/*`)**: Se inhabilitan las altas y ediciones de espacios físicos.
- **Bloqueo en Bloqueos Externos (`/bloqueos_externos`)**: Se bloquea la creación y eliminación de reservas externas.
- **Protección a Nivel Backend (API & Formularios)**: Cualquier intento de envío de formulario o petición POST (`/api/bloque/<id>/mover`, `/api/bloque/<id>/deshacer`, etc.) es rechazado con respuesta HTTP `403 Forbidden` y un mensaje claro al usuario: *"El sistema está congelado. No se permiten cambios."*
- **Registro en Auditoría**: Se genera automáticamente un evento de auditoría (`congelar_sistema`) con la marca temporal, el usuario administrador y el motivo.

### 3.5. Cómo Descongelar el Sistema
1. Inicie sesión como **Administrador** (`admin`).
2. Diríjase al **Dashboard** (`/dashboard`).
3. En la barra superior, haga clic en el botón **`🔓 DESCONGELAR SISTEMA`**.
4. El sistema retornará instantáneamente al modo activo regular, habilitando nuevamente la edición para gestores y docentes, removiendo el banner global y registrando la acción en auditoría (`descongelar_sistema`).

---

## 📅 4. Guía de Uso: Grilla Horaria y Consulta Pública (Estudiantes y Docentes)

### 4.1. Acceso Libre a la Grilla Semanal
- Ingrese a la raíz del sistema (`/` o `/horarios`).
- La grilla organiza de lunes a viernes en franja de 8:00 a 23:00 hs todas las asignaturas activas.

### 4.2. Barra de Filtros Multicriterio
En la barra superior interactiva puede filtrar simultáneamente por:
- **Carrera**: Alternar entre *TUASSL* (Sistemas y Software Libre), *TUDW* (Desarrollo Web) o *Materias Externas*.
- **Cuatrimestre**: Filtrar por *1° Cuatrimestre* o *2° Cuatrimestre* (con aislamiento de reglas de solapamiento).
- **Profesor/a**: Seleccionar un docente específico para consultar su agenda semanal.
- **Aula / Sala**: Filtrar por espacio físico (*Sala 1 JCBrocca*, *Sala 2 JColombo*, *Aula 18*, etc.).
- **Modalidad**: Filtrar por clases *Presenciales*, *Virtuales*, *Híbridas* o *Asincrónicas (PEDCO)*.

### 4.3. Popover Informativo al Pasar el Cursor (*Hover*)
Al posicionar el cursor sobre cualquier bloque horario, se despliega una tarjeta flotante con la ficha técnica de la clase:
- Nombre de la Asignatura, Carrera, Año y Cuatrimestre.
- Horario de inicio/fin y cómputo de horas reloj.
- Docente a cargo con indicación de su categoría en la clase (**PAD** para teoría / **AYP** para práctica).
- Aula o laboratorio asignado y observaciones pedagógicas.
- En caso de existir advertencias, **explicación detallada del conflicto** (solapamiento de aula, cruce de docente o choque de cohorte).

### 4.4. Impresión Ecológica y Exportación PDF
- Presione el botón **`🖨️ Imprimir / PDF`** o el atajo de teclado `Ctrl + P`.
- La vista de impresión aplica una hoja de estilos de alto contraste en **blanco y negro con fondo 100% blanco y tipografía en negro puro**, eliminando fondos oscuros para **ahorrar tinta/tóner** e incorporando el membrete institucional formal de la UNComa - CURZAS.

---

## 🖐️ 5. Guía de Uso: Reubicación Interactiva Drag & Drop y Deshacer (Docentes y Gestores)

### 5.1. Mover Clases Arrastrando en la Grilla
1. Inicie sesión con su cuenta docente (`docente`) o gestor (`gestor` / `admin`).
2. En la grilla (`/horarios`), haga clic sobre el bloque horario y **arrástrelo directamente hacia el nuevo día y horario deseado**.
3. **Validación Anticonflicto en Tiempo Real**:
   - **Movimiento Válido**: Si la celda destino no genera cruces, el bloque se reubica inmediatamente y el sistema confirma el cambio mediante una notificación flotante verde.
   - **Conflicto Detectado**: Si el nuevo horario genera colisión de aula o solapamiento del docente, el movimiento es rechazado automáticamente y se despliega una notificación de error con el motivo específico.
   - **Sistema Congelado**: Si el sistema fue congelado por el administrador, el arrastre queda inhabilitado.

### 5.2. Botón de Deshacer Rápido (*Undo*)
- Al pasar el cursor sobre cualquier bloque de clase que tenga permisos para editar, aparecerá un botón circular de deshacer (**`↺`**).
- Al hacer clic, el sistema revierte instantáneamente la clase a su día y horario anterior mediante la API backend (`/api/bloque/<id>/deshacer`), revalidando las condiciones del aula y profesor.

---

## 📚 6. Guía de Uso: Gestión de Materias y Planes de Estudio (`/materias`)

### 6.1. Regla Normativa del >50% Sincrónico
Para las tecnicaturas TUASSL y TUDW, la reglamentación exige que la carga horaria sincrónica semanal ($H_{sinc}$) cumpla:
$$H_{sinc} \ge \left\lfloor \frac{H_{total}}{2} \right\rfloor + 1$$

En la tabla general de materias (`/materias`), el sistema calcula e indica automáticamente el estado de cada asignatura:
- 🟢 **Cumple (>50%)**: La materia alcanza o supera la cantidad de horas sincrónicas reglamentarias.
- 🟡 **Falta Xh sinc.**: La materia aún requiere programar horas sincrónicas para satisfacer el plan de estudios.

### 6.2. Panel Centralizado de Clases por Materia (`Editar Clases`)
- En la tabla de materias, cada fila cuenta con el botón **`Editar Clases`** (indicando la cantidad de clases asignadas).
- Al ingresar (`/materias/<id>/clases`), se presenta el panel específico de la asignatura:
  - **`+ Crear Clase`**: Abre el formulario de programación con la materia ya preseleccionada de forma automática.
  - **Editar**: Modificar el día, franja horaria (24hs), modalidad, aula o docente de una clase existente.
  - **Eliminar**: Dar de baja un bloque horario con confirmación de seguridad.
- Al editar los datos generales de la materia (`/materias/<id>/editar`), también se incluye al pie del formulario el listado integrado de clases para facilitar ajustes rápidos.

### 6.3. Eliminación Segura de Materias
- La eliminación de materias incluye confirmación de seguridad para prevenir pérdidas de datos accidentales en asignaturas con bloques horarios asociados.

---

## 🏫 7. Guía de Uso: Programación de Clases y Bloques Horarios (`/bloques/nuevo`)

1. Ingrese con perfil **Gestor** o **Administrador** y presione **`+ Nueva Clase / Reserva`**.
2. Complete los campos requeridos:
   - **Asignatura**: Materia a la que corresponde la clase.
   - **Profesor/a a Cargo**: Docente responsable.
   - **Rol en esta Clase**: Seleccione `PAD` (Profesor/Teoría) o `AYP` (Asistente/Práctica).
   - **Día y Horarios**: Día de la semana y horas de inicio y fin (formato 24hs).
   - **Modalidad**: Presencial, Virtual, Híbrido o Asincrónico PEDCO.
   - **Espacio Físico**: Selección del aula o laboratorio (si la modalidad lo requiere).
   - **Observaciones**: Indicaciones pedagógicas o requerimientos especiales.
3. Al guardar, el motor valida en backend la disponibilidad del aula y del docente antes de persistir los cambios.

---

## 🏛️ 8. Guía de Uso: Gestión Integral de Aulas y Espacios Físicos (`/aulas`)

El módulo de aulas (`/aulas`) permite al Administrador y Gestores mantener actualizado el inventario de espacios educativos:

1. **Catálogo de Espacios**:
   - Visualización de Laboratorios de Informática (*Sala 1 JCBrocca*, *Sala 2 JColombo*), Aulas comunes y Talleres.
   - Detalle de capacidad de estudiantes, tipo de espacio, ubicación y equipamiento disponible (proyectores, cantidad de computadoras, conectividad).
2. **Alta de Nueva Aula (`/aulas/nueva`)**:
   - Registro de nuevos espacios físicos con su capacidad y descripción.
3. **Edición Completa de Aula (`/aulas/<id>/editar`)**:
   - Actualización de nombres, tipo de aula, capacidad máxima y estado operativo (Activa / Inactiva).

---

## 🔒 9. Guía de Uso: Bloqueos de Aula Externos (`/bloqueos_externos`)

1. Ingrese a la sección **`Bloqueos Externos`**.
2. Permite reservar aulas físicas para materias pertenecientes a otras unidades académicas de la UNComa (Facultad de Economía, Ciencias Exactas, Posgrados) o eventos institucionales.
3. **Comportamiento**:
   - Ocupan visual y físicamente el aula en la grilla horaria para evitar solapamientos.
   - **No intervienen** en el cómputo de la regla del >50% sincrónico de las carreras del CURZAS.

---

## 🔍 10. Guía de Uso: Módulo de Auditoría y Trazabilidad (`/auditoria`)

Disponible para **Administradores** y **Gestores de Aulas**, este módulo garantiza la transparencia y trazabilidad absoluta de las operaciones realizadas en el sistema.

### 10.1. Registro Cronológico de Acciones
El sistema audita automáticamente eventos clave, incluyendo:
- `crear_bloque`, `editar_bloque`, `eliminar_bloque` (incluyendo movimientos por Drag & Drop y Deshacer).
- `congelar_sistema`, `descongelar_sistema` (con autor y motivo).
- `crear_materia`, `editar_materia`, `eliminar_materia`.
- `crear_profesor`, `editar_profesor`, `eliminar_profesor`.
- `crear_usuario`, `editar_usuario`, `eliminar_usuario`.

### 10.2. Filtros y Análisis Forense
- Filtro por tipo de acción realizada.
- Filtro por tipo de entidad afectada (*bloque*, *materia*, *profesor*, *usuario*, *configuración*).
- Filtro por usuario responsable.
- Visualización de fecha/hora exacta, dirección IP y comparación de datos previos vs. nuevos en formato estructurado.

---

## 📋 11. Guía de Uso: Solicitudes de Cambio (`/solicitudes`)

1. Permite gestionar solicitudes formales de modificación de días, horarios o aulas.
2. Los Gestores de Aulas pueden revisar las solicitudes pendientes, analizar la disponibilidad de los espacios y proceder a su **Aprobación** o **Rechazo** motivado.

---

## 👥 12. Guía de Uso: Administración de Docentes y Usuarios (`/profesores` y `/usuarios`)

- **Plantel Docente (`/profesores`)**:
  - Alta y edición de docentes con su nombre completo, categoría habitual (`PAD` / `AYP`) y correo institucional `@curza.com.ar` para auto-vinculación con OAuth 2.0.
  - Eliminación con confirmación de seguridad.
- **Gestión de Usuarios (`/usuarios`)**:
  - Exclusivo para Administradores.
  - Alta de usuarios locales, asignación de roles (`admin`, `gestor_aulas`, `docente`, `alumno`), actualización de contraseñas y vinculación 1:1 con la entidad del Profesor correspondiente.

---

## ⚖️ 13. Páginas Legales y Términos de Servicio

La plataforma incorpora páginas públicas institucionales requeridas para la verificación de Google OAuth 2.0 y cumplimiento normativo:
- **Términos y Condiciones del Servicio**: Accesible en `/terminos` o `/condiciones-del-servicio`.
- **Política de Privacidad**: Accesible en `/privacidad` o `/politica-de-privacidad`.

---

© 2026 Universidad Nacional del Comahue — CURZAS (Departamento de Ciencia y Tecnología)
