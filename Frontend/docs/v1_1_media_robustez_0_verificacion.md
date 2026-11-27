# V1.1-MEDIA-ROBUSTEZ.0 — Verificación focalizada del flujo de fotos

**Tipo:** verificación (sin cambios de código productivo, permisos ni subida).
**Fecha:** 2026-11-27.
**Contraste:** `Frontend/docs/v1_1_media_estabilidad_0_relevamiento.md` (2026-11-16) frente al código actual.
**Escritura realizada:** solo este documento.

---

## Respuesta al criterio de aceptación

**¿Qué se guarda, qué queda pendiente y qué se repite cuando falla una foto en Editar?**

Al tocar **Guardar cambios** (`ActuacionDetalleDialog.handleSaveClick`):

1. Se confirman los **datos** (`PUT /actuaciones/:id`, y antes, si aplica, corrección de oficio y/o quitar actas). Eso **ya persistió** aunque después falle una foto.
2. Recién entonces se suben las fotos de a una (intent → PUT al bucket → complete). El panel de progreso **ya existe** (`MediaUploadProgress`: «Subiendo fotos», contador N/Total, «No cierres esta pantalla»).
3. Si alguna foto no llega a **READY**, el modal **no cierra**. Toast: *«Algunas fotos no terminaron de subir… tocá CONTINUAR SUBIDA…»*. El botón del modal, sin embargo, sigue diciendo **Guardar cambios**.
4. Un segundo toque **vuelve a ejecutar el PUT** (y puede repetir quitar actas), porque `editOriginalRow` no se actualiza tras el primer PUT. No hay un modo «solo fotos» en Editar.
5. Si el fallo ocurrió **después** de obtener `archivoId` (intent OK, bytes o complete fallidos), `pendingSaveCount()` cuenta 0. El segundo Guardar **omite las fotos**, cierra el modal y muestra *«Actuación editada correctamente»*. La cola en memoria se pierde al desmontar.

**¿Qué conviene corregir primero sin alterar la subida que ya funciona?**

Los **estados y mensajes de Editar** (Etapa 1) van **juntos** con **reintentar solo fotos** en el mismo ticket pequeño. Separar mensajes sin cambiar el botón dejaría el copy «CONTINUAR SUBIDA» contradiciendo «Guardar cambios», y un segundo Guardar seguiría repitiendo el PUT.

No reabrir el hotfix de Chrome Translate: sigue en el código y pasó QA (emulador y Moto G41).

---

## 1. Hallazgos anteriores que siguen vigentes

Evidencia en el código actual (no reabren Translate).

| Id | Hallazgo | Evidencia |
|----|----------|-----------|
| V-1 | Datos y fotos **no son atómicos**. Orden: PUT (o corrección de oficio) → fotos. | `handleSaveClick` (aprox. 1723–1752) llama `onSave` y, si `putOk`, `gallery.saveQueuedPhotos()`. Test de orden: `actuacionDetalleSaveSequence.test.ts`. |
| V-2 | Tras PUT + fotos parciales, **volver a Guardar re-ejecuta el PUT** y puede repetir `postQuitarActaCanalActas` o `actas_a_quitar` en el PUT. | `handleDialogSave` no asigna `editOriginalRow` con `result.updatedRow` (aprox. 395–408). `submitActuacionRow.ts` 471–576. |
| V-3 | Mensaje genérico **después** de un PUT ya OK: *«No se pudo guardar la actuación.»* | `catch` de `handleSaveClick` 1761–1763 (`MENSAJE_ERROR_GRAVE`). |
| V-4 | El toast de parcial pide **CONTINUAR SUBIDA**; en Editar el botón es **Guardar cambios**. En Cargar más fotos el label sí cambia (`manualMediaSavePrimaryLabel`). | `MANUAL_MEDIA_PARTIAL_MESSAGE`; `saveLabel="Guardar cambios"` (detalle 2918); `InspectorCargarFotosDialog` 111. |
| V-5 | `pendingSaveCount` / `countUploadableQueueItems` **no** cuenta `error` con `archivoId`. Segundo Guardar puede **cerrar como éxito** sin reintentar esas fotos. | `actuacionManualMediaSave.ts` 10–14; `ActuacionMediaGallery.saveQueuedPhotos` 147; `handleSaveClick` 1747. En Cargar más fotos, `pending === 0` muestra «Seleccioná fotos para guardar.» |
| V-6 | Cola **solo en memoria**. Cerrar el modal (tras confirmar descarte), cambiar de pantalla, recargar o cerrar la pestaña pierde fotos no READY. Sin `beforeunload` en estos flujos. | `useMediaUploadCoordinator` (estado React). Cerrar edición: `setEditDraft(null)` desmonta el diálogo. |
| V-7 | Permisos de **Cargar más fotos** desalineados (ver §8). El botón de lista no mira `ui_policy` ni `ruta_item_id`. | `TableActuaciones.tsx` 645–655; cards móviles 149–157; presenter `puede_fotos = inspector_session and ruta_item_id`; media: `assert_current_user_can_access_ruta_item` (grupo de ruta). |
| V-8 | Sin timeout HTTP; 401 recarga a `/login` y pierde formulario y cola. | `apiClient.ts` (sin `timeout`; `window.location.assign("/login")`). |
| V-9 | Sin Error Boundary global ni telemetría. El panel de fotos sí tiene `MediaUploadPanelErrorBoundary`; **no** envuelve Guardar. | `main.tsx` 20–27. |
| V-10 | Idempotencia de fotos por SHA en servidor (reintentar la misma foto no duplica). Cargar actuación sigue sin clave de idempotencia en `commit-batch`. | Sin cambio respecto del relevamiento. |

Estados de una foto (cliente):

| Estado | Significado | ¿Persistió? |
|--------|-------------|-------------|
| Seleccionada / `pending` | En cola local, no hay intent | No |
| `preparing` / `uploading` / `verifying` | En vuelo | Intent puede ser PENDING en DB; objeto puede estar en el bucket |
| Enviada no confirmada (`error` + `archivoId`) | Hubo intent; complete no llegó a READY | PENDING o bytes huérfanos hasta limpieza |
| Confirmada (`ready` / listado servidor) | `POST .../complete` OK | Sí (READY) |

---

## 2. Hallazgos que ya fueron corregidos

- **Pantalla blanca con Chrome Translate (`insertBefore`)**: hotfix vigente. `index.html` (`lang="es"`, `translate="no"`, `notranslate` en html/body/#root/#portal); `AppButton` envuelve el rótulo; `MediaUploadProgress` marca `translate="no"`. Tests: `chromeTranslateOptOut.test.ts`, `AppButton.test.tsx`. QA de Luis en emulador y Moto G41. **No reabrir.**
- **Panel de progreso de subida**: existe y se usa en Editar, Completar trabajo y Cargar más fotos. No proponerlo como faltante.
- **Cerrar Completar trabajo durante la subida**: bloqueo / «Salir y pausar» (`completarTrabajoModalExitDuringUpload`). Distinto de Editar, que confirma descarte de **selección no subida**.
- El relevamiento de nov-2026 dejaba la causa del blanco como hipótesis; el caso Translate **ya no es pendiente**. Otras causas de blanco (OOM, 401, render fuera del panel) no están demostradas ni cubiertas.

---

## 3. Comportamientos no confirmados (solo código o sin entorno)

| Tema | Cómo probarlo |
|------|----------------|
| Segundo Guardar en Editar con `error`+`archivoId` cierra como éxito | QA: 2 fotos, cortar red en la 2.ª tras el intent; Guardar otra vez; Console + Network + galería. |
| Repetición de quitar acta (409 o no-op) | Editar quitando un acta, fallar fotos, Guardar de nuevo. |
| PUT OK y respuesta perdida (sin timeout el spinner no corta) | Throttle offline justo tras el PUT; reintentar; una sola actuación. |
| Inspector en `actuaciones_inspector` y no en el grupo de ruta → 403 al listar/subir | Cuenta de prueba; no hay test que una listado Mis trabajos + upload-intent. |
| Prevalencia en datos reales | Consulta de solo lectura autorizada (conteo, sin PII). |
| Google Translate real post-hotfix | QA Chrome 158 / Moto G41 (ya hecho por Luis; no repetido aquí). |

---

## 4. Pruebas ejecutadas

Destino backend verificado: `tests/conftest.py` fija `TEST_DATABASE_URL`, `assert_connected_database_is_test` y `MEDIA_STORAGE_PROVIDER=mock`.

**Aprobadas**

- Frontend vitest (12 archivos, **47 passed**): cascarón Translate, `AppButton`, `MediaUploadProgress`, `actuacionManualMediaSave`, pipeline, reconciliación, secuencia PUT→fotos, refresh diferido, Inspector Cargar más fotos (cierre solo en `success`), Completar (orden cierre→fotos, salida durante subida).
- Backend: `test_inspector_a_detalle_b_403` (inspector de otro grupo → 403); `test_media_storage_1a.py` (4 tests, incluye 403 de list/delete ajeno).

**Fallidas (fuera de foco; no tocadas)**

- `test_inspector_completar_trabajo_v1_1_3.py`: `test_resumen_mismo_scope_que_listado` (StopIteration) y `test_inspector_a_cerrar_b_403_sin_negocio` (mock desactualizado). El 403 de detalle sí pasó.

**No ejecutadas**

- Subida real de fotos, Chrome Translate, teléfono, producción.
- Flujo completo Editar con red cortada (no hay jsdom ni stack de subida real en este ticket).
- Suite media 1b (cupo 12 vs 20, ya conocido).

---

## 5. Archivos y funciones

**Editar**

- `ActuacionDetalleDialog.tsx` — `handleSaveClick`, `tryCloseDialog`
- `TableActuaciones.tsx` — `handleDialogSave`, `handleEditSaveSessionEnd`
- `submitActuacionRow.ts` — PUT, quitar actas
- `actuacionSaveFeedback.ts` — `MENSAJE_EDICION_OK`, `MENSAJE_ERROR_GRAVE`
- `ActuacionMediaGallery.tsx` — `saveQueuedPhotos`, `pendingSaveCount`, `manualSave` (sin `onRetry` en el panel)
- `actuacionManualMediaSave.ts` — `runManualMediaSave`, copy de parcial
- `MediaUploadProgress.tsx` — progreso existente
- `mediaUploadPipeline.ts` — intent / PUT / complete, concurrencia 1

**Cargar más fotos**

- `InspectorCargarFotosDialog.tsx` — solo fotos, `CONTINUAR SUBIDA` si `uploadable > 0`
- Lista: `TableActuaciones.renderRowActionsCb`, `ActuacionesGestionMobileCardList`

**Permisos (sin cambiar)**

- `actuacion_gestion_seguimiento_presenter.py` — `puede_gestionar_fotos_propias`
- `completar_trabajo_ruta_item_access.py` — grupo de ruta
- `ruta_item_resolver.py` — `ruta_item_id` o `None`

**Protección**

- `MediaUploadPanelErrorBoundary.tsx` (solo galería)
- `index.html` / `AppButton.tsx` (Translate, ya QA)

---

## 6. Propuesta de alcance — Etapa 1 (estados y mensajes de Editar)

Solo frontend de Editar. **No** tocar pipeline, SHA, cupos, galerías ni Completar trabajo.

1. Tras PUT OK, no usar *«No se pudo guardar la actuación»* si falla lo posterior.
2. Distinguir: datos guardados + fotos subiendo (el panel ya cubre el progreso); datos guardados + fotos parciales; datos y fotos OK (`MENSAJE_EDICION_OK` solo al final).
3. Alinear el botón y el toast: no pedir CONTINUAR SUBIDA si el botón sigue siendo Guardar cambios.
4. Criterios: sin fotos, el mensaje de éxito no cambia; con fotos OK, un solo éxito al cerrar; con parcial, el modal permanece y el texto no niega el PUT.

---

## 7. Etapa 1 sola vs. reintentar solo fotos

| Si Etapa 1 va sola | Riesgo |
|--------------------|--------|
| Mensajes honestos, mismo Guardar | El inspector entiende que los datos están, pero el segundo toque **repite el PUT** y puede repetir actas. |
| Reutilizar el copy de Cargar más fotos | Mentira: no hay CONTINUAR SUBIDA en Editar. |

| Si «solo fotos» va sola | Riesgo |
|-------------------------|--------|
| Segundo toque sin PUT | El usuario sigue leyendo *«No se pudo guardar»* o *«editada correctamente»* a destiempo. |

**Recomendación: un solo ticket de Editar** que, después del primer PUT OK:

- actualice `editOriginalRow` / baseline;
- si la cola está incompleta, el botón pase a reintentar **solo** `saveQueuedPhotos` (y cuente también `error` con `archivoId`, o resetee a `pending` como `retryItem`);
- aplique los mensajes del §6.

Así no se toca el pipeline ni el orden «datos luego fotos». Completar trabajo ya separa cierre e evidencias pendientes; no mezclarlo.

---

## 8. Decisión pendiente — Cargar más fotos

**No se cambian permisos en esta etapa.**

| Superficie | Hoy |
|------------|-----|
| Lista / cards (inspector) | Botón **siempre** visible. |
| Detalle | `puede_gestionar_fotos_propias` = inspector + `ruta_item_id`. |
| API media | Inspector debe estar en **grupo de la ruta**. Mis trabajos lista por `actuaciones_inspector`. |
| Sin `ruta_item_id` | Modal: «No hay ítem de ruta asociado…»; Guardar deshabilitado. Restricción deliberada (media anclada al ítem). El defecto es **mostrar el botón**. |
| Inspector en la actuación y no en el grupo | Puede ver el botón y recibir **403** al listar o subir. Defecto de alineación, no regla de negocio documentada. |

Hace falta decidir: el criterio es **grupo de ruta**, **asignación a la actuación**, o **ambos**. Después alinear botón, `ui_policy` y `assert_current_user_can_access_ruta_item`. Hasta entonces no implementar.
