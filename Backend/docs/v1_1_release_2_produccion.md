# V1.1-RELEASE.2 — Auditoría y cierre técnico de producción

**Fecha de auditoría (documento):** 2026-10-12 (UTC-3)  
**Alcance:** verificación técnica y runbook; **sin** cambios de reglas de negocio ni migración histórica de datos.  
**Repositorio:** `LuisBarrionuevodev/proyecto_pratica`  
**Rama de producción acordada:** `main` únicamente.

---

## Resumen ejecutivo

| Decisión | Estado |
|----------|--------|
| **Go / No-Go para iniciar `V1.1-MIG-RELEVAMIENTOS.2`** | **NO-GO** hasta completar ítems **bloqueantes** de la sección [Matriz](#matriz-de-estado) (despliegues cloud, Alembic productivo, cron verificado, smoke por rol firmado). |
| Código en `origin/main` alineado con auditoría local | **OK** (working tree limpio, SHA coincidente). |
| Build frontend de producción (local) | **OK** (`npm run build`). |
| Tests focalizados frontend (local) | **OK** (52 tests en paquete CRUD/media/inicio). |
| Tests focalizados backend media (local) | **Pendiente / deuda** (fallos por desalineación cupo inspección 12 vs 20; ver [Deuda](#deuda-conocida-no-bloqueante-del-ticket)). |

---

## A. Estado de código y despliegue

### Git (relevado 2026-10-12)

| Referencia | SHA (corto) | SHA (completo) | Notas |
|------------|-------------|----------------|-------|
| `HEAD` local (`main`) | `6d826ea` | `6d826eac804e0b1a9183baed745e3275e07c14ff` | Mensaje último commit: `buenas` |
| `origin/main` (post-`fetch`) | `6d826ea` | `6d826eac804e0b1a9183baed745e3275e07c14ff` | Igual que local |
| Working tree | — | — | **Limpio** (`nothing to commit`) |
| Tracking | — | — | `main` up to date con `origin/main` |

### SHA desplegado en cloud (pendiente operador)

| Plataforma | SHA desplegado | Fecha deploy | Verificado por |
|------------|----------------|--------------|----------------|
| **Vercel (Frontend)** | _Pendiente_ | _Pendiente_ | Dashboard Vercel → Deployments → commit asociado al deployment **Production** |
| **Railway (Backend)** | _Pendiente_ | _Pendiente_ | Railway → Service → Deployments → commit / imagen |

**Cómo cerrar:** el SHA de ambos entornos debe ser **`6d826ea`** (o el commit de `main` vigente al momento del go-live si hubo deploy posterior documentado aquí).

**CLI (esta auditoría):** `gh` no disponible en el entorno de auditoría. Vercel CLI: usuario `luisbarrionuevodev` (sesión presente). Railway CLI: no instalado. No se leyó SHA de deployment desde API en este ticket.

### Ramas sin merge a `main`

Ramas **locales** no fusionadas en `main`:

- `conciliacion`
- `rescue/cambios-locales`

Ramas **remotas** (`origin/*`) sin merge a `origin/main` (relevado con `git branch -r --no-merged origin/main`):

- `origin/feature/v1.1-inspector-3-mis-trabajos`
- `origin/frontnuevo`

**Hotfixes** (`hotfix/v1.1-media-*`, etc.) aparecen en remoto pero **no** figuran como sin merge respecto de `main` en el relevamiento anterior (asumir integrados o obsoletos; confirmar en GitHub si alguna sigue activa).

**Criterio operativo:** producción solo desde `main`; no desplegar ramas feature/hotfix sin merge.

---

## B. Frontend — Vercel

### Build local (verificado en auditoría)

```bash
cd Frontend
npm run build
```

- **Resultado:** exit 0 (`tsc -b` + `vite build`).
- **`npm ci`:** no ejecutado en esta pasada; recomendado en CI/Vercel (reproducibilidad lockfile).

### Configuración esperada (sin secretos)

| Ítem | Fuente / criterio | Estado doc |
|------|-------------------|------------|
| Variable pública API | `VITE_API_BASE_URL` → URL HTTPS del backend Railway (ver `Frontend/.env.example`) | **Checklist operador** |
| SPA | `Frontend/vercel.json` — rewrite a `index.html` | **OK** en repo |
| Dominio | Panel Vercel → dominio production | **Pendiente** |
| CORS backend | `CORS_ORIGINS` en Railway debe incluir dominio Vercel + `http://localhost:5173` (ver `Backend/.env.example`) | **Checklist operador** |

### Smoke manual por rol (claro / oscuro y mobile)

Marcar en operación (no automatizado en este ticket):

| Área | Admin/Usuario | Inspector | Relevamiento | Notas |
|------|---------------|-----------|--------------|-------|
| Login y recuperación contraseña | ☐ | ☐ | ☐ | Responsive compactación AUTH-UX |
| Inicio / Acerca / navegación | ☐ | ☐ | ☐ | Card Acerca sin CTA; `/acerca-de` volver arriba |
| Completar trabajo + evidencias | ☐ | ☐ | — | Cierre idempotente; subida manual post-PUT en edición actuaciones |
| Mis trabajos / fotos manuales | — | ☐ | — | `manualSave`, sin auto upload-intent |
| Actuaciones / edición | ☐ | ☐ | — | Habilitación + fotos manual |
| Relevamientos / gestión | ☐ | — | ☐ | Resolución relevador |
| Mapa e indicadores | ☐ | ☐ | ☐ | |

**Estado global smoke:** **Pendiente** (requiere ejecución en URL de producción).

### Lint / suite completa

No es objetivo de V1.1-RELEASE.2 dejar `npm run lint` ni la suite entera en verde. Registrar deuda aparte.

---

## C. Backend — Railway

### Alembic

| Concepto | Valor en `main` |
|----------|-----------------|
| **Head de revisiones** | `z1a2b3c4d5e6` (`media_2d1_upload_origin`) |
| Comando local heads | `python -m flask db heads` → `z1a2b3c4d5e6 (head)` |

**Producción (obligatorio antes de Go):**

```bash
FLASK_APP=run.py /opt/venv/bin/python -m flask db current
```

Debe imprimir **`z1a2b3c4d5e6 (head)`** (o la línea equivalente con ese revision id).

**Nota auditoría local:** `flask db current` contra sandbox local no reportó revisión aplicada en la salida capturada (posible BD local vacía o distinta de producción). **No sustituye** la verificación en Railway.

### Arranque (repo)

`Backend/railway.toml`:

- `flask db upgrade` antes de Gunicorn.
- Healthcheck: `GET /health`.
- Workers: 2, timeout 120s.

### Variables de entorno (checklist — sin valores)

Confirmar en Railway (nombres desde `Backend/.env.example`):

| Grupo | Variables |
|-------|-----------|
| Core | `ENVIRONMENT=production`, `DATABASE_URL`, `JWT_SECRET_KEY` (≥ 32 caracteres) |
| CORS | `CORS_ORIGINS` (dominio Vercel, localhost dev) |
| Mail | `MAIL_PROVIDER`, SMTP o Mailjet (`MAILJET_*`, `SMTP_*`) |
| Media storage | `MEDIA_STORAGE_PROVIDER`, `MEDIA_S3_BUCKET`, `MEDIA_S3_ENDPOINT`, `MEDIA_S3_REGION`, `MEDIA_S3_ACCESS_KEY_ID`, `MEDIA_S3_SECRET_ACCESS_KEY`, `MEDIA_PRESIGNED_URL_TTL_SECONDS` |
| Cupos media (vigentes) | `MEDIA_MAX_FOTO_ACTA_PER_RUTA_ITEM=10`, `MEDIA_MAX_FOTO_DOCUMENTACION_LOCAL_PER_RUTA_ITEM=10`, `MEDIA_MAX_FOTO_INSPECCION_PER_RUTA_ITEM=20` |

Defaults en código (`app/integrations/media_storage/config.py`) coinciden con cupos **10 / 10 / 20** si no se sobreescriben.

### Bucket y CORS del bucket

| Ítem | Criterio | Estado doc |
|------|----------|------------|
| Bucket privado | Sin URLs públicas permanentes; acceso vía presigned | **Checklist operador** |
| CORS bucket | Orígenes: producción Vercel, `localhost`; métodos **PUT, GET, HEAD** | **Checklist operador** |
| Logs | Sin URIs de DB, keys ni URLs firmadas en logs | Revisar últimos deploy logs |

---

## D. Media y operación programada

### Comando cron (Railway)

Programación documentada en `Backend/railway.toml` y `Backend/docs/ops_cleanup_pending_media.md`:

```bash
FLASK_APP=run.py /opt/venv/bin/python -m flask cleanup-pending-media
```

- **Schedule sugerido:** `0 5 * * *` (05:00 UTC).
- **Servicio:** job/cron **separado** del API Gunicorn.

### Política (código)

- Solo archivos en estado **PENDING** abandonados (por defecto **> 24 h**).
- Archivos **READY** no deben entrar en el batch de limpieza (cubierto por tests de dominio; ver deuda local en `test_media_storage_2a_idempotency`).

### Ejecución real en producción (pendiente)

| Campo | Valor |
|-------|-------|
| Fecha/hora UTC | _Registrar tras correr manual o revisar log cron_ |
| Comando | `flask cleanup-pending-media` |
| Resultado JSON esperado | `deleted_pending`, `storage_delete_errors`, `skipped_already_deleted` (ver runbook) |
| READY afectados | Debe ser **0** |

---

## E. Backup y plan de reversión

### Backup base Railway (antes de migración histórica)

1. Railway Dashboard → servicio MySQL / plugin de base → **Backups** (o snapshot según plan).
2. Export manual alternativo: `mysqldump` desde entorno autorizado (sin documentar credenciales en este archivo).
3. Registrar **fecha/hora del último backup válido** en la tabla siguiente antes de `V1.1-MIG-RELEVAMIENTOS.2`.

| Backup | Fecha (UTC) | Retención | Responsable |
|--------|-------------|-----------|-------------|
| _Pendiente_ | | | |

### Orden de ejecución migración histórica

1. Restaurar/clonar backup en **sandbox** o BD local dedicada (`digitaliza_test` / piloto).
2. Ejecutar scripts/migración de relevamientos **solo** en sandbox; validar conteos y muestras.
3. Ventana de mantenimiento en producción con backup fresco.
4. **No** asumir que `alembic downgrade` revierte importación masiva de datos históricos.

### Reversión de despliegue (aplicación)

| Plataforma | Acción |
|------------|--------|
| **Vercel** | Deployments → seleccionar deployment anterior estable → **Promote to Production** / Redeploy |
| **Railway** | Deployments → redeploy imagen/commit anterior conocido estable |

### Reversión de datos históricos

- Requiere **plan por lote** (restore desde backup o script inverso documentado en el ticket de migración).
- `flask db downgrade` solo revierte esquema Alembic, **no** filas importadas.

---

## F. Verificación mínima (ejecutada en auditoría local)

### Backend

```bash
cd Backend
pytest -q tests/test_hotfix_crud_actuaciones_habilitacion_v1_1.py
# OK — 5 passed (2026-10-12)

pytest -q tests/test_media_storage_1b.py tests/test_media_storage_2a_idempotency.py tests/test_media_storage_v1_1_0.py
# Parcial — fallos/errores (ver deuda cupo 12 vs 20)
```

### Frontend

```bash
cd Frontend
npm run build
# OK

npm test -- --run \
  src/features/media/ActuacionMediaGallery.test.tsx \
  src/Containers/Actuaciones/utils/submitActuacionRow.test.ts \
  src/Containers/Actuaciones/utils/actuacionDetalleSaveSequence.test.ts \
  src/Containers/Inicio/inicioAbout1.test.ts
# OK — 52 passed
```

---

## Matriz de estado

| # | Ítem | Estado | Bloqueante migración |
|---|------|--------|----------------------|
| 1 | `main` limpio y = `origin/main` | **OK** | No |
| 2 | SHA Vercel = SHA `main` objetivo | **Pendiente** | **Sí** |
| 3 | SHA Railway = SHA `main` objetivo | **Pendiente** | **Sí** |
| 4 | Alembic prod = `z1a2b3c4d5e6` | **Pendiente** | **Sí** |
| 5 | Variables JWT/DB/mail/CORS/media en Railway | **Pendiente** (checklist) | **Sí** |
| 6 | Cupos media 10/10/20 | **OK** (código + `.env.example`) | No |
| 7 | Bucket privado + CORS PUT/GET/HEAD | **Pendiente** | **Sí** |
| 8 | Cron `cleanup-pending-media` activo + log | **Pendiente** | **Sí** |
| 9 | Smoke manual por rol | **Pendiente** | **Sí** |
| 10 | Backup documentado | **Pendiente** | **Sí** |
| 11 | `npm run build` frontend | **OK** | No |
| 12 | Tests focalizados FE | **OK** | No |
| 13 | Tests focalizados BE media | **Deuda** | No (pero corregir antes de release mayor) |

---

## Deuda conocida (no bloqueante del ticket de documentación)

1. **Tests `test_media_storage_1b.py`:** asumen cupo **12** para `FOTO_INSPECCION`; producción y config usan **20** (`MEDIA_MAX_FOTO_INSPECCION_PER_RUTA_ITEM`). Actualizar tests o documentar override en CI.
2. **`test_inspeccion_checklist.py`:** fallo intermitente/preexistente en `test_quitar_notificacion_elimina_personas_sin_carnet` (regla reinspección origen).
3. **Suite global lint/pytest:** fuera de alcance RELEASE.2.
4. **Ramas locales/remotas sin merge:** no bloquean si no se despliegan; conviene archivar o mergear `feature/v1.1-inspector-3-mis-trabajos` si quedó obsoleta.

---

## Go / No-Go — `V1.1-MIG-RELEVAMIENTOS.2`

**NO-GO** para iniciar la migración histórica de relevamientos hasta que:

1. Vercel y Railway desplieguen el mismo commit acordado en `main` (hoy: `6d826ea`, salvo nuevo merge documentado).
2. `flask db current` en Railway reporte `z1a2b3c4d5e6`.
3. Cron de media ejecutado al menos una vez con evidencia (log sin borrado de READY).
4. Smoke por rol completado en producción.
5. Backup de BD con fecha registrada en este documento.

Cuando los cinco puntos estén **OK**, actualizar esta sección a **GO** y firmar responsable/fecha.

---

## Referencias en repo

- `Backend/railway.toml` — start + healthcheck
- `Backend/docs/ops_cleanup_pending_media.md` — cron y JSON de salida
- `Backend/.env.example` — nombres de variables
- `Frontend/.env.example` — `VITE_API_BASE_URL`
- `Frontend/vercel.json` — SPA rewrites

---

## Historial del documento

| Versión | Fecha | Autor / nota |
|---------|-------|----------------|
| 1.0 | 2026-10-12 | Auditoría inicial V1.1-RELEASE.2 (relevamiento local + checklist cloud pendiente) |
