# 📘 Manual de Uso y Usuario — Sistema de Gestión de Horarios y Aulas
**CURZAS — Universidad Nacional del Comahue (UNComa)**  
*Tecnicatura Universitaria en Administración de Sistemas y Software Libre (TUASSL)*  
*Tecnicatura Universitaria en Desarrollo Web (TUDW)*  
**Versión 1.0.0**

---

## 📌 1. Introducción y Propósito
El **Sistema de Gestión de Horarios y Aulas** es una aplicación web desarrollada para el Complejo Universitario Zona Atlántica y Sur (CURZAS) de la Universidad Nacional del Comahue. Su propósito principal es planificar, validar y visualizar la distribución semanal de materias y el uso de los espacios físicos (laboratorios de computación y aulas comunes), garantizando el cumplimiento de la reglamentación académica y optimizando la coordinación entre docentes, gestores y estudiantes.

---

## 🔑 2. Perfiles de Usuario y Credenciales de Demostración

El sistema admite 4 niveles de permisos diferenciados:

| Rol / Perfil | Nombre de Usuario | Contraseña | Descripción de Permisos |
| :--- | :--- | :--- | :--- |
| **Público / Alumnos** | *(Sin login)* | *(Sin login)* | **Consulta pública de solo lectura**. Acceso libre a la grilla semanal, filtros y exportación/impresión en PDF. |
| **Alumno Autenticado** | `alumno` | `alumno123` | Consulta de horarios y aulas de cursada. |
| **Profesor / Docente** | `docente` | `docente123` | Consulta y **reubicación interactiva Drag & Drop de sus propias clases asignadas** (siempre que el cambio no genere colisiones). |
| **Gestor de Aulas** | `gestor` | `gestor123` | Control completo de materias, reservas de aulas, bloqueos externos y creación de horarios. |
| **Administrador** | `admin` | `admin123` | **Acceso total**, incluyendo Alta, Edición y Baja de Usuarios y Docentes. |

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
     - En caso de solapamiento, **explicación detallada del conflicto** (aula o docente afectado).

4. **Impresión Ecológica / Exportación a PDF**:
   - Haga clic en el botón **`🖨️ Imprimir / PDF`** o presione `Ctrl + P`.
   - El sistema aplica una plantilla especial de impresión en **blanco y negro con fondo 100% blanco y texto en negro puro**, eliminando fondos pesados para **ahorrar tóner** e incluir un encabezado formal institucional.

---

## 🖐️ 4. Guía de Uso: Reubicación Interactiva Drag & Drop (Docentes y Gestores)

1. Inicie sesión con su usuario docente (ej: `docente`) o gestor (`gestor`).
2. En la grilla semanal (`/horarios`), haga clic sobre el bloque de la clase que desea reubicar y **arrástrelo directamente hacia el nuevo día y horario deseado** (estilo Google Calendar).
3. **Validación Anticonflicto Instantánea**:
   - Si la nueva celda de destino está libre, la clase se moverá inmediatamente y el sistema confirmará con un aviso verde.
   - Si la celda destino genera un **solapamiento de aula** o un **conflicto de horarios del docente**, el cambio será bloqueado y el sistema mostrará una notificación flotante indicando el motivo exacto.

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

- **Visualización**: En la tabla `/materias`, el sistema muestra el estado de cumplimiento de cada materia mediante distintivos de color:
  - 🟢 **Cumple (>50%)**: La materia ya tiene programadas las horas sincrónicas requeridas.
  - 🟡 **Falta Xh sinc.**: La asignatura aún no alcanza la cuota mínima sincrónica exigida.
- **Asignación de Cátedra**: Cada materia permite asociar **1 único Profesor Adjunto (PAD)** a cargo de la Teoría y **múltiples Ayudantes de Primera (AYPs)** a cargo de las comisiones de práctica.

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
