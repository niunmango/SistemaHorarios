# 📅 Sistema de Gestión de Horarios y Aulas — CURZAS UNComa

![Python Version](https://img.shields.io/badge/Python-3.12-blue.svg)
![Framework](https://img.shields.io/badge/Framework-Flask-emerald.svg)
![UI Feature](https://img.shields.io/badge/UI-Drag%20%26%20Drop%20Calendar-purple.svg)
![Authentication](https://img.shields.io/badge/Auth-OAuth%202.0%20%40curza.com.ar-indigo.svg)
![Status](https://img.shields.io/badge/Status-v1.0.0%20Ready-success.svg)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

Sistema web de administración, planificación de horarios y gestión de espacios físicos (laboratorios de informática y aulas) desarrollado para el Complejo Universitario Zona Atlántica y Sur (**CURZAS**) de la **Universidad Nacional del Comahue (UNComa)**.

Diseñado específicamente para las carreras:
- **TUASSL**: *Tecnicatura Universitaria en Administración de Sistemas y Software Libre* (Ord. 0895/12 CS).
- **TUDW**: *Tecnicatura Universitaria en Desarrollo Web* (Ord. 0885/12 CS).

---

## 🌟 Características Principales

1. **Grilla Horaria Semanal Interactiva con Drag & Drop (08:00 a 21:00 hs)**:
   - **Reubicación de Clases Estilo Google Calendar**: Arrastrar y soltar clases directamente sobre la grilla para cambiar el día y horario.
   - Vista de pantalla completa (1920p) optimizada con bloques de hora de alto simétrico.
   - Tarjeta flotante emergente (**Hover Popover Tooltip**) con explicación detallada de conflictos por cuatrimestre.
   - Coincidencias simultáneas en subcolumnas dinámicas ordenadas por número de aula física de izquierda a derecha (*ej: Sala 1 [JCBrocca] a la izquierda, Sala 2 [JColombo] a la derecha*).
2. **Motor de Reglas de Negocio y Auditoría Automática**:
   - **Regla del >50% Sincrónico**: Verifica que cada materia cumpla $H_{sinc} \ge \lfloor H_{total}/2 \rfloor + 1$ horas semanales presenciales o por videoconferencia.
   - **Detección de Conflictos de Aula**: Alerta inmediata ante solapamientos de aulas o laboratorios físicos en el mismo cuatrimestre.
   - **Detección de Conflictos Docentes**: Bloquea el intento de asignar al mismo profesor a dos clases sincrónicas en simultáneo.
   - **Detección de Conflictos de Cohorte**: Advierte la superposición de materias del mismo año y carrera.
3. **Autenticación Institucional OAuth 2.0 (`@curza.com.ar`)**:
   - Integración nativa con **OAuth 2.0 (Google / Institucional UNComa `@curza.com.ar`)**.
   - Auto-vinculación automática de cuentas de correo institucional con la entidad del `Profesor` mediante coincidencia de email.
4. **Roles Docentes Flexibles (1 PAD + Múltiples AYPs por Cátedra)**:
   - Permite definir **1 único Profesor Adjunto (PAD)** a cargo de la teoría y **múltiples Ayudantes de Primera (AYP)** para comisiones de práctica y talleres.
   - Reubicación autogestionada de horarios por el propio profesor sobre sus materias asignadas.
5. **Consulta Pública para Alumnos (Sin Login)**:
   - Acceso de solo lectura para que los estudiantes consulten y filtren horarios por carrera, cuatrimestre, profesor o aula.
   - **Modo de Impresión Ecológico**: Hoja de estilo `@media print` en blanco y negro puro sobre fondo blanco sin consumo excesivo de tóner.

---

## 🔐 Configuración de OAuth 2.0 (Google / Dominio `@curza.com.ar`)

Por defecto, la interfaz del sistema permite ingresar con usuario y contraseña local. Para **activar el botón de inicio de sesión institucional con Google / OAuth 2.0**:

1. Vaya a la [Consola de Google Cloud Credentials](https://console.cloud.google.com/apis/credentials).
2. Cree una credencial de **ID de cliente de OAuth 2.0** de tipo *Aplicación web*.
3. En **URIs de redireccionamiento autorizados**, agregue la dirección de su servidor:
   - **Desarrollo local**: `http://localhost:5000/auth/callback`
   - **Servidor / Producción**: `https://tu-dominio-curza.edu.ar/auth/callback`
4. Configure las dos variables de entorno en su servidor o archivo de entorno (Podman / Docker / Linux):
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
- **Testing**: Suite nativa de `unittest` con 100% de éxito en verificación de reglas.
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
> Al arrancar, la aplicación crea las tablas automáticamente (`db.create_all()`) y, si la base está vacía, **puebla los datos de seed por primera vez** (ver sección *Importación de Datos de Seed*).

---

## 🧪 Ejecución de Pruebas Automatizadas (Unit Tests)

Para correr la suite de tests unitarios y validar las reglas de negocio y detección de solapamientos:
```bash
python3 tests/test_rules_unittest.py
```

---

## 🦭 Guía de Despliegue (Podman Compose con MariaDB externo)

El archivo **`compose.yaml`** define dos servicios: un contenedor **MariaDB** (base de datos externa, persistida en el volumen `mariadb_data`) y el contenedor de la **aplicación Flask** (imagen construida desde el `Containerfile`). La aplicación se conecta a la base de datos mediante el driver **PyMySQL** usando la variable `DATABASE_URL`.

> **Sobre la red entre contenedores**: la base de datos usa una **IP estática** (`DB_IP`) dentro de la red del compose. Esto permite que la aplicación llegue a MariaDB incluso cuando Podman usa el backend **CNI sin el plugin `dnsname`** (caso en el que los contenedores no se resuelven entre sí por nombre). Si su instalación de Podman resuelve nombres (netavark + aardvark) o usa Docker, puede cambiar `DATABASE_URL` al nombre de servicio `db` y quitar la IP estática del archivo `compose.yaml`.

### Despliegue con el paquete preconstruido de GitHub Actions (sin `--build`)

El pipeline de CI/CD en GitHub Actions construye y publica automáticamente la imagen del contenedor en **GitHub Container Registry (GHCR)** en cada push a la rama principal:
`ghcr.io/niunmango/sistemahorarios:latest`

Para desplegar la aplicación utilizando directamente este paquete preconstruido (sin necesidad de compilar localmente con `--build`):

```bash
# 1. Descargar la versión más reciente del paquete desde GHCR (opcional, podman lo descargará si no existe)
podman pull ghcr.io/niunmango/sistemahorarios:latest

# 2. Levantar el entorno sin compilar imagen local
podman-compose up -d

# En sistemas con "podman compose" integrado:
#   podman compose up -d
```

### Despliegue compilando la imagen localmente (`--build`)

Si realiza modificaciones en el código fuente o en el `Containerfile` y desea construir la imagen en su propio equipo:

```bash
podman-compose up -d --build
```

### Verificación y gestión de servicios

```bash
# Verificar el estado de los servicios
podman-compose ps

# Ver los logs de la aplicación
podman-compose logs -f app

# Acceder a la aplicación
#   http://localhost:5000
```

La aplicación espera activamente a que MariaDB esté lista al arrancar (reintentos de conexión) y crea automáticamente las tablas, por lo que no es necesario ordenar el arranque de forma manual.

### Configuración de variables de entorno
Los valores por defecto se pueden sobrescribir exportando variables en el entorno previo al `podman-compose up`:

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
| `OAUTH_CLIENT_ID` | ID de cliente de Google OAuth 2.0 | *(vacío)* |
| `OAUTH_CLIENT_SECRET` | Secreto de cliente de Google OAuth 2.0 | *(vacío)* |

> **Importante**: antes de desplegar en producción cambie `SECRET_KEY`, `MARIADB_PASSWORD` y `MARIADB_ROOT_PASSWORD`.

---

## 🌱 Importación de Datos de Seed

Los datos de ejemplo (usuarios de demo, plantel docente, carreras, aulas, asignaturas y horarios oficiales TUASSL/TUDW) se importan automáticamente **la primera vez** que la aplicación arranca con una base de datos vacía (tabla `users` sin registros), tanto en SQLite local como en MariaDB.

### Sembrado automático al primer arranque
```bash
podman-compose up -d --build
podman-compose logs -f app    # verá el mensaje "🌱 Inicializando datos base del CURZAS..."
```

### Re-sembrado manual (restablecer la base de datos)
Para **borrar y volver a poblar** toda la base de datos (destructivo: elimina todos los datos actuales):

```bash
podman-compose exec app python -m app.seed
```

> Equivalente en desarrollo local: `python -m app.seed`. El seed ejecuta `seed_database()`, que hace `db.drop_all()` + `db.create_all()` y vuelve a insertar todos los registros.

### Conectar a MariaDB desde fuera (cliente SQL)
Con el servicio desplegado, la base queda accesible en el host en el puerto configurado (`DB_PORT`, por defecto `3306`) con el usuario `MARIADB_USER`:

```bash
mariadb -h localhost -P 3306 -u horarios -p sistema_horarios
```

---

## 🔑 Cuentas Locales de Demostración

| Usuario | Correo Institucional | Contraseña | Rol | Acceso / Permisos |
| :--- | :--- | :--- | :--- | :--- |
| *(Sin login)* | *(Sin login)* | *(Sin login)* | Público / Alumno | Consulta de grilla, filtros e impresión. |
| `OAuth 2.0` | `usuario@curza.com.ar` | *(Google Auth)* | Docente / Alumno | Autenticación con correo institucional `@curza.com.ar`. |
| `alumno` | `alumno@curza.com.ar` | `alumno123` | Alumno | Consulta de horarios y materias. |
| `docente` | `ramiro.garcia@curza.com.ar` | `docente123` | Profesor | Reubicación autogestionada Drag & Drop. |
| `gestor` | `gestor.aulas@curza.com.ar` | `gestor123` | Gestor de Aulas | ABM de clases, materias y bloqueos. |
| `admin` | `admin@curza.com.ar` | `admin123` | Administrador | Control total + ABM de usuarios y plantel docente. |

---

## 📂 Estructura del Proyecto

```text
SistemaHorarios/
├── app/
│   ├── __init__.py           # App Factory, SQLAlchemy y Authlib OAuth 2.0
│   ├── models.py             # Modelos User, Profesor, Carrera, Asignatura, EspacioFisico, BloqueHorario
│   ├── rules.py              # Motor de validación (>50% sync, solapamiento aulas, docentes y cohortes)
│   ├── seed.py               # Puebla los planes de estudio 1er y 2do cuatri TUASSL, TUDW y docentes (@curza.com.ar)
│   ├── auth.py               # Rutas de autenticación (Login local + OAuth 2.0 Google/Institucional)
│   ├── routes.py             # Rutas principales (Horarios, Materias, Profesores, Usuarios, API Drag & Drop)
│   ├── static/
│   │   └── favicon.png       # Icono oficial de la aplicación
│   └── templates/            # Plantillas Jinja2 con Tailwind CSS
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── horarios.html     # Grilla semanal interactiva con Drag & Drop y Popovers
│       ├── materias.html
│       ├── materia_form.html
│       ├── materia_clases.html    # Gestión de clases precargadas por asignatura
│       ├── profesores.html
│       ├── profesor_form.html
│       ├── bloque_form.html
│       ├── bloqueos_externos.html
│       ├── aulas.html
│       └── usuarios.html
├── tests/
│   └── test_rules_unittest.py # Suite de pruebas unitarias
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # GitHub Actions CI/CD pipeline
├── Containerfile             # Multi-stage build Podman/Docker
├── compose.yaml              # Despliegue con Podman Compose (MariaDB + app)
├── requirements.txt          # Dependencias de Python (Authlib, Flask, PyMySQL, etc.)
├── LICENSE                   # Licencia GNU General Public License v3.0 (GPLv3)
├── MANUAL_DE_USO.md          # Manual de Usuario detallado
├── README.md                 # Documentación principal del proyecto
├── DATABASE_SCHEMA.md        # 🆕 Esquema completo de la base de datos (tablas, relaciones, tipos, migraciones)
└── run.py                    # Punto de entrada de la aplicación
```

---

## 📜 Licencia
Este proyecto es Software Libre distribuido bajo los términos de la **[GNU General Public License v3.0 (GPLv3)](LICENSE)**.
Desarrollado para el **CURZAS — Universidad Nacional del Comahue**.
