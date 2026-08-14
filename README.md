# 📅 Sistema de Gestión de Horarios y Aulas — CURZAS UNComa

![Python Version](https://img.shields.io/badge/Python-3.12-blue.svg)
![Framework](https://img.shields.io/badge/Framework-Flask-emerald.svg)
![UI Feature](https://img.shields.io/badge/UI-Drag%20%26%20Drop%20Calendar-purple.svg)
![Authentication](https://img.shields.io/badge/Auth-OAuth%202.0%20%40curza.com.ar-indigo.svg)
![Status](https://img.shields.io/badge/Status-v0.1%20Production%20Ready-success.svg)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

Sistema web de administración, planificación de horarios y gestión de espacios físicos (laboratorios de informática y aulas comunes) desarrollado para el Complejo Universitario Zona Atlántica y Sur (**CURZAS**) de la **Universidad Nacional del Comahue (UNComa)** por el Departamento de Ciencia y Tecnología.

Diseñado específicamente para las carreras:
- **TUASSL**: *Tecnicatura Universitaria en Administración de Sistemas y Software Libre* (Ord. 0895/12 CS).
- **TUDW**: *Tecnicatura Universitaria en Desarrollo Web* (Ord. 0885/12 CS).

---

## 🌟 Características Principales

1. **Grilla Horaria Semanal Interactiva con Drag & Drop (08:00 a 21:00 / 23:00 hs)**:
   - **Reubicación de Clases Estilo Google Calendar**: Arrastrar y soltar clases directamente sobre la grilla para cambiar el día y horario con validación anticonflicto en tiempo real.
   - **Botón de Deshacer (Undo)**: Botón desplegable flotante (`↺`) para revertir rápidamente la última reubicación o cambio de clase.
   - **Adaptabilidad y Vista Móvil Optimizada**: Formato compacto de hora (`08`, `09`, ..., `21`) y días abreviados en dispositivos móviles para prevenir roturas visuales o solapamientos.
   - **Hover Popover Tooltip**: Tarjeta flotante interactiva con datos completos de cátedra, docente, categoría (`PAD`/`AYP`), aula y advertencias explicativas de solapamiento.
   - **Subcolumnas Dinámicas**: Ordenamiento automático por aula física de izquierda a derecha (*ej: Sala 1 JCBrocca a la izquierda, Sala 2 JColombo a la derecha*).

2. **❄️ Módulo de Congelamiento del Sistema (*Sistema Congelado*)**:
   - Bloqueo global de modificaciones administrado exclusivamente por el rol `admin` al cerrar períodos de planificación o durante revisiones académicas.
   - Banner de advertencia superior visible para Docentes, Gestores y Administradores indicando autor, fecha y motivo de congelamiento.
   - Desactivación automática del *Drag & Drop*, botones de edición/borrado y protección estricta en endpoints backend (HTTP `403 Forbidden`).
   - Modo de consulta pública de solo lectura garantizado para estudiantes y público general.

3. **🔍 Módulo de Auditoría y Trazabilidad (`/auditoria`)**:
   - Registro cronológico inmutable de altas, bajas, ediciones, movimientos de clases, congelamientos y descongelamientos.
   - Filtros avanzados por acción, entidad (`bloque`, `materia`, `profesor`, `usuario`, `configuración`) y usuario operador.
   - Comparación estructurada de datos previos vs. nuevos (diff JSON) con IP y marca temporal.

4. **Motor de Reglas de Negocio y Validación Anticonflicto**:
   - **Regla del >50% Sincrónico**: Verifica que cada materia cumpla $H_{sinc} \ge \lfloor H_{total}/2 \rfloor + 1$ horas semanales presenciales o por videoconferencia.
   - **Detección de Conflictos de Aula**: Alerta inmediata ante solapamientos de aulas o laboratorios físicos en el mismo cuatrimestre.
   - **Detección de Conflictos Docentes**: Bloquea la asignación simultánea de un mismo profesor a dos clases sincrónicas.
   - **Detección de Conflictos de Cohorte**: Advierte sobre superposiciones de materias del mismo año y carrera.

5. **🔐 Autenticación Institucional OAuth 2.0 (`@curza.com.ar`)**:
   - Integración nativa con **Google Workspace / OAuth 2.0** para cuentas institucionales `@curza.com.ar`.
   - Auto-vinculación automática de profesores a su entidad docente mediante coincidencia de email.
   - Páginas públicas institucionales de **Términos de Servicio** (`/terminos`) y **Política de Privacidad** (`/privacidad`).

6. **🏛️ Gestión Integral de Aulas y Materias**:
   - **Catálogo de Espacios Físicos (`/aulas`)**: ABM y edición integral de laboratorios y aulas comunes, capacidad, equipamiento y estado.
   - **Gestión Centralizada de Clases (`/materias/<id>/clases`)**: Visualización, alta rápida con materia precargada, edición y borrado de bloques por asignatura.
   - **Bloqueos Externos (`/bloqueos_externos`)**: Reserva de aulas físicas para otras facultades o eventos sin afectar el cómputo de horas sincrónicas locales.

7. **📄 Consulta Pública e Impresión Ecológica en PDF**:
   - Acceso libre de solo lectura para estudiantes y comunidad sin requerir autenticación.
   - Modo de impresión optimizado en blanco y negro puro sobre fondo 100% blanco para ahorro de tinta/tóner con membrete oficial institucional.

---

## 🔐 Configuración de OAuth 2.0 (Google / Dominio `@curza.com.ar`)

Para **activar el botón de inicio de sesión institucional con Google / OAuth 2.0**:

1. Ingrese a la [Consola de Google Cloud Credentials](https://console.cloud.google.com/apis/credentials).
2. Cree una credencial de **ID de cliente de OAuth 2.0** de tipo *Aplicación web*.
3. En **URIs de redireccionamiento autorizados**, agregue la dirección exacta con la ruta del callback:
   - **Desarrollo local**: `http://localhost:5000/auth/callback`
   - **Servidor / Producción**: `https://horarios.curza.com.ar/auth/callback` (o según su dominio/`BASE_URL`)

> [!WARNING]
> **Coincidencia exacta de URI y Error `redirect_uri_mismatch`**:
> - **Problema**: Si en Google Cloud Console solo está registrada la URI base (`https://horarios.curza.com.ar`) sin el endpoint `/auth/callback`, el inicio de sesión fallará arrojando `redirect_uri_mismatch`.
> - **Solución**: Se debe agregar explícitamente `https://horarios.curza.com.ar/auth/callback` en **"URIs de redireccionamiento autorizados"** en Google Cloud Console.
> - **Importante**: No sirve modificar esta dirección únicamente en el archivo JSON de la credencial; el cambio debe registrarse directamente en Google Cloud Console. Para más detalles, consulte la [documentación oficial de Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2/web-server).

4. Configure las variables de entorno en su servidor o archivo de entorno (Podman / Docker / Linux):
   ```bash
   export OAUTH_CLIENT_ID="xxxxxxxxx-xxxxxxxxxx.apps.googleusercontent.com"
   export OAUTH_CLIENT_SECRET="GOCSPX-xxxxxxxxxxxxxxxxxxxx"
   ```
5. Una vez configuradas las variables, el botón **`Google / UNComa (@curza.com.ar)`** se activará automáticamente en el formulario de inicio de sesión (`/login`).

---

## 🛠️ Tecnología e Infraestructura

- **Backend**: Python 3.12, Flask, Flask-SQLAlchemy 3.1, Flask-Login, Authlib (OAuth 2.0), Werkzeug, PyMySQL.
- **Base de Datos**: **MariaDB** (externo, vía contenedor Podman) con compatibilidad MySQL 8. En desarrollo local se puede usar SQLite3 (ORM SQLAlchemy 2.0).
- **Frontend**: HTML5 Drag & Drop API, Tailwind CSS, FontAwesome 6, JavaScript Vanilla.
- **Testing**: Suite nativa de `unittest` con 33 pruebas automatizadas (100% de éxito).
- **Contenedores**: `Containerfile` multi-etapa + `compose.yaml` compatible con **Podman Compose** y Docker Compose.
- **CI/CD**: GitHub Actions Pipeline en `.github/workflows/ci-cd.yml`.

---

## 🚀 Guía de Instalación y Ejecución Local

### 1. Clonar el repositorio y preparar entorno
```bash
git clone https://github.com/niunmango/SistemaHorarios.git
cd SistemaHorarios

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Iniciar el servidor de desarrollo
```bash
python3 run.py
```
Acceda desde el navegador a: `http://localhost:5000`

> **Base de datos en desarrollo local**: por defecto se usa un archivo **SQLite** en `instance/sistema_horarios.db`. Para apuntar a un **MariaDB externo**, exporte la variable `DATABASE_URL` antes de arrancar:
> ```bash
> export DATABASE_URL="mysql+pymysql://usuario:clave@localhost:3306/sistema_horarios?charset=utf8mb4"
> python3 run.py
> ```
> Al arrancar, la aplicación crea las tablas automáticamente (`db.create_all()`) y, si la base está vacía, **puebla los datos de seed por primera vez**.

---

## 🧪 Ejecución de Pruebas Automatizadas (Unit Tests)

Para correr la suite completa de 33 tests unitarios (reglas de negocio, seguridad de borrado, páginas legales y visibilidad del banner de congelamiento):

```bash
python3 -m unittest discover -s tests
```

O ejecutar módulos específicos:
```bash
python3 tests/test_rules_unittest.py
python3 tests/test_deletion_security.py
python3 tests/test_legal_pages.py
python3 tests/test_frozen_banner.py
```

---

## 🦭 Guía de Despliegue (Podman Compose con MariaDB externo)

El archivo **`compose.yaml`** define dos servicios: un contenedor **MariaDB** (base de datos externa, persistida en el volumen `mariadb_data`) y el contenedor de la **aplicación Flask** (imagen construida desde el `Containerfile`).

### Despliegue con el paquete preconstruido de GitHub Actions
```bash
podman pull ghcr.io/niunmango/sistemahorarios:latest
podman-compose up -d
```

### Despliegue compilando la imagen localmente (`--build`)
```bash
podman-compose up -d --build
```

### Configuración de variables de entorno

| Variable | Uso | Valor por defecto |
| :--- | :--- | :--- |
| `MARIADB_DATABASE` | Nombre de la base de datos | `sistema_horarios` |
| `MARIADB_USER` | Usuario de la base de datos | `horarios` |
| `MARIADB_PASSWORD` | Clave del usuario de la app | `horarios_secreto` |
| `MARIADB_ROOT_PASSWORD` | Clave del usuario root de MariaDB | `cambiar_clave_root` |
| `DB_SUBNET` | Subred de la red del compose | `172.30.0.0/24` |
| `DB_IP` | IP estática del contenedor de MariaDB | `172.30.0.10` |
| `DB_PORT` | Puerto del host para acceder a MariaDB | `3306` |
| `APP_PORT` | Puerto del host para acceder a la aplicación | `5000` |
| `SECRET_KEY` | Clave de firma de sesiones de Flask | `cambiar-clave-secreta-curzas-2026` |
| `BASE_URL` | URL base o dominio principal del sitio | `horarios.curza.com.ar` |
| `OAUTH_CLIENT_ID` | ID de cliente de Google OAuth 2.0 | *(vacío)* |
| `OAUTH_CLIENT_SECRET` | Secreto de cliente de Google OAuth 2.0 | *(vacío)* |

---

## 🔑 Cuentas Locales de Demostración

| Usuario | Correo Institucional | Contraseña | Rol | Acceso / Permisos |
| :--- | :--- | :--- | :--- | :--- |
| *(Sin login)* | *(Sin login)* | *(Sin login)* | Público / Estudiante | Consulta pública de grilla, filtros e impresión ecológica. |
| `OAuth 2.0` | `usuario@curza.com.ar` | *(Google Auth)* | Docente / Alumno | Autenticación institucional con correo `@curza.com.ar`. |
| `alumno` | `alumno@curza.com.ar` | `alumno123` | Alumno | Consulta personalizada de horarios y materias. |
| `docente` | `docente@curza.com.ar` | `docente123` | Profesor | Reubicación interactiva Drag & Drop de clases asignadas y Undo. |
| `gestor` | `gestor.aulas@curza.com.ar` | `gestor123` | Gestor de Aulas | Control total de horarios, ABM de materias, aulas y auditoría. |
| `admin` | `admin@curza.com.ar` | `admin123` | Administrador | Control total, gestión de usuarios, congelar/descongelar sistema. |

---

## 📂 Estructura del Proyecto

```text
SistemaHorarios/
├── app/
│   ├── __init__.py           # App Factory, SQLAlchemy, Authlib OAuth 2.0 y Context Processors
│   ├── models.py             # Modelos User, Profesor, Carrera, Asignatura, EspacioFisico, BloqueHorario, etc.
│   ├── rules.py              # Motor de validación (>50% sync, solapamiento aulas, docentes y cohortes)
│   ├── seed.py               # Poblado de datos base oficiales 2026 (TUASSL, TUDW, docentes @curza.com.ar)
│   ├── auth.py               # Autenticación local y flujo Google OAuth 2.0 institucional
│   ├── routes.py             # Controladores (Horarios, Materias, Profesores, Aulas, Auditoría, Congelamiento)
│   ├── audit_helpers.py      # Helpers para registro inmutable de auditoría
│   ├── static/
│   │   ├── favicon.png       # Icono oficial de la aplicación
│   │   └── logocytCURZA.png  # Logo oficial Departamento de Ciencia y Tecnología CURZAS
│   └── templates/            # Plantillas Jinja2 con Tailwind CSS
│       ├── base.html         # Layout principal con banner de congelamiento y navegación responsiva
│       ├── login.html        # Formulario de login local y acceso Google OAuth 2.0
│       ├── dashboard.html    # Panel de control de métricas, accesos rápidos y congelar/descongelar
│       ├── horarios.html     # Grilla semanal interactiva (Drag & Drop, Undo, Popovers, vista móvil compacta)
│       ├── materias.html     # Catálogo de materias con indicador >50% sincrónico
│       ├── materia_form.html # Formulario de edición con listado de clases integrado
│       ├── materia_clases.html # Submódulo de gestión de clases por asignatura
│       ├── profesores.html   # Plantel docente con confirmación de borrado
│       ├── profesor_form.html# Alta y edición de docentes (PAD/AYP, vinculación email)
│       ├── aulas.html        # Catálogo de aulas y laboratorios de computación
│       ├── aula_form.html    # Formulario de alta y edición de espacios físicos
│       ├── bloque_form.html  # Programación de clases con validación anticonflicto
│       ├── bloqueos_externos.html # Gestión de reservas de aulas para unidades académicas externas
│       ├── solicitudes.html  # Workflow de aprobación de cambios de horario
│       ├── auditoria.html    # Panel de auditoría y trazabilidad con filtros y diffs
│       ├── terminos.html     # Términos y Condiciones del Servicio (público)
│       ├── privacidad.html   # Política de Privacidad institucional (público)
│       └── usuarios.html     # Administración de cuentas y asignación de roles
├── tests/
│   ├── test_rules_unittest.py     # Pruebas de reglas de negocio y solapamientos
│   ├── test_deletion_security.py  # Pruebas de seguridad de borrado
│   ├── test_legal_pages.py        # Pruebas de páginas legales y endpoints públicos
│   └── test_frozen_banner.py      # Pruebas de visibilidad del banner de congelamiento
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions CI/CD pipeline
├── Containerfile             # Multi-stage build Podman/Docker
├── compose.yaml              # Despliegue con Podman Compose (MariaDB + app)
├── requirements.txt          # Dependencias de Python (Authlib, Flask, PyMySQL, etc.)
├── LICENSE                   # Licencia GNU General Public License v3.0 (GPLv3)
├── MANUAL_DE_USO.md          # Manual de Usuario y Guía Operativa completa
├── DATABASE_SCHEMA.md        # Esquema completo de la base de datos (tablas, relaciones, tipos)
├── README.md                 # Documentación técnica principal del proyecto
└── run.py                    # Punto de entrada de la aplicación
```

---

## 📜 Licencia
Este proyecto es Software Libre distribuido bajo los términos de la **[GNU General Public License v3.0 (GPLv3)](LICENSE)**.  
Desarrollado para el **CURZAS — Universidad Nacional del Comahue**.
