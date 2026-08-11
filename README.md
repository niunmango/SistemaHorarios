# 📅 Sistema de Gestión de Horarios y Aulas — CURZAS UNComa

![Python Version](https://img.shields.io/badge/Python-3.12-blue.svg)
![Framework](https://img.shields.io/badge/Framework-Flask-emerald.svg)
![Status](https://img.shields.io/badge/Status-v1.0.0%20Ready-success.svg)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

Sistema web de administración, planificación de horarios y gestión de espacios físicos (laboratorios de informática y aulas) desarrollado para el Complejo Universitario Zona Atlántica y Sur (**CURZAS**) de la **Universidad Nacional del Comahue (UNComa)**.

Diseñado específicamente para las carreras:
- **TUASSL**: *Tecnicatura Universitaria en Administración de Sistemas y Software Libre* (Ord. 0895/12 CS).
- **TUDW**: *Tecnicatura Universitaria en Desarrollo Web* (Ord. 0885/12 CS).

---

## 🌟 Características Principales

1. **Grilla Horaria Semanal Simétrica e Interactiva (08:00 a 21:00 hs)**:
   - Vista de pantalla completa (1920p) optimizada con bloques de hora de alto simétrico.
   - Tarjeta flotante emergente (**Hover Popover Tooltip**) con orientación inteligente para filas inferiores (a partir de las 16:00 hs).
   - Coincidencias simultáneas en subcolumnas dinámicas ordenadas por número de aula física de izquierda a derecha (*ej: Sala 1 [JCBrocca] a la izquierda, Sala 2 [JColombo] a la derecha*).
2. **Motor de Reglas de Negocio y Auditoría Automática**:
   - **Regla del >50% Sincrónico**: Verifica que cada materia cumpla $H_{sinc} \ge \lfloor H_{total}/2 \rfloor + 1$ horas semanales presenciales o por videoconferencia.
   - **Detección de Conflictos de Aula**: Alerta inmediata ante solapamientos de aulas o laboratorios físicos.
   - **Detección de Conflictos Docentes**: Bloquea el intento de asignar al mismo profesor a dos clases sincrónicas en simultáneo.
   - **Módulo de Bloqueos Externos**: Permite reservar aulas para materias de Exactas o eventos sin alterar las métricas sincrónicas de las tecnicaturas.
3. **Roles Docentes Flexibles (1 PAD + Múltiples AYPs por Cátedra)**:
   - Permite definir **1 único Profesor Adjunto (PAD)** a cargo de la teoría y **múltiples Ayudantes de Primera (AYP)** para comisiones de práctica y talleres.
   - Reubicación autogestionada de horarios por el propio profesor sobre sus materias asignadas.
4. **Consulta Pública para Alumnos (Sin Login)**:
   - Acceso de solo lectura para que los estudiantes consulten y filtren horarios por carrera, cuatrimestre, profesor o aula.
   - **Modo de Impresión Ecológico**: Hoja de estilo `@media print` en blanco y negro puro sobre fondo blanco sin consumo excesivo de tóner.

---

## 🛠️ Tecnología e Infraestructura

- **Backend**: Python 3.12, Flask, Flask-SQLAlchemy 3.1, Flask-Login, Werkzeug.
- **Base de Datos**: SQLite3 / PostgreSQL compatible (ORM SQLAlchemy 2.0).
- **Frontend**: HTML5, Tailwind CSS, FontAwesome 6, JavaScript Vanilla.
- **Testing**: Suite nativa de `unittest` con 100% de éxito en verificación de reglas.
- **Contenedores**: Archivo `Containerfile` multi-etapa compatible con Podman y Docker.
- **CI/CD**: GitHub Actions Pipeline en `.github/workflows/ci-cd.yml`.

---

## 🚀 Guía de Instalación y Ejecución Local

### 1. Clonar el repositorio y preparar entorno
```bash
git clone https://github.com/ramiro-uncoma/SistemaHorarios.git
cd SistemaHorarios

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Poblar la base de datos con planes oficiales
```bash
python3 -c "from app import create_app; from app.seed import seed_database; app = create_app(); app.app_context().push(); seed_database()"
```

### 3. Iniciar el servidor de desarrollo
```bash
python3 run.py
```
Acceda desde el navegador a: `http://localhost:5000`

---

## 🧪 Ejecución de Pruebas Automatizadas (Unit Tests)

Para correr la suite de tests unitarios y validar las reglas de negocio y detección de solapamientos:
```bash
python3 tests/test_rules_unittest.py
```

---

## 🦭 Guía Completa de Despliegue con Podman

El proyecto cuenta con un `Containerfile` multi-etapa optimizado para entornos de producción con **Podman** sin necesidad de permisos de superusuario (rootless).

### 1. Construir la imagen del contenedor
```bash
podman build -t sistema-horarios-curzas -f Containerfile .
```

### 2. Inicializar la base de datos con los datos oficiales de cursada
```bash
podman run --rm -v ./instance:/app/instance:Z sistema-horarios-curzas python3 -c "from app import create_app; from app.seed import seed_database; app = create_app(); app.app_context().push(); seed_database()"
```

### 3. Ejecutar el contenedor en segundo plano (Modo Detached)
```bash
podman run -d \
  --name sistema_horarios_app \
  -p 5000:5000 \
  -v ./instance:/app/instance:Z \
  --restart always \
  sistema-horarios-curzas
```

### 4. Verificar el estado del servicio y consultar registros
```bash
# Verificar que el contenedor esté en ejecución
podman ps

# Inspeccionar los logs del servidor
podman logs -f sistema_horarios_app
```

### 5. Comandos útiles de gestión
```bash
# Detener el contenedor
podman stop sistema_horarios_app

# Reiniciar el contenedor
podman start sistema_horarios_app

# Eliminar el contenedor
podman rm -f sistema_horarios_app
```
Acceda desde cualquier equipo de la red a `http://<ip-servidor>:5000`

---

## 🔐 Cuentas de Demostración

| Usuario | Contraseña | Rol | Acceso / Permisos |
| :--- | :--- | :--- | :--- |
| *(Sin login)* | *(Sin login)* | Público / Alumno | Consulta de grilla, filtros e impresión. |
| `alumno` | `alumno123` | Alumno | Consulta de horarios y materias. |
| `docente` | `docente123` | Profesor | Reubicación autogestionada de sus clases. |
| `gestor` | `gestor123` | Gestor de Aulas | ABM de clases, materias y bloqueos. |
| `admin` | `admin123` | Administrador | Control total + ABM de usuarios y plantel docente. |

---

## 📂 Estructura del Proyecto

```text
SistemaHorarios/
├── app/
│   ├── __init__.py           # App Factory y configuración Flask/SQLAlchemy
│   ├── models.py             # Modelos User, Profesor, Carrera, Asignatura, EspacioFisico, BloqueHorario
│   ├── rules.py              # Motor de validación (>50% sync, solapamiento aulas y docentes)
│   ├── seed.py               # Puebla los planes de estudio TUASSL, TUDW y docentes
│   ├── auth.py               # Rutas de autenticación (Login / Logout)
│   ├── routes.py             # Rutas principales (Horarios, Materias, Profesores, Usuarios, APIs)
│   ├── static/
│   │   └── favicon.png       # Icono oficial de la aplicación
│   └── templates/            # Plantillas Jinja2 con Tailwind CSS
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── horarios.html
│       ├── materias.html
│       ├── materia_form.html
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
├── requirements.txt          # Dependencias de Python
├── LICENSE                   # Licencia GNU General Public License v3.0 (GPLv3)
├── MANUAL_DE_USO.md          # Manual de Usuario detallado
├── README.md                 # Documentación principal del proyecto
└── run.py                    # Punto de entrada de la aplicación
```

---

## 📜 Licencia
Este proyecto es Software Libre distribuido bajo los términos de la **[GNU General Public License v3.0 (GPLv3)](LICENSE)**.
Desarrollado para el **CURZAS — Universidad Nacional del Comahue**.
