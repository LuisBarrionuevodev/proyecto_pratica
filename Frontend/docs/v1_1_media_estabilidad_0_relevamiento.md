# V1.1-MEDIA-ESTABILIDAD.0 — Relevamiento de carga de fotos y guardado en móviles

**Tipo:** relevamiento (sin cambios de código productivo, migraciones, configuración ni tests).
**Fecha:** 2026-11-16.
**Alcance:** Cargar actuación, Editar actuación, Completar trabajo → fotos, Mis trabajos → Cargar más fotos, backend de media.
**Escritura realizada:** solo este documento.

---

## 1. Resumen ejecutivo

### Confirmado por código o por tests

1. **No hay Error Boundary global.** `main.tsx` monta `<App />` sin boundary, y no hay handlers `window.onerror` / `unhandledrejection` ni telemetría de errores del navegador (no hay Sentry ni similar). Con React 19, una excepción de render **fuera** del panel de fotos desmonta todo el árbol: el resultado es literalmente una **pantalla blanca**, y no queda ningún registro remoto. El único boundary (`MediaUploadPanelErrorBoundary`) envuelve solo la galería de fotos.
2. **Cargar actuación no sube fotos.** El modal vigente (`CargarActuacionNuevaModal`) solo hace `POST /grid/start` → `POST /grid/validate-row` → `POST /grid/commit-batch`. Una pantalla blanca en Cargar actuación **no puede venir de la subida de fotos**.
3. **Guardar datos y subir fotos no son atómicos en ningún canal.** En Editar actuación, el `PUT /actuaciones/:id` se confirma primero y después se suben las fotos de a una (intent → PUT al bucket → complete). En Completar trabajo, el cierre se confirma primero y las fotos van después. Una falla posterior deja la actuación guardada y las fotos pendientes o parciales.
4. **Los permisos de "Cargar más fotos" no coinciden con los de acceso a la actuación.** Mis trabajos y el detalle filtran por `actuaciones_inspector`; los endpoints de media exigen que el inspector integre el **grupo de la ruta** (`ruta_grupo_inspector`). `ui_policy.puede_gestionar_fotos_propias` solo verifica sesión de inspector y que exista `ruta_item_id`. Si un inspector figura en la actuación pero no en el grupo de la ruta, ve el botón habilitado y recibe 403 al cargar la galería o al guardar.
5. **El botón "Cargar más fotos" de la lista se muestra siempre** para el inspector, sin mirar `ui_policy` ni `ruta_item_id`. Las actuaciones sin ítem de ruta (por ejemplo, las cargadas por Cargar actuación) abren un modal que dice "No hay ítem de ruta asociado para archivos." con el guardado deshabilitado.
6. **No hay compresión, reducción ni `capture` en el cliente.** Se sube la foto original (hasta 10 MB por imagen). Las vistas previas usan `URL.createObjectURL` sobre el archivo original, y se liberan con `revokeObjectURL` al quitar, limpiar o resetear.
7. **El SHA-256 se calcula en el cliente leyendo el archivo completo en memoria** (`sha256File.ts`: `file.arrayBuffer()` + `crypto.subtle.digest`). Esto ocurre justo después de tocar Guardar, una foto por vez (concurrencia 1).
8. **No hay timeout HTTP** en `apiClient` (axios) ni en el XHR de subida. Una red móvil que "cuelga" deja el botón en estado de carga sin límite de tiempo.
9. **Un 401 provoca una navegación completa** (`window.location.assign("/login")`). Si el token venció (TTL por defecto 8 h, `JWT_ACCESS_TOKEN_MINUTES`), el primer Guardar recarga la página: el formulario y la cola de fotos en memoria se pierden, y **no se guardó nada** (el backend rechazó la request).
10. **Cargar actuación no tiene idempotencia** en `commit-batch` (no hay clave por `batch_id`/`row_id`). Si la respuesta se pierde y el usuario reintenta, solo lo protege la unicidad de los números de acta.
11. **La subida de fotos sí es idempotente** en el servidor: hay un índice único `(ruta_item_id, categoria, content_sha256)`, se reutilizan intents PENDING/READY con el mismo hash, y `complete` no hace nada si el archivo ya está en READY. Reintentar la misma foto no la duplica.
12. **Las colas de fotos viven solo en memoria.** No hay IndexedDB ni localStorage. Recargar, cerrar la pestaña o que el sistema operativo descarte la pestaña en segundo plano pierde la selección no subida. Durante la subida no hay aviso `beforeunload`.

### Riesgos principales

- Pantalla blanca **sin diagnóstico posible**: no hay boundary global ni telemetría, así que hoy no se puede saber qué excepción se produjo.
- **Incertidumbre del inspector** sobre qué quedó guardado: datos guardados y fotos no, o al revés. Puede llevar a recargar actuaciones (posible duplicado en Cargar actuación) o a abandonar la evidencia.
- **Fotos imposibles de cargar en trabajos antiguos o reasignados** por la diferencia de permisos del punto 4.

### Sigue sin demostrarse

- La **causa** de la pantalla blanca reportada. Ninguna hipótesis está confirmada: falta la traza del error en un teléfono afectado (ver §5 y §8).
- Si la memoria es un factor real en los teléfonos afectados.
- Cuántas actuaciones reales caen en la diferencia de permisos o no tienen `ruta_item_id` (requiere una consulta de solo lectura que no se ejecutó).

---

## 2. Mapa de flujos y secuencia real de escrituras y lecturas

Convención: **[DB]** = escritura confirmada en base de datos; **[S3]** = escritura en el bucket; **[UI]** = solo estado del cliente.

### 2.1 Cargar actuación (crear)

Ruta `/cargarActuacion` → `LazyCargarActuaciones` (carga diferida, `routing/lazyRouteModules.tsx`) → `Containers/CargarActuaciones/index.tsx` → `Components/CargarActuacionNuevaModal.tsx`.

| # | Paso | Función | Efecto |
|---|------|---------|--------|
| 1 | Abrir el modal | botón "Nueva actuación" → `setOpen(true)` | [UI]; carga de catálogos con flag `cancelled` |
| 2 | Tocar Guardar | `handleSubmit` | `setFieldErrors({})` |
| 3 | Lote | `ensureBatch()` → `POST /grid/start` (solo la primera vez) | estado del lote en el servidor |
| 4 | `setLoading(true)` | botón deshabilitado (`loading \|\| …`) | [UI] |
| 5 | Validar | `submitCargarActuacionNuevaRow` → `POST /grid/validate-row` | sin escritura |
| 6 | Confirmar | `POST /grid/commit-batch` (`grid/routes/batch.py::commit_batch` → `handler.create_fn`) | **[DB]** actuación, OT, domicilio, contribuyente y actas |
| 7 | Resultado | `runCargarActuacionPostSaveCleanup`: toast, `resetForm`, `closeModal` | [UI] |

- **No hay fotos.** El componente legado `TablaCargarActuacionesGlideStyled.tsx` no está montado en la ruta.
- **Atómico:** el commit de cada fila es una transacción del servicio de creación. `commit-batch` continúa con otras filas si una falla, pero acá el lote tiene una sola fila.
- **Ventana de doble toque:** `ensureBatch()` se ejecuta **antes** de `setLoading(true)`. La primera vez el botón queda deshabilitado por `startingBatch && !batchId`, así que el riesgo es bajo. Ver H-6.

### 2.2 Editar actuación (Gestión y Mis trabajos → "Editar datos")

`ActuacionesContainer.tsx` → `TableActuaciones.tsx` → `{editDraft && <ActuacionDetalleDialog open … />}`. El diálogo se **desmonta** al cerrarse (`editDraft = null`).

| # | Paso | Función | Efecto |
|---|------|---------|--------|
| 1 | Abrir | `loadActuacionDetalle(row, "edit")` → `GET` detalle de gestión | primero muestra la fila de lista; después el detalle. Sin abort si se cierra antes |
| 2 | Seleccionar fotos | `ActuacionMediaGallery` (`manualSave`) → `useMediaUploadCoordinator.addFiles` | [UI] cola en estado React y `createObjectURL` |
| 3 | Tocar Guardar | `ActuacionDetalleDialog.handleSaveClick` | validaciones locales, `actaFlushRegistry` |
| 4 | (opcional) | `corregirCierreOficio` → `PUT /actuaciones/:id/corregir-cierre-oficio` | **[DB]** antes del PUT principal |
| 5 | Guardar datos | `onSave` = `TableActuaciones.handleDialogSave` → `submitActuacionRow` → (validate-row opcional) → `postQuitarActaCanalActas` por acta → `PUT /actuaciones/:id` | **[DB]** |
| 6 | Parche de lista | `onActuacionListPatch(stripActuacionRowForListStorage(prepareActuacionGestionModalRow(updatedRow)))` → `fusionarActuacionEnLista` | [UI] **re-render de la grilla con la fila del PUT** |
| 7 | Subir fotos | `gallery.saveQueuedPhotos()` → `runManualMediaSave` → por foto: SHA-256 → `POST /ruta-items/:id/archivos/upload-intents` **[DB PENDING]** → XHR `PUT` presignado **[S3]** → `POST /archivos/:id/complete` **[DB READY]** | concurrencia 1 |
| 8 | Conciliar | `reconcileMediaQueueAfterUploadAttempt` → `GET /ruta-items/:id/archivos` | lectura |
| 9 | Cierre de sesión | `onEditSaveSessionEnd("success" \| "aborted")` | éxito: toast, `onRefresh` (refetch de lista) y cierre; parcial: el modal queda abierto |

- **No atómico** entre los pasos 4, 5 y 7. Con éxito en 5 y falla en 7, la actuación queda guardada y las fotos quedan en error o PENDING.
- Si el paso 7 se interrumpe, **volver a tocar Guardar repite los pasos 4–6** (el `PUT` y "quitar acta"), porque `editOriginalRow` no se actualiza después del primer PUT. Ver H-7.
- Cualquier excepción no prevista entre los pasos 5 y 9 muestra `MENSAJE_ERROR_GRAVE` = "No se pudo guardar la actuación." **aunque el PUT ya se haya confirmado** (catch final de `handleSaveClick`).

### 2.3 Completar trabajo → fotos

`Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx` (carga eager), cola en `features/media/rutaItemMediaUploadStore.ts` (un `Map` a nivel módulo, por `ruta_item_id`).

| # | Paso | Función | Efecto |
|---|------|---------|--------|
| 1 | Fotos "antes" del cierre | `handleSafeAddMediaFiles` → store | [UI] (sobrevive al cerrar y reabrir el modal en la misma SPA; **no** sobrevive a una recarga) |
| 2 | Finalizar | `runCompletarTrabajoFinalizeFlow`: validar → `submitCierre` | — |
| 3 | Cierre | `POST /actuaciones/completar-trabajo/cerrar/:ruta_item_id` con `idempotency_key` (UUID por apertura del modal) y `evidencias_pendientes_al_cierre` | **[DB]** actuación, ítem e iniciador en una transacción |
| 4 | Subir | `uploadPendingMedia` → mismo pipeline que en 2.2 | [DB]/[S3] por foto |
| 5 | Resultado | todo OK → éxito; falla de fotos → `success_evidencias_pendientes` ("Trabajo guardado…") | [UI] |
| 6 | Falla de red en el cierre | `tryRecoverCompletarTrabajoTrasErrorRed` → `GET detalle` | detecta si el cierre ya persistió |
| 7 | Solo fotos (reabrir) | `isCompletarTrabajoSoloFotosMode` → `runCompletarTrabajoSoloEvidenciasFlow` | [DB]/[S3] |
| 8 | "Finalizar por ahora" | `POST /ruta-items/:id/fotos/finalizar-por-ahora` (exige `FINALIZADO`) | **[DB]** |

- Es el canal **mejor protegido**: idempotencia de cierre, recuperación ante error de red, bloqueo de cierre del modal durante la subida y opción "Salir y pausar".

### 2.4 Mis trabajos → "Cargar más fotos"

`TableActuaciones.renderRowActionsCb` (y `ActuacionesGestionMobileCardList`) → `loadActuacionDetalle(row, "fotos")` → `InspectorCargarFotosDialog` → `ActuacionMediaGallery manualSave` con `upload_origin = MIS_TRABAJOS`.

| Condición | Comportamiento |
|-----------|----------------|
| Inspector (`inspectorSelfService`) | **Botón visible en todas las filas** (no consulta `ui_policy`) |
| Detalle con `puede_gestionar_fotos_propias=false` | No aparece en el selector del detalle, pero el botón de la fila sigue abriendo el modal |
| `ruta_item_id == null` | El modal se abre con "No hay ítem de ruta asociado…" y el guardado deshabilitado |
| Inspector en `actuaciones_inspector` pero no en `ruta_grupo_inspector` | El modal se abre; `GET archivos` responde **403** ("No se pudieron cargar los archivos."); el guardado responde 403 |
| Falla el `GET` de detalle | Toast "No se pudo cargar el detalle de la actuación." y el modal se cierra |
| Cerrar con selección pendiente | Confirmación "¿Salir sin guardar las fotos seleccionadas?" |
| Cerrar durante la subida | Bloqueado (`isUploadInProgress`) |
| Recargar o cerrar la pestaña | Se pierde la selección; no hay aviso |

### 2.5 Backend de media

- Endpoints en `Backend/app/domains/media/routes/`: `upload_intent.py`, `complete.py`, `list_archivos.py`, `delete_archivo.py`, `download_url.py`, `finalizar_fotos_por_ahora.py`. Todos con `@jwt_required()`.
- **No hay multipart.** Los bytes van directo del navegador al bucket con una URL presignada (TTL por defecto 600 s).
- Validación: MIME por categoría, tamaño declarado (10 MB para imágenes, 15 MB para documentos), cupos (10/10/20), y en `complete`: HEAD, tamaño, content-type, **descarga completa** del objeto, magic bytes y SHA-256.
- Estados de `Archivo`: `PENDING → READY | REJECTED | DELETED`. Los PENDING huérfanos se limpian con `flask cleanup-pending-media` (24 h por defecto).
- Gunicorn: `--workers 2 --timeout 120` (`Procfile`, `railway.toml`). Las subidas no pasan por gunicorn; `complete` sí, y descarga el objeto completo.
- `crear_upload_intent` **no** verifica `estado_ruta_item` ni `fotos_pendientes_cerradas_at`, solo el acceso al ítem.

### 2.6 Qué es atómico

| Operación | ¿Atómica? |
|-----------|-----------|
| `commit-batch` de una fila (Cargar actuación) | Sí (por fila) |
| `PUT /actuaciones/:id` | Sí |
| `corregir-cierre-oficio` + `PUT` | **No** (dos requests) |
| Cierre de Completar trabajo | Sí, e idempotente |
| Datos + fotos (cualquier canal) | **No** |
| Una foto (intent → S3 → complete) | No, pero recuperable: idempotente por SHA, con limpieza de PENDING |
| Refresco de la galería y de la lista | Independiente; su falla no revierte nada |

---

## 3. Matriz de escenarios

Leyenda: **T** = cubierto por test automatizado existente · **M** = probado manualmente en este relevamiento · **P** = pendiente.
En este relevamiento **no se hizo ninguna prueba manual en navegador ni en teléfono**, por eso no hay ninguna celda "M".

| Escenario | Cargar actuación | Editar actuación | Completar trabajo | Cargar más fotos |
|-----------|:---:|:---:|:---:|:---:|
| Guardar sin fotos | T (submit) | T (orden PUT→fotos) | T (flujo de finalización) | n/a |
| 1 foto | n/a | P | T (pipeline) | T (guardado manual) |
| Varias fotos | n/a | P | T (concurrencia 1) | T |
| Fotos grandes (cerca de 10 MB) | n/a | P | P | P |
| Galería con evidencia previa / cupo | n/a | P | T (cupo) | P |
| Una foto falla entre varias | n/a | T (`partial`) | T (`success_evidencias_pendientes`) | T (`partial`) |
| Falla el refresco de la galería tras subir | n/a | T (`refreshFailed`) | P | T |
| Red lenta | P | P | P | P |
| Desconexión y reconexión | P | P | T (recuperación de cierre, parcial) | P |
| Doble toque en Guardar | P | P | T (idempotencia de cierre, backend) | P |
| Cerrar el modal durante la subida | n/a | P | T (bloqueo o pausa) | T (bloqueo, por lectura de código) |
| Recargar la página durante la subida | P | P | P | P |
| Token vencido (401) al guardar | P | P | P | P |
| Reabrir después de un parcial | n/a | P | T (modo solo fotos) | P |
| Inspector fuera del grupo de la ruta | n/a | P | T (backend 403) | **P (defecto por código)** |
| Actuación sin `ruta_item_id` | n/a | P | n/a | P |
| Excepción de render tras guardar | P | P | P | P |
| Teléfono Android de gama baja real | P | P | P | P |
| iOS Safari real | P | P | P | P |
| Simulación móvil (DevTools) | P | P | P | P |

---

## 4. Hallazgos individuales

Severidad: **Alta** = puede perder trabajo o bloquear la operación · **Media** = confusión o recuperación manual · **Baja** = higiene o rendimiento.

### F-1 · Alta · Sin Error Boundary global ni captura de errores del cliente
- **Evidencia:** `Frontend/src/main.tsx` (líneas 20–27) renderiza `<App />` sin boundary. No aparecen `componentDidCatch` fuera de `features/media/components/MediaUploadPanelErrorBoundary.tsx`, ni `window.onerror`, `unhandledrejection`, `onUncaughtError` o Sentry en `Frontend/`.
- **Impacto:** cualquier excepción de render en la grilla, el diálogo o el layout deja la pantalla en blanco y no queda registro.
- **Reproducción:** forzar un `throw` en un renderer de celda de `TableActuaciones` (solo en local) → pantalla blanca.

### F-2 · Alta · Diferencia de permisos en "Cargar más fotos"
- **Evidencia:** el acceso a la actuación usa `actuaciones_actuacion_inspector_scope.py::assert_inspector_puede_acceder_actuacion` → `scope_actuaciones_to_inspector` (`actuaciones_inspector`). La media usa `completar_trabajo_ruta_item_access.py::assert_current_user_can_access_ruta_item` → `scope_ruta_items_to_inspector` (`ruta_grupo_inspector`). La política de UI está en `actuacion_gestion_seguimiento_presenter.py` línea 101: `puede_fotos = bool(inspector_session and ruta_item_id is not None)`.
- **Impacto:** un inspector que figura en la actuación pero no en el grupo (por ejemplo, agregado como acompañante, grupo reasignado o rutas antiguas) ve el botón habilitado y recibe 403. Es un **defecto**, no una restricción deliberada: la política de UI promete algo que el backend niega.
- **Reproducción:** con una base de test, crear un ítem en un grupo A, vincular la actuación al inspector X que no está en A, y entrar como X a Mis trabajos → Cargar más fotos.

### F-3 · Media · Botón "Cargar más fotos" sin condiciones en la lista
- **Evidencia:** `TableActuaciones.tsx` líneas 645–655 (y la lista móvil) renderizan el botón para todo `inspectorSelfService`. `InspectorCargarFotosDialog.tsx` línea 113 deshabilita el guardado si `rutaItemId == null`.
- **Impacto:** el usuario abre un modal que no puede usar. Que las actuaciones de Cargar actuación no tengan ítem de ruta es una **restricción deliberada** (la media se ancla en `ruta_item`); el defecto es mostrar el botón.

### F-4 · Media · Mensaje de "no se guardó" aunque el PUT ya se confirmó
- **Evidencia:** en el `catch` de `ActuacionDetalleDialog.handleSaveClick` (líneas 1761–1764) se muestra `MENSAJE_ERROR_GRAVE` = "No se pudo guardar la actuación." para cualquier excepción, incluidas las que ocurren después de `putOk === true`.
- **Impacto:** el inspector cree que perdió los datos y vuelve a cargar o a editar.

### F-5 · Media · Reintentar Guardar después de un parcial repite el PUT y las acciones de actas
- **Evidencia:** después de un PUT exitoso con `deferDialogClose`, `editOriginalRow` y `editBaseline` no se actualizan con `result.updatedRow` (`TableActuaciones.handleDialogSave`, líneas 395–408). Con `outcome="partial"` el diálogo sigue abierto y el único botón es "Guardar", que vuelve a llamar a `onSave`.
- **Impacto:** se repiten `postQuitarActaCanalActas` y `corregirCierreOficio` contra datos que ya cambiaron. Puede fallar (por ejemplo, porque el acta ya fue quitada) **antes** de llegar a reintentar las fotos. Consecuencia exacta no verificada: ver H-7.

### F-6 · Media · Sin timeout de red
- **Evidencia:** `Frontend/src/api/apiClient.ts` (`axios.create` sin `timeout`); `mediaUploadPipeline.ts::putFileToPresignedUrl` sin `xhr.timeout`.
- **Impacto:** con 3G intermitente, Guardar puede quedar girando sin fin; el usuario recarga o cierra, y el estado queda desconocido.

### F-7 · Media · Un 401 recarga la página y pierde el formulario y la cola de fotos
- **Evidencia:** `apiClient.ts` líneas 63–81 → `window.location.assign("/login")`. TTL del token: `Backend/app/domains/usuarios/security/jwt.py` (480 min por defecto). No hay refresh token.
- **Impacto:** si la sesión vence durante la jornada, el Guardar **no persiste nada** y lo escrito se pierde. En un teléfono lento la recarga se ve unos segundos en blanco antes del login.

### F-8 · Media · Colas de fotos solo en memoria, sin aviso al salir
- **Evidencia:** `rutaItemMediaUploadStore.ts` (un `Map` en memoria) y `useMediaUploadCoordinator` (estado React). `beforeunload` solo aparece en `CargarRelevamientos`.
- **Impacto:** Android e iOS descartan pestañas en segundo plano, por ejemplo al abrir la cámara nativa desde el selector de archivos. Al volver, la página se recarga y la selección desapareció.

### F-9 · Media · Cargar actuación sin idempotencia ante respuesta perdida
- **Evidencia:** `grid/routes/batch.py::commit_batch` crea si `normalized.id is None`, sin clave de idempotencia. `store.clear_row_key` corre solo cuando el commit sale bien.
- **Impacto:** si se corta la red después del commit y el usuario reintenta, puede crearse una segunda actuación. Las actas con número quedan protegidas por la unicidad (`attach/comprobacion.py`, `attach/oficio.py`); una actuación **sin actas** no.

### F-10 · Baja · Fotos originales sin reducir; SHA-256 con el archivo entero en memoria
- **Evidencia:** no hay canvas, `createImageBitmap` ni compresión en `features/media`. `sha256File.ts` usa `file.arrayBuffer()`. Las vistas previas de 48×48 px cargan el original con `createObjectURL` (`MediaUploadQueue.tsx` líneas 58–63).
- **Impacto:** más datos móviles, subidas más lentas y más memoria por miniatura (el navegador decodifica la imagen completa). El efecto en los teléfonos afectados **no está medido**.

### F-11 · Baja · Re-render por cada evento de progreso
- **Evidencia:** `useMediaUploadCoordinator.patchItem` hace `setItems` + `setSession` en cada `onprogress`. En `InspectorCargarFotosDialog`, `onQueueStatsChange={setQueueStats}` recibe un objeto nuevo en cada cambio.
- **Impacto:** trabajo extra en el hilo principal mientras se sube. En el diálogo de edición no se propaga al componente padre (muy grande, unas 3000 líneas).

### F-12 · Baja · Si falla el refetch de la lista después de guardar, la grilla desaparece
- **Evidencia:** `useActuacionesFiltradas.buscar`: en el `catch` hace `setActuaciones([])` y `setMeta(null)`; `ActuacionesContainer` renderiza la tabla solo con `hasSearched && meta`.
- **Impacto:** el guardado salió bien, pero la lista se vacía y aparece "Error al cargar actuaciones". No es una pantalla blanca, pero puede confundirse con una pérdida.

### F-13 · Baja · Tests existentes que fallan (antes de este relevamiento)
- `Backend/tests/test_media_storage_1b.py::test_foto_inspeccion_intent_autorizado_cupo_12`: espera 422 en la foto 13, pero el cupo vigente es 20 (`integrations/media_storage/config.py`). El test quedó desactualizado.
- `Frontend/src/Containers/CompletarTrabajos/utils/completarTrabajoEvidenciasConfirm.test.ts` ("cola all READY…"): espera que un ítem `error` con `archivoId` cuente como terminado, pero `isLocalCompletarTrabajoMediaQueueFinished` devuelve `false`. El código es el criterio más conservador (no da por terminada una foto con error). Falta decidir cuál es el comportamiento correcto.

### F-14 · Baja · El backend acepta intents sin verificar el estado del ítem
- **Evidencia:** `media_upload_intent_service.py::crear_upload_intent` solo llama a `assert_current_user_can_access_ruta_item`.
- **Impacto:** hoy no genera fallas visibles; es una restricción que depende solo del frontend.

---

## 5. Hipótesis sobre la pantalla blanca (separadas de los hechos)

Orden por probabilidad × impacto según la evidencia disponible. **Ninguna está confirmada.**

| # | Hipótesis | A favor | En contra | Experimento mínimo |
|---|-----------|---------|-----------|--------------------|
| **H-1** | Una excepción de render después de guardar desmonta toda la app (F-1). Candidatos: la fila del PUT fusionada en la grilla (`fusionarActuacionEnLista`) con una forma distinta a la del listado, o el refetch y re-render posterior | No hay boundary global; afecta a **ambos** canales reportados (Cargar y Editar); no depende de las fotos; el síntoma es exactamente "blanco" | No hay traza del error; los tests de submit pasan; no se conoce el campo que fallaría | Boundary global con registro anónimo (ticket E-1) **o** conectar el teléfono por USB con depuración remota (Chrome `chrome://inspect`, Safari Web Inspector) y leer la consola en el momento del blanco |
| **H-2** | Recarga por 401 con el token vencido (F-7) | Sucede justo al tocar Guardar (primera request después de mucho tiempo); en red lenta se ve blanco hasta que carga el login | El usuario normalmente terminaría viendo el login y lo reportaría como "me sacó"; con 8 h de TTL es menos frecuente | Revisar los logs del backend de los días reportados: 401 en `PUT /actuaciones/*` o `POST /grid/*` con `msg` "Token has expired". Probar con `JWT_ACCESS_TOKEN_MINUTES=5` en local |
| **H-3** | El sistema operativo descarta la pestaña por memoria (renderer OOM) al combinar varias fotos originales, miniaturas decodificadas y el `arrayBuffer` del SHA (F-10, F-8) | Sin compresión; fotos de 3–10 MB; teléfonos de gama baja; ocurre al guardar, cuando se lee cada archivo | **No explica Cargar actuación**, que no tiene fotos; con concurrencia 1, solo un `arrayBuffer` vive a la vez | En el teléfono afectado: Editar con 0, 1 y 8 fotos grandes, mirando la memoria en depuración remota. Si la pestaña se recarga sola, es OOM o descarte |
| **H-4** | Fallo al cargar un chunk diferido después de un deploy (Cargar actuación es `lazy`), sin boundary que lo capture | Cargar actuación está en carga diferida; Vercel sirve los hashes nuevos | El chunk de la ruta se carga al **entrar**, no al Guardar; al guardar no hay `import()` dinámico (verificado con grep) | Buscar en la consola "Failed to fetch dynamically imported module" o `vite:preloadError`; reproducir abriendo la app, desplegando y navegando |
| **H-5** | La pestaña se cuelga (no está en blanco, está congelada) por una red sin timeout (F-6) | No hay timeout | Un cuelgue suele verse como un spinner, no como blanco | Throttling "Offline" en DevTools justo después de tocar Guardar |
| **H-6** | Doble toque durante `ensureBatch` o `corregirCierreOficio`, antes de que el botón se deshabilite | El primer `await` ocurre antes de `setLoading` o `setEditSaving` | Produce duplicados o errores, no blancos | Test con dos clics sincrónicos sobre el botón (Testing Library) y contar las llamadas a la API mockeada |
| **H-7** | Reintentar Guardar después de un parcial falla en "quitar acta" o en la corrección de oficio (F-5) | La base del diff no se actualiza | Requiere un parcial y cambios de actas en la misma edición | Test unitario de `handleDialogSave` llamado dos veces con el mismo `editOriginalRow` y `actasClearedByOficioCorrection` |

**Advertencia:** la pantalla blanca no implica que no se haya guardado. Con H-1 el PUT o el commit **ya se confirmaron**; con H-2 **no** se guardó nada; con H-3 depende del momento (datos sí, fotos parcial).

---

## 6. Pérdida de datos, duplicados y recuperabilidad

| Interrupción en… | ¿Qué persistió? | Riesgo | Cómo lo verifica hoy el usuario |
|------------------|-----------------|--------|----------------------------------|
| Cargar actuación, antes del commit | Nada | Perder lo escrito (no hay borrador) | Buscar en Gestión / Mis trabajos |
| Cargar actuación, commit OK y respuesta perdida | Actuación completa | **Duplicado** si reintenta (F-9) | Buscar por OT o por número de acta |
| Editar, durante `corregir-cierre-oficio` | Corrección de oficio sí, PUT no | Estado intermedio | Reabrir el detalle |
| Editar, PUT OK y fotos sin empezar | Datos sí, fotos no | Perder la selección (memoria) | Galería vacía al reabrir |
| Editar, fotos a mitad de camino | Datos y las fotos READY | Las fotos PENDING se limpian en 24 h; la selección local se pierde | Galería: solo aparecen las READY |
| Completar, cierre OK y fotos fallidas | Cierre y `evidencias_pendientes_abiertas=true` | Bajo; el banner de pendientes avisa | Banner "fotos pendientes" y modo solo fotos |
| Cualquier canal con 401 | Nada de esa request | Perder el formulario | Reingresar |
| Pestaña descartada o recargada | Lo confirmado hasta ese momento | Perder la cola local | Reabrir y revisar |

**Duplicados de fotos:** protegidos en el servidor por el SHA-256 (índice único y reutilización de intent). Un archivo **re-codificado** (por ejemplo, otra captura de la misma escena) no se considera duplicado, y está bien que así sea.

**Duplicados de actuaciones:** solo existe protección en Completar trabajo (`idempotency_key`). En Cargar actuación la protección es parcial (unicidad de actas).

---

## 7. Plan de implementación (tickets pequeños)

### A. Estabilización urgente

**E-1 · Boundary global y registro anónimo de errores del cliente** *(primer ticket recomendado)*
- Alcance: un `AppErrorBoundary` alrededor de `<App />` (y del `Suspense` de `AppLayout`) con una pantalla de recuperación ("Algo falló. Tus datos pueden haberse guardado. Revisá Mis trabajos antes de volver a cargar." + botones "Ir a Mis trabajos" y "Recargar"). Registro de `window.onerror` y `unhandledrejection`, más `onUncaughtError` de `createRoot`, hacia un endpoint propio o la consola con un código corto copiable. **Sin datos personales:** solo ruta, componente, tipo de error, un id de actuación opcional y la versión del build.
- Dependencias: ninguna.
- Aceptación: un `throw` forzado en una celda muestra la pantalla de recuperación, no el blanco; queda un registro sin PII.
- Regresión: vitest del boundary; los tests existentes de Actuaciones y Completar siguen pasando.
- *Por qué primero:* convierte la pantalla blanca en un error diagnosticable y confirma o descarta H-1, H-3 y H-4 con datos reales.

**E-2 · Mensajes de resultado que distinguen datos de fotos (Editar)**
- Alcance: en `handleSaveClick`, separar el `catch` anterior y el posterior a `putOk`. Después del PUT, nunca mostrar "No se pudo guardar la actuación"; mostrar los mensajes de §7-UX.
- Aceptación: si las fotos lanzan una excepción después del PUT, el mensaje dice "Datos guardados; fotos pendientes".
- Regresión: `actuacionDetalleSaveSequence.test.ts` más un test nuevo.

**E-3 · Reintentar solo las fotos después de un parcial (Editar)**
- Alcance: cuando `outcome="partial"`, el botón principal pasa a "CONTINUAR SUBIDA" y solo llama a `saveQueuedPhotos`. Actualizar `editOriginalRow` y `editBaseline` con `updatedRow`.
- Dependencia: E-2.
- Aceptación: el segundo toque no genera un `PUT` ni "quitar acta" (verificado con mocks).

**E-4 · Unificar permisos de "Cargar más fotos"**
- Alcance: decidir la regla (grupo de la ruta **o** `actuaciones_inspector`). Alinear `puede_gestionar_fotos_propias` con `assert_current_user_can_access_ruta_item`, y que el botón de la lista use `ui_policy` (o un flag en el listado). Ocultar o explicar el caso sin `ruta_item_id`.
- Requiere antes una **consulta de solo lectura** en producción (con autorización) para contar los casos afectados.
- Aceptación: no queda ningún caso con botón habilitado y 403. Tests de backend para el inspector dentro y fuera del grupo.
- No modifica Completar trabajo.

**E-5 · Timeouts y manejo explícito de "sin respuesta"**
- Alcance: timeout en `apiClient` (por ejemplo, 30 s en JSON) y en el XHR (por ejemplo, 120 s o según el tamaño). Mensaje "No sabemos si se guardó; revisá antes de reintentar", con acción de verificación (GET del detalle).
- Aceptación: con throttling offline, el botón vuelve a estar disponible en ≤ timeout con el mensaje correcto.

**E-6 · 401 sin perder lo escrito**
- Alcance: ante un 401 durante un Guardar, mostrar un aviso y conservar el estado; o guardar el borrador en `sessionStorage` antes de redirigir (solo campos, sin fotos).
- Aceptación: con token vencido, después de iniciar sesión el formulario se recupera o el usuario recibe un aviso explícito.

### B. Integridad

**I-1 · Idempotencia de `commit-batch` en Cargar actuación**
- Alcance: una clave `(batch_id, row_id)` o un `idempotency_key` en el cliente, con la misma estrategia que el cierre de Completar trabajo. Requiere migración (tabla o columna de idempotencia).
- Aceptación: dos commits con la misma clave dan una sola actuación; pytest concurrente.

**I-2 · Corregir los dos tests desactualizados (F-13)**, decidiendo antes el comportamiento correcto de `isLocalCompletarTrabajoMediaQueueFinished`.

### C. Rendimiento y UX (no urgente)

- **R-1 · Reducción de imagen en el cliente** (por ejemplo, lado máximo de 2560 px, JPEG 0,85) antes del SHA. Se debe medir antes y después; el SHA pasa a ser el del archivo reducido.
- **R-2 · Miniaturas livianas** (`createImageBitmap` con `resizeWidth`, o `img decoding="async"` y `loading="lazy"`).
- **R-3 · Limitar los re-renders de progreso** (throttle a unos 4 por segundo; `setQueueStats` solo si cambió).
- **R-4 · Aviso `beforeunload`** con cola pendiente o subida en curso (Editar y Cargar más fotos).
- **R-5 · Cola persistente opcional** (IndexedDB) para fotos seleccionadas y no subidas. Evaluar después de R-1 y R-4; es el cambio más grande.

### Mensajes propuestos (no implementados)

| Estado | Mensaje | Acción |
|--------|---------|--------|
| Datos guardados, fotos subiendo | "Actuación guardada. Subiendo fotos (2 de 5)… No cierres esta pantalla." | — |
| Parcial | "Actuación guardada. 3 fotos guardadas, 2 pendientes." | "Continuar subida" · "Salir (las pendientes se descartan)" |
| Error de red | "Sin conexión. Lo ya guardado se mantiene." | "Reintentar" |
| Guardado OK, la galería no refrescó | "Fotos guardadas. No pudimos actualizar la vista." | "Actualizar galería" |
| Estado desconocido (timeout o recuperación tras blanco) | "No pudimos confirmar si se guardó. Revisá el trabajo antes de volver a cargarlo." | "Ver en Mis trabajos" |
| Sin permiso o sin ítem de ruta | "Este trabajo no admite fotos desde aquí (no pertenece a tu ruta)." | — (sin botón de guardar) |

---

## 8. Limitaciones y protocolo de QA en teléfono real

### Pruebas ejecutadas realmente

- **Frontend (vitest, local):** `src/features/media`, `CompletarTrabajos`, `CargarActuaciones`, `InspectorCargarFotosDialog*`, `actuacionDetalleSaveSequence`, `actuacionEditListRefresh` y `ActuacionesGestionMobileCardList`. Resultado: **64 archivos, 300 tests: 299 pasan y 1 falla** (F-13, previo).
- **Backend (pytest, local):** 11 suites de media (`test_media_storage_*`, `test_media_2b/2c2/2d/2d1_*`). Resultado: **61 tests: 60 pasan y 1 falla** (F-13, cupo desactualizado). Destino verificado: `tests/conftest.py` usa `TEST_DATABASE_URL` con `assert_connected_database_is_test` y `MEDIA_STORAGE_PROVIDER=mock`, así que la base y el almacenamiento son de prueba y aislados.
- **Lectura de código** de todos los archivos citados.

### No ejecutadas (y qué haría falta)

| Prueba | Motivo | Qué haría falta |
|--------|--------|-----------------|
| Mediciones en navegador (tiempos, requests, hilo principal, memoria) | El almacenamiento `mock` devuelve URLs `mock://put/…` que un navegador no puede usar, así que la subida real no se puede ejercitar en local | Un bucket S3 compatible local (MinIO) o un bucket de staging, una base de test y un usuario de prueba |
| Simulación móvil (DevTools: CPU 4×, Slow 3G) | Lo mismo, y no se levantó el stack en este ticket | Lo anterior y Chrome DevTools |
| Teléfono real | No hay dispositivo ni acceso | Los teléfonos donde ocurrió el blanco |
| Consulta de prevalencia de F-2 y F-3 | Prohibido operar sobre producción sin autorización | Una consulta de solo lectura autorizada (ver abajo) |
| Logs de producción (401, errores de `complete`) | Sin acceso | Acceso de solo lectura a los logs de Railway |

Consulta de solo lectura sugerida para F-2 (ejecutar solo con autorización y sin exportar datos personales; solo conteos):

```sql
SELECT COUNT(*) AS actuaciones_inspector_fuera_de_grupo
FROM actuaciones_inspector ai
JOIN ruta_item ri ON ri.actuacion_id = ai.actuaciones_id AND ri.deleted_at IS NULL
WHERE ai.deleted_at IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM ruta_grupo_inspector rgi
    WHERE rgi.ruta_grupo_id = ri.ruta_grupo_id AND rgi.inspector_id = ai.inspector_id
  );
```

### Protocolo breve en teléfono real

**Preparación:** usar un usuario de prueba y una actuación de prueba (nunca datos reales de inspección). Tener 1 foto chica (menos de 1 MB) y 8 fotos de cámara (3–8 MB) **de objetos genéricos**. Anotar el modelo, el sistema operativo, el navegador con su versión y la RAM.

**Captura de evidencia:**
- **Android:** conectar por USB y abrir `chrome://inspect` en la PC → Console + Network + Performance monitor (JS heap).
- **iOS:** conectar a una Mac → Safari → Desarrollo → el dispositivo → Web Inspector.
- Sin cable: grabar la pantalla del teléfono, anotar la hora exacta (para cruzar con los logs del backend) y no mostrar datos personales en la grabación.

**Pasos (repetir cada uno 3 veces):**
1. Cargar actuación sin fotos → Guardar. ¿Hubo blanco? ¿Qué muestra la consola?
2. Editar actuación sin fotos → Guardar.
3. Editar con 1 foto chica → Guardar.
4. Editar con 8 fotos grandes → Guardar. Mirar el heap y si la pestaña se recarga sola.
5. Repetir el paso 4 abriendo la cámara desde el selector (en lugar de la galería).
6. Repetir el paso 3 activando el modo avión a mitad de la subida y después desactivándolo.
7. Doble toque rápido en Guardar (pasos 1 y 2).
8. Dejar la sesión abierta más de 8 h (o un token corto en staging) y tocar Guardar.
9. Mis trabajos → Cargar más fotos en un trabajo antiguo y en uno donde el inspector no integró el grupo.

**Después de cada blanco:**
- Copiar el último error de la consola (sin datos personales) y la lista de requests (estado HTTP de PUT, commit, intents y complete).
- Verificar desde otro dispositivo qué quedó guardado (detalle de la actuación y galería).
- Registrar: paso, cantidad y tamaño de fotos, red, hora, si hubo recarga, el error y lo que persistió.

**Criterio de cierre del diagnóstico:** al menos una pantalla blanca reproducida con su traza de consola, o la evidencia del boundary de E-1 en producción.
