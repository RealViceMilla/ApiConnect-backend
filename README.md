# APIConnect

APIConnect es una plataforma web para gestionar el seguimiento administrativo de secciones API con trabajo aplicado al sector productivo. El sistema permite centralizar secciones, etapas del proceso, documentos, socios productivos, visitas, calendario y alertas.

El proyecto esta dividido en dos partes:

- `APIConnect/`: backend Django con API JSON, autenticacion por sesion y reglas de permisos.
- `APIConnect-frontend/`: frontend React + Vite que consume la API del backend.

## Caracteristicas

- Autenticacion con usuarios Django y roles institucionales.
- Dashboard administrativo con datos reales desde el backend.
- Gestion de secciones API por sede, carrera, asignatura y semestre.
- Seguimiento de etapas BPM y avance documental.
- Carga, revision, aprobacion y descarga protegida de documentos.
- Propuesta y seleccion de socios productivos.
- Calendario con etapas, entregas, revisiones y visitas.
- Alertas activas por atrasos, documentos pendientes y otros hitos.
- Registro de archivos en almacenamiento privado (`private_media`).

## Tecnologias

### Backend

- Python
- Django 6
- PostgreSQL
- Sesiones y CSRF de Django

### Frontend

- React 19
- Vite
- Tailwind CSS
- ESLint

## Estructura

```text
codigo/
|-- APIConnect/
|   |-- APIConnect/
|   |-- APIConnectApp/
|   |-- private_media/
|   |-- manage.py
|   `-- requirements.txt
`-- APIConnect-frontend/
    |-- src/
    |-- package.json
    `-- vite.config.js
```

## Requisitos

- Python 3.13 o compatible con Django 6
- PostgreSQL
- Node.js y npm

## Configuracion del backend

Entra a la carpeta del backend:

```bash
cd APIConnect
```

Crea y activa un entorno virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

Instala dependencias:

```bash
pip install -r requirements.txt
```

Crea un archivo `.env` en `APIConnect/` con tus variables locales:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=conectaapi
DB_USER=conectaapi_app
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174
```

Aplica migraciones:

```bash
python manage.py migrate
```

Crea un usuario administrador:

```bash
python manage.py createsuperuser
```

Levanta el backend:

```bash
python manage.py runserver
```

El backend queda disponible en:

```text
http://localhost:8000
```

## Configuracion del frontend

Desde la carpeta raiz `codigo/`, entra al frontend:

```bash
cd APIConnect-frontend
```

Instala dependencias:

```bash
npm install
```

Levanta Vite:

```bash
npm run dev
```

El frontend usa `/api/` como base URL. En desarrollo, `vite.config.js` proxya esas llamadas al backend:

```text
/api -> http://localhost:8000
```

Si necesitas apuntar a otra URL, puedes definir:

```env
VITE_API_BASE_URL=http://localhost:8000/api/
```

## Comandos utiles

Backend:

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
npm run dev
npm run lint
npm run build
npm run preview
```

## Endpoints principales

La API esta montada bajo `/api/`.

```text
GET  /api/health/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/

GET  /api/sections/
GET  /api/sections/<id>/
POST /api/sections/<id>/requirements/
POST /api/sections/<id>/partners/propose/
POST /api/sections/<id>/partners/select/

GET  /api/calendar/events/
POST /api/calendar/visits/
PATCH /api/calendar/events/<event_id>/
DELETE /api/calendar/events/<event_id>/

GET  /api/documents/
POST /api/documents/<id>/upload/
POST /api/documents/<id>/review/
GET  /api/documents/versions/<id>/download/

GET  /api/alerts/
POST /api/alerts/generate/
```

## Notas de seguridad

- No subas `.env` al repositorio.
- Los documentos se guardan en `private_media/` y se descargan mediante vistas protegidas.
- En produccion, activa cookies seguras y configura `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` y HTTPS.

## Estado del proyecto

Proyecto academico en desarrollo. El backend Django y el frontend React se ejecutan como aplicaciones separadas durante desarrollo.
