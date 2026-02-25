# Digitaliza Bromatología (San Miguel de Tucumán)

Sistema interno para **digitalizar, registrar y consultar actuaciones de Bromatología** (órdenes de trabajo, inspecciones, notificaciones, comprobaciones, decomisos, clausuras, expedientes/oficios), con foco en:
- carga rápida (incluye grilla editable en front),
- trazabilidad por mes/año,
- normalización de contribuyentes/domicilios/rubros,
- soporte geográfico (Distrito/Barrio con geometrías),
- base para tableros e indicadores.

---

## Stack tecnológico

### Frontend
- React 19 + TypeScript
- Vite
- React Router
- MUI (Material UI)

### Backend
- Flask 3
- Flask-SQLAlchemy + SQLAlchemy 2
- Alembic / Flask-Migrate
- Pydantic 2 (validación y payloads)
- MySQL
- GeoAlchemy2 (geometrías para distrito/barrio)
- pytest (tests)

### Deploy (plan)
- Docker (app + DB + migraciones) / Docker Compose

---

## Arquitectura (criterio de código)

**Objetivo:** separar responsabilidades para que el sistema sea escalable y fácil de testear.

- `routes/` (o `api/`): Blueprints / endpoints HTTP. No lógica pesada.
- `schemas/`: Pydantic (entradas/salidas), validaciones.
- `mappers/`: transforma inputs validados a payloads limpios para services (sin DB).
- `services/`: reglas de negocio + orquestación (puede usar repos).
- `repositories/` (opcional): acceso DB / queries reutilizables.
- `models/`: modelos SQLAlchemy.
- `utils/`: normalizadores/validadores pequeños, helpers, constantes.

Reglas clave:
- Las rutas NO tocan directamente modelos complejos (solo llaman services).
- Pydantic valida entradas; services aplican reglas de negocio.
- Alembic maneja cambios de esquema (nunca “a mano” en prod).
- Todo cambio relevante: test mínimo (pytest).

---

## Modelo de datos (resumen desde el dump)

Entidades principales:

### Operación / núcleo
- `orden_trabajo`  
  Orden base (número, mes, año).
- `actuaciones`  
  Registro principal por fecha/mes/año con tipo (enum) y referencia a:
  - `orden_trabajo` (obligatorio)
  - `notificacion` (opcional)
  - `comprobacion` (opcional)
  - `domicilio` (opcional)

### Actas relacionadas
- `inspeccion` (FK a `actuaciones`)
- `clausura` (FK a `actuaciones`)
- `decomiso` (FK a `actuaciones`, incluye `cantidad`)
- `notificacion` (tabla propia; motivos por relación)
- `comprobacion` (tabla propia)

### Inspectoría
- `inspector` (incluye `turno_id`)
- `turno`
- `actuaciones_inspector` (N:N entre actuaciones e inspectores)

### Contribuyentes / lugares
- `contribuyente` (apellido, nombre, documento)
- `domicilio` (calle, número, cp, ciudad, provincia, país, lat/long)
  - FK a `contribuyente`
  - FK a `rubro`
  - FK opcional a `barrio`
- `rubro`

### Geografía
- `distrito` (geom)
- `barrio` (geom, FK a distrito)

### Flujos administrativos
- `expediente` (FK a `comprobacion`, FK opcional a `oficio`)
- `oficio` (FK a `comprobacion`)

### Catálogos / otros
- `motivo`
- `notificacion_motivo` (tabla puente: notificación ↔ motivo)
- `usuario`
- `alembic_version`

---

## API (criterios de endpoints)
- JSON siempre.
- Validación de entrada con Pydantic.
- Respuestas: schema de salida (Pydantic) o dict serializable.
- Errores: status codes correctos + mensaje claro (sin stacktrace).

---

## Dev Setup

### Front
```bash
cd frontend
npm install
npm run dev
```

### Backend (Windows)
```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```Variables minimas (ejemplo):
- `DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/digitaliza`Setup rapido (migraciones + upgrade + import CSV):
```powershell
python run.py setup --csv .\app\domains\geolocalizacion\normalizacion_calles\data\calles_normalizadas.csv --message "auto migration"
```

Levantar server:
```powershell
python run.py
```

### Backend (Linux/Mac)
```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Variables minimas (ejemplo):
- `DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/digitaliza`

Setup rapido (migraciones + upgrade + import CSV):
```bash
python run.py setup --csv ./app/domains/geolocalizacion/normalizacion_calles/data/calles_normalizadas.csv --message "auto migration"
```

Levantar server:
```bash
python run.py
```

Notas:
- Si ya existe `migrations/`, el setup no ejecuta `flask db init`.
- Si no hay cambios de modelos, `migrate` puede generar migracion vacia (usa `--no-migrate` si queres omitir).
- Si falla por GeoAlchemy2: `pip install geoalchemy2`.