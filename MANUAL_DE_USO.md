# 📘 Manual de Uso y Usuario — Sistema de Gestión de Horarios y Aulas
**CURZAS — Universidad Nacional del Comahue (UNComa)**  
*Tecnicatura Universitaria en Administración de Sistemas y Software Libre (TUASSL)*  
*Tecnicatura Universitaria en Desarrollo Web (TUDW)*  
**Versión 1.0.0**

---

## 📌 1. Introducción y Propósito
El **Sistema de Gestión de Horarios y Aulas** es una aplicación web desarrollada para el Complejo Universitario Zona Atlántica y Sur (CURZAS) de la Universidad Nacional del Comahue. Su propósito principal es planificar, validar y visualizar la distribución semanal de materias y el uso de los espacios físicos (laboratorios de computación y aulas comunes), garantizando el cumplimiento de la reglamentación académica y optimizando la coordinación entre docentes, gestores y estudiantes.

---

## 🔑 2. Perfiles de Usuario, Credenciales e Inicio con OAuth 2.0

### 2.1. Cuentas Locales de Demostración

| Rol / Perfil | Nombre de Usuario | Correo Institucional | Contraseña | Descripción de Permisos |
| :--- | :--- | :--- | :--- | :--- |
| **Público / Alumnos** | *(Sin login)* | *(Sin login)* | *(Sin login)* | **Consulta pública de solo lectura**. Acceso libre a la grilla semanal, filtros y exportación/impresión en PDF. |
| **Alumno Autenticado** | `alumno` | `alumno@curza.com.ar` | `alumno123` | Consulta de horarios y aulas de cursada. |
| **Profesor / Docente** | `docente` | `ramiro.garcia@curza.com.ar` | `docente123` | Consulta y **reubicación interactiva Drag & Drop de sus propias clases asignadas**. |
| **Gestor de Aulas** | `gestor` | `gestor.aulas@curza.com.ar` | `gestor123` | Control completo de materias, reservas de aulas, bloqueos externos y creación de horarios. |
| **Administrador** | `admin` | `admin@curza.com.ar` | `admin123` | **Acceso total**, incluyendo Alta, Edición y Baja de Usuarios y Docentes. |

---

### 2.2. Autenticación Institucional OAuth 2.0 (`@curza.com.ar`)

El sistema cuenta con integración nativa para **Inicio de Sesión Unificado con Google / OAuth 2.0** utilizando la cuenta institucional (`@curza.com.ar` o `@fi.uncoma.edu.ar`).

#### ¿Cómo Habilitar el Botón de OAuth 2.0 en Producción?
Para que el botón **`Google / UNComa`** aparezca activo en la pantalla de inicio de sesión (`/login`):

1. **Crear Credenciales de OAuth 2.0 en Google Cloud / Workspace**:
   - Vaya a la [Consola de Google Cloud](https://console.cloud.google.com/apis/credentials).
   - Cree un nuevo proyecto o seleccione el proyecto de la universidad.
   - En **Pantalla de Consentimiento de OAuth**, configure el dominio institucional `curza.com.ar`.
   - En **Credenciales** $\rightarrow$ **ID de cliente de OAuth 2.0** $\rightarrow$ **Aplicación web**, agregue las URIs de redireccionamiento autorizadas:
     - **Para desarrollo local**: `http://localhost:5000/auth/callback`
     - **Para Servidor / Producción**: `https://tu-dominio-curza.edu.ar/auth/callback`

2. **Configurar Variables de Entorno en el Servidor (Podman / Docker / Linux)**:
   Agregue las siguientes dos variables de entorno (`OAUTH_CLIENT_ID` y `OAUTH_CLIENT_SECRET`), ya sea exportándolas en el entorno previo al `podman compose up` o configurándolas en su archivo de variables de entorno:
   - `OAUTH_CLIENT_ID`: `xxxxxx-xxxxxx.apps.googleusercontent.com`
   - `OAUTH_CLIENT_SECRET`: `GOCSPX-xxxxxxxxxxxxxx`

3. **Auto-vinculación de Cuentas de Docentes**:
   - Cuando un profesor inicia sesión con su correo institucional (`ej: ramiro.garcia@curza.com.ar`), el sistema reconoce automáticamente la cuenta, la vincula al plantel docente y le otorga permisos de edición sobre sus clases correspondientes.

---

## 📅 3. Guía de Uso: Consulta Pública de Horarios (Estudiantes)

1. **Ingreso Directo**:
   - Ingrese a la dirección principal del sistema (`http://localhost:5000/` o la URL del servidor). Serás dirigido directamente a la **Grilla Horaria Semanal**. No es necesario iniciar sesión.

2. **Filtros Interactivos**:
   - En la barra superior de filtros se puede acotar la grilla seleccionando:
     - **Carrera**: Alternar entre *TUASSL*, *TUDW* o *Materias Externas*.
     - **Cuatrimestre**: Filtrar materias de 1° o 2° Cuatrimestre (con aislamiento automático de reglas de conflicto).
     - **Profesor/a**: Ver el cronograma de un docente en particular.
     - **Aula / Sala**: Consultar la ocupación de la *Sala 1 (JCBrocca)*, *Sala 2 (JColombo)*, *Aula 18*, etc.
     - **Modalidad**: Filtrar por clases Presenciales, Virtuales o Híbridas.

3. **Detalles de Clase al Pasar el Cursor (Hover Popover)**:
   - Al mover el cursor sobre cualquier bloque horaria, se desplegará una tarjeta flotante con la información completa:
     - Nombre de la Asignatura, Carrera, Año y Cuatrimestre.
     - Horario exacto y duración total en horas.
     - Docente a cargo e indicación de su rol (**PAD** para Teoría o **AYP** para Práctica).
     - Aula asignada y observaciones pedagógicas.
     - En caso de solapamiento, **explicación detallada del conflicto** (aula, docente o cohorte afectada).

4. **Impresión Ecológica / Exportación a PDF**:
   - Haga clic en el botón **`🖨️ Imprimir / PDF`** o presione `Ctrl + P`.
   - El sistema aplica una plantilla especial de impresión en **blanco y negro con fondo 100% blanco y texto en negro puro**, eliminando fondos pesados para **ahorrar tóner** e incluir un encabezado formal institucional.

---

## 🖐️ 4. Guía de Uso: Reubicación Interactiva Drag & Drop (Docentes y Gestores)

1. Inicie sesión con su usuario docente (ej: `docente`) o mediante Google OAuth con su correo `@curza.com.ar`.
2. En la grilla semanal (`/horarios`), haga clic sobre el bloque de la clase que desea reubicar y **arrástrelo directamente hacia el nuevo día y horario deseado** (estilo Google Calendar).
3. **Validación Anticonflicto Instantánea**:
   - Si la nueva celda de destino está libre, la clase se moverá inmediatamente y el sistema confirmará con un aviso verde.
   - Si la celda destino genera un **solapamiento de aula** o un **conflicto de horarios del docente**, el cambio será bloqueado y el sistema mostrará una notificación flotante indicando el motivo exacto.
4. **Botón de Deshacer (Undo)**:
   - Al posicionar el cursor (*hover*) sobre cualquier bloque de clase que tenga permisos para editar, se visualizará un botón de deshacer (**`↺`**).
   - Al hacer clic, el sistema invoca la API `/api/bloque/<id>/deshacer` y restaura la clase a su día y horario anterior, revalidando las reglas anticonflicto de forma automática.

---

## 🏫 5. Guía de Uso: Gestión de Horarios y Aulas (Gestores y Docentes)

### 5.1. Programación de una Nueva Clase (`/bloques/nuevo`)
1. Inicie sesión con una cuenta de **Gestor** (`gestor`) o **Administrador** (`admin`).
2. Haga clic en el botón **`+ Nueva Clase / Reserva`** de la barra superior.
3. Seleccione la Asignatura, el Profesor/a a cargo y su **Rol en esta Clase** (`PAD` o `AYP`).
4. Indique el Día de la semana, Modalidad (Presencial, Virtual, Híbrido, Asincrónico PEDCO) y las Horas de Inicio y Fin.
5. Si requiere espacio físico, seleccione el **Aula / Sala**.
6. Haga clic en **Guardar Reserva**. El motor de validación verificará instantáneamente que no existan colisiones de aulas ni solapamientos docentes.

---

## 📚 6. Guía de Uso: Planes de Estudio y Regla del >50% Sincrónico (`/materias`)

Para las carreras TUASSL y TUDW, la normativa exige que la carga semanal sincrónica $H_{sinc}$ cumpla:
$$H_{sinc} \ge \left\lfloor \frac{H_{total}}{2} \right\rfloor + 1$$

- **Visualización y Control**: En la tabla `/materias`, el sistema muestra el estado de cumplimiento de cada materia mediante distintivos de color:
  - 🟢 **Cumple (>50%)**: La materia ya tiene programadas las horas sincrónicas requeridas.
  - 🟡 **Falta Xh sinc.**: La asignatura aún no alcanza la cuota mínima sincrónica exigida.

- **Gestión Centralizada de Clases Precargadas (`Editar Clases`)**:
  - En la columna de acciones de la tabla `/materias`, cada asignatura cuenta con la opción **`Editar Clases`** (mostrando la cantidad de clases programadas).
  - Al ingresar, el sistema precarga el listado completo de clases asignadas a dicha materia, permitiendo:
    - **Editar**: Modificar el día, horario (24hs), modalidad, aula o docente de una clase existente.
    - **Borrar**: Eliminar un bloque horario programado.
    - **+ Crear Clase**: Programar una nueva clase para la asignatura preseleccionada.
  - Asimismo, al editar la información general de la asignatura (`/materias/<id>/editar`), el sistema precarga al pie del formulario el listado de clases existentes con las mismas opciones de edición y borrado.

---

## 🔒 7. Guía de Uso: Bloqueos de Aula Externos (`/bloqueos_externos`)

1. Ingrese a la sección **`Bloqueos Externos`**.
2. Permite reservar aulas físicas para materias de otras unidades académicas (Exactas, Economía) o eventos institucionales.
3. Estos bloqueos ocupan el aula física en la grilla impidiendo colisiones, pero **no afectan la regla del >50% sincrónico** de las tecnicaturas del CURZAS.

---

## 👨‍🏫 8. Guía de Uso: Administración de Docentes y Usuarios (`/profesores` y `/usuarios`)

- **Plantel Docente (`/profesores`)**: Acceso para dar de alta, modificar la categoría habitual (`PAD` / `AYP`) o dar de baja a profesores.
- **Gestión de Cuentas (`/usuarios`)**: Exclusivo para Administradores. Permite crear usuarios, asignar roles (`admin`, `gestor_aulas`, `docente`, `alumno`), modificar contraseñas y **vincular cuentas de usuario a la entidad de un Profesor**.

---

© 2026 Universidad Nacional del Comahue — CURZAS (Departamento de Ciencia y Tecnología)
