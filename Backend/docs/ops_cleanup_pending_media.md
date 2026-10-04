# Runbook — Cleanup Media PENDING vencidos

## Objetivo

Eliminar cargas `PENDING` abandonadas (>24 h): borrado best-effort en bucket privado y soft-delete en MySQL. **No** se ejecuta en requests de usuario.

## Comandos

Desde `Backend/` con entorno activo:

```bash
flask cleanup-pending-media
flask cleanup-pending-media --older-than-hours 24
python -m app.domains.media.pipelines.cleanup_pending_media
```

Salida JSON:

```json
{"deleted_pending": 3, "storage_delete_errors": 0, "skipped_already_deleted": 0}
```

## Railway (cron diario)

1. Crear un **servicio Cron** en el proyecto Railway (o duplicar el servicio backend como Cron Job).
2. **Schedule:** `0 5 * * *` (05:00 UTC diario; ajustar según zona operativa).
3. **Start command:**

```bash
FLASK_APP=run.py flask cleanup-pending-media
```

4. Mismas variables de entorno que el backend (DB, `MEDIA_*`, storage).
5. No compartir el proceso Gunicorn del API: el cron debe ser un job aparte.

## Windows Task Scheduler

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_cleanup_pending_media.ps1
```

## Checklist

- [ ] Cron diario activo en Railway.
- [ ] Logs `media_cleanup_pending_batch` visibles sin URLs firmadas.
- [ ] Archivos `READY` no aparecen en métricas `processed`.
