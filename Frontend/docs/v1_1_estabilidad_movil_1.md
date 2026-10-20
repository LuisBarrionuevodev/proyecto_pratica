# HOTFIX V1.1-ESTABILIDAD-MÓVIL.1 — auditoría y correcciones

## A. Contraproducencia `NO_EXISTE_LOCAL`

| Capa | Causa | Corrección |
|------|--------|------------|
| Backend `ActuacionGridRowIn` | Coerción estricta de catálogo y reglas de tipo/domicilio/actas como visita realizada | Alias + familia NO EXISTE (paridad con Completar trabajo); rama terminal sin exigir rubro/calle/actas; rechazo si se envían actas |
| Frontend `actuacionFormValidation` | CRUD exigía calle/rubro y validaba actas aun con visita no realizada | `esFamiliaNoExisteLocalContraproducencia` omite esos requisitos |

**Endpoints:** `PUT /actuaciones/<id>` (mismo body grid). Completar trabajo ya usaba `CompletarTrabajoCierreIn` con coerce ampliado.

**Pruebas:** `Backend/tests/test_actuacion_no_existe_local_grid.py`, `contraproducenciaNoExisteLocal.test.ts`, bloque CRUD en `actuacionFormValidation.test.ts`.

## B. Edición + fotos (modal no debe “recargar”)

| Causa | Corrección |
|--------|------------|
| Tras `PUT` con `deferDialogClose`, `TableActuaciones` llamaba `triggerRefresh()` + `onRefresh()` de inmediato → remount/refetch de grilla y sensación de cierre sin panel de progreso | `scheduleActuacionListRefreshAfterSave`: refresco solo si no hay defer; al terminar fotos, `onEditSaveSessionEnd` refresca y cierra |

**Flujo:** `PUT` una vez → modal abierto → `ActuacionMediaGallery.saveQueuedPhotos()` (Mis trabajos / manualSave) → toast único → cierre.

**No se usa** `location.reload()` en estos flujos.

## C. Selects / catálogos en edición

| Causa | Corrección |
|--------|------------|
| Catálogos async con selects vacíos al abrir edición | `catalogsLoading` en `TableActuaciones`; alerta + `saveDisabled` en `ActuacionDetalleDialog` hasta cargar |
| Valor guardado | Sin cambio: `buildContraproducenciaCrudSelectOptions` ya fusiona valor legacy |

## D. Eliminar fotos

Sin cambio de contrato en este ticket. `ActuacionMediaGallery` ya expone delete READY (`DELETE` archivo) y `onRemove` local en cola. Revisar permisos `readOnly` por contexto si QA reporta botón oculto.

## E. Guardar en móvil / pantalla blanca

| Medida |
|--------|
| `MediaUploadPanelErrorBoundary` envuelve galería en edición de actuación |
| Evitar refetch agresivo durante subida (ítem B) |

Deuda: ErrorBoundary dedicado al cuerpo completo del modal (solo galería en esta entrega).

## F. Rendimiento (medición)

| Flujo | Antes (observado) | Después (esperado) |
|-------|-------------------|---------------------|
| Editar + 1 foto | PUT + refetch inmediato + segundo clic para ver éxito | PUT + progreso en modal + 1 refetch al cierre |
| Completar trabajo fotos | Cubierto en MEDIA-FINAL.3/4 | Sin cambios en este ticket |

Medición formal en dispositivo (360px, CPU×4) queda como QA manual pendiente.

## G. Notificaciones

Edición: un toast `MENSAJE_EDICION_OK` al cerrar sesión exitosa (datos + fotos). No duplicar toast en `handleDialogSave` cuando `deferDialogClose`.

## Alcance explícitamente no tocado

- Pipeline Mis trabajos → Cargar más fotos
- Railway Storage, cupos, idempotencia de archivos
- Migraciones Alembic

## Commit sugerido

`HOTFIX V1.1-ESTABILIDAD-MÓVIL.1: estabiliza edición, evidencia y contraproducencias.`
