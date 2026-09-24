# Runbook Operativo - Sync Notificaciones Vencidas

## Objetivo
Ejecutar periodicamente el sync de iniciadores por notificaciones vencidas fuera del request lifecycle, con salida trazable para operaciones.

**Fase C:** el camino canónico no depende de GETs de lectura. Los listados (`/actuaciones/pendientes-notificacion`, resumen/listado de pendientes con slice notificaciones) **no** materializan iniciadores salvo compatibilidad transitoria (ver abajo).

## Comandos equivalentes (canónico)

1. Módulo Python (recomendado para scripts / Task Scheduler):

`python -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas`

2. Flask CLI (misma lógica, JSON en stdout):

`flask sync-notificaciones-vencidas`

(Desde el directorio `Backend`, con `FLASK_APP=app:create_app` o `python -m flask` según tu entorno.)

## Compatibilidad transitoria (solo emergencia)

Si necesitás el comportamiento antiguo (materializar al leer):

- Variable de entorno: `SYNC_NOTIFICACIONES_VENCIDAS_ON_READ=1` (valores aceptados: `1`, `true`, `yes`).

Desaconsejado en producción: usar scheduler + comando de arriba.

## Ejecucion manual (validacion operativa)

1. Abrir terminal en `Backend`.
2. Activar el entorno virtual.
3. Ejecutar:

```powershell
python -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas
```

Salida esperada:
- Linea operativa: `Sync notificaciones vencidas OK. created=... eligible=... skipped_blocking=... collisions=... elapsed_ms=...`
- Linea JSON con metricas: `status`, `created`, `eligible_notificaciones`, `skipped_already_blocking`, `collisions_idempotent`, `elapsed_ms`, `started_at`

Logs en aplicación (nivel INFO): `sync_reinspeccion_notificacion_inicio` y `sync_reinspeccion_notificacion_fin` en el logger del servicio de iniciadores.

## Wrapper recomendado (Windows)

Se incluye script wrapper para scheduler:

`Backend/scripts/run_sync_notificaciones_vencidas.ps1`

Ejecucion manual del wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_sync_notificaciones_vencidas.ps1
```

Opciones utiles:

```powershell
# Python explicito
powershell -ExecutionPolicy Bypass -File .\scripts\run_sync_notificaciones_vencidas.ps1 -PythonPath ".\.venv\Scripts\python.exe"

# Log dir explicito
powershell -ExecutionPolicy Bypass -File .\scripts\run_sync_notificaciones_vencidas.ps1 -LogDir ".\logs\ops"
```

## Frecuencia sugerida

- Recomendado: cada `10` minutos.
- Alternativa mas agresiva: cada `5` minutos (si el volumen operativo lo requiere).

## Logging y monitoreo

El wrapper deja logs por corrida en:

`Backend/logs/ops/sync_notificaciones_vencidas_YYYYMMDD_HHMMSS.log`

Cada archivo contiene:
- salida completa del comando Python (stdout/stderr)
- metricas impresas por el CLI
- codigo de salida final

Interpretacion:
- `exit_code = 0`: corrida correcta.
- `exit_code != 0`: error operativo; revisar el log y reintentar.

## Configuracion en Windows Task Scheduler

### Opcion A - Task Scheduler (GUI)

1. Abrir `Task Scheduler`.
2. `Create Task...`.
3. Pestaña `General`:
   - Name: `sync_notificaciones_vencidas`
   - Run whether user is logged on or not.
   - Run with highest privileges (si aplica en tu entorno).
4. Pestaña `Triggers`:
   - New Trigger:
   - Begin the task: On a schedule
   - Daily
   - Repeat task every: `10 minutes`
   - For a duration of: `Indefinitely`
5. Pestaña `Actions`:
   - Action: `Start a program`
   - Program/script: `powershell.exe`
   - Add arguments:
     `-ExecutionPolicy Bypass -File "C:\Users\pablo\proyecto_pratica\Backend\scripts\run_sync_notificaciones_vencidas.ps1"`
   - Start in:
     `C:\Users\pablo\proyecto_pratica\Backend`
6. Pestaña `Settings` (recomendado):
   - Allow task to be run on demand.
   - If the task fails, restart every 5 minutes, attempt 3 times.
   - If the running task does not end when requested, force it to stop.

### Opcion B - Registro por linea de comandos

Ejemplo con `schtasks`:

```powershell
schtasks /Create /TN "sync_notificaciones_vencidas" /SC MINUTE /MO 10 /TR "powershell.exe -ExecutionPolicy Bypass -File \"C:\Users\pablo\proyecto_pratica\Backend\scripts\run_sync_notificaciones_vencidas.ps1\"" /F
```

## Checklist operativo

- [ ] La tarea corre en background cada 10 min.
- [ ] Se generan logs en `Backend/logs/ops`.
- [ ] El JSON de salida incluye `status=ok` y `created` coherente.
- [ ] Ante error, se observa `exit_code != 0` y hay log para diagnostico.
