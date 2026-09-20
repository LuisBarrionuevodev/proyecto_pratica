# Tests backend — aislamiento de base de datos

## Regla

| Variable | Uso | Base ejemplo |
|----------|-----|----------------|
| `SQLALCHEMY_DATABASE_URI` | Development (`python run.py`) | `digitaliza_sandbox` |
| `TEST_DATABASE_URL` | pytest / integración | `digitaliza_test` |

**pytest nunca debe escribir en `digitaliza_sandbox`.** No hay fallback de `TEST_DATABASE_URL` a `SQLALCHEMY_DATABASE_URI`.

## Preparar `digitaliza_test` (local)

1. Crear base vacía en MySQL:

```sql
CREATE DATABASE digitaliza_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. En `Backend/.env` (no commitear credenciales):

```env
SQLALCHEMY_DATABASE_URI=mysql+pymysql://USER:PASS@localhost:3306/digitaliza_sandbox
TEST_DATABASE_URL=mysql+pymysql://USER:PASS@localhost:3306/digitaliza_test
```

3. Aplicar migraciones **solo** a la base de tests:

```powershell
cd Backend
python scripts/migrate_test_db.py
```

Alternativa manual:

```powershell
$env:SQLALCHEMY_DATABASE_URI = $env:TEST_DATABASE_URL
flask db upgrade
```

4. Ejecutar tests:

```powershell
pytest
```

## Guardas

- `TEST_DATABASE_URL` obligatoria al iniciar pytest (mensaje con pasos si falta).
- Aborta si test DB == dev DB (mismo host/puerto/driver/nombre).
- El nombre de la base de tests debe contener `test`.
- `digitaliza_sandbox` no puede usarse como DB de pytest.
- En `ENVIRONMENT` / `FLASK_ENV` = `production` o `staging`, pytest con DB aborta.
- No se ejecuta `ALTER TABLE` desde fixtures: el esquema debe estar en Alembic HEAD.

## Catálogos canónicos (CATALOGOS-PREDEPLOY.3)

Versión manifest: ver `app/domains/catalogos/canonical/manifest.py` (`CATALOG_VERSION`).

### DB nueva

```powershell
cd Backend
python scripts/migrate_test_db.py   # o flask db upgrade en la DB destino
python scripts/seed_catalogos_canonicos.py --dry-run
python scripts/seed_catalogos_canonicos.py
```

Fuentes versionadas:

- Python: `app/domains/catalogos/canonical/*.py`
- Calles: `app/domains/catalogos/canonical/data/calles_canonicas.csv` (740)
- Distritos: `app/domains/geolocalizacion/geocode/data/distritos.geojson`

El seed **no limpia** contaminación QA en bases existentes; solo crea/reutiliza canónicos por clave natural.

## PREDEPLOY-CLEANUP FASE 1 — backup antes de `--apply`

**No ejecutar `--apply` sin backup verificable.** Procedimiento para `digitaliza_sandbox`:

1. Crear dump consistente (InnoDB, transaccional):

```powershell
cd Backend
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = "..\backups\digitaliza_sandbox_pre_cleanup_$ts.sql"
mysqldump --single-transaction --routines --triggers --set-gtid-purged=OFF `
  -u USER -p digitaliza_sandbox > $out
```

2. Verificar que el archivo no está vacío:

```powershell
(Get-Item $out).Length
```

3. Conservar la ruta absoluta del `.sql` (registrar en el reporte `cleanup_phase1_apply_*.json`).

4. Ejecutar apply **solo** con todas las guardas:

```powershell
python scripts/cleanup_test_contamination.py --apply `
  --confirm-database digitaliza_sandbox `
  --backup-confirmed `
  --execution-manifest scripts/output/cleanup_execution_manifest_phase1_20260920.json `
  --protected-manifest scripts/output/protected_operational_manifest_20260920.json `
  --backup-path $out
```

Generar execution manifest congelado (sin writes):

```powershell
python scripts/generate_execution_manifest.py
```

Dry-run contra manifest congelado:

```powershell
python scripts/cleanup_test_contamination.py `
  --execution-manifest scripts/output/cleanup_execution_manifest_phase1_20260920.json `
  --protected-manifest scripts/output/protected_operational_manifest_20260920.json `
  --confirm-database digitaliza_sandbox
```

## Notas

- `digitaliza_test` es **descartable**: puede recrearse y volver a migrar.
- Los commits de tests pueden dejar datos en `digitaliza_test`; eso no afecta Development.
- Vitest (frontend) no usa base de datos.
