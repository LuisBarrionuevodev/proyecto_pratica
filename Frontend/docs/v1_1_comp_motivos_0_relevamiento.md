# V1.1-COMP-MOTIVOS.0 — Motivos múltiples de comprobación y ciclo de oficios

**Fecha:** 2026-11-09  
**Alcance:** diagnóstico. Sin migraciones, sin backfill, sin cambios funcionales.  
**Base leída (solo SELECT):** `digitaliza_migracion` (Alembic `a2b3c4d5e6f8`). Esa base está casi vacía tras limpiezas de predeploy; **no representa el histórico de producción**. Las consultas de control quedan en el apéndice para reejecutarlas sobre un dump real antes de MOTIVOS.1.

Este documento entrega el contrato para:

1. Pasar `comprobacion.motivo` de **1:1 (texto)** a **1:N (catálogo)**.
2. Explicar por qué **algunos oficios siguen editables** después de una reinspección y otros no.

No se tocó código productivo, ni registros, ni permisos.

---

## 1. Inventario de consumidores de `comprobacion_motivo`

### 1.1 Modelo actual (persistencia)

| Pieza | Qué es hoy |
|---|---|
| Tabla/modelo | `comprobacion` / `Comprobacion` (`Backend/app/models/comprobacion.py`) |
| Columna | `motivo VARCHAR(255) NULL`, índice `ix_comprobacion_motivo` |
| Tipo | **Texto libre**. No hay FK a catálogo. |
| Unicidad del acta | `UNIQUE (numero_acta, anio)` = `uq_acomp_numero_anio` |
| Auditoría del acta | `created_at`, `updated_at`, `deleted_at` |
| Catálogo | Tabla aparte `catalog_motivo_comprobacion` (`nombre` único, 160). Sin `deleted_at`. Sin relación ORM hacia `comprobacion`. |
| Campo de Actuación | **No**. `actuaciones` solo tiene `comprobacion_id`. |
| Oficio / expediente | **No copian el motivo.** Oficio guarda `causa`. Expediente no tiene motivo. |

Origen del esquema: migración baseline `Backend/migrations/versions/05a3b9d35a32_sdsd.py`. No hay revisión posterior que convierta `motivo` a FK ni que cree tabla puente.

Catálogo canónico (`Backend/app/domains/catalogos/canonical/motivos.py`):

1. Falta de Higiene  
2. Condiciones Edilicias Inadecuadas  
3. No Permite la Inspección  
4. Incumplimiento  
5. Incumplimiento de Notificación  
6. Sin Certificado de Desinfección  
7. Sin Carnet de Sanidad  
8. Sin Certificado de Sanidad  
9. Mercadería Vencida  
10. Productos Sin Rotulación  

API de catálogo: `GET /grid/catalogs/motivos-comprobacion` (`list_motivos_comprobacion` en `Backend/app/domains/grid/routes/batch.py`). Frontend: `fetchMotivosComprobacion()`.

### 1.2 Escritura

Único escritor de la columna: `attach_comprobacion` (`Backend/app/domains/actuaciones/attach/comprobacion.py`).

- Payload interno: `{ acta_num, motivo }`.
- `motivo` obligatorio si hay número de acta (`ValueError: "Motivo de comprobación es obligatorio."`).
- **No consulta el catálogo.** Persiste el string ya coerceado (o no) por el schema del canal.
- Placeholder de previas: `previas_service` puede crear una comprobación con `motivo="PENDIENTE"`. Los KPI de “labrada” lo excluyen (`_comprobacion_labarda_filter`).

Mapeo UI → attach:

| Canal | Schema / mapper | ¿Coerce a catálogo? |
|---|---|---|
| Cargar / Editar (grilla PUT) | `ActuacionGridRowIn.comprobacion_motivo` → `map_actuacion_row` → `comprobacion.motivo` | **Sí** (`_coerce_catalog_value`) |
| Patch inspector | `ActuacionInspectorPatchIn` | **Sí** |
| Completar trabajo | `CompletarTrabajoCierreCompletoIn` → `map_completar_trabajo_cierre_completo` | **No** (solo strip). Exige motivo si hay acta. |
| Histórica solo comprobación | misma `ActuacionGridRowIn` + `carga_solo_comprobacion` | **Sí**, y el schema exige motivo |
| PATCH genérico | `ActuacionPatchIn` | Campo presente, **sin** validador de catálogo |

Orquestadores: `create_service`, `update_service`, `patch_service`, `historical_solo_comprobacion_service`, `completar_trabajo_actas_service`.

### 1.3 Lectura (presenters)

Todos leen `Comprobacion.motivo` y lo exponen como string único. No lo copian a otras entidades.

| Presenter / servicio | Clave de salida |
|---|---|
| `actuacion_to_grid_row` | `comprobacion_motivo` |
| `actuacion_to_pendiente_oficio_row` | `comprobacion_motivo` |
| `referencia_actuacion_from_grid_row` | `comprobacion_motivo` |
| `comprobacion_recorrido_detalle` / ficha documental | `acta_comprobacion.motivo` + `referencia_actuacion.comprobacion_motivo` |
| `completar_trabajo_presenters` | `comprobacion_motivo` |
| `pendientes_service` (seguimiento de notificación) | `comprobacion_motivo` de la visita |

### 1.4 Formularios con selector **único**

| Pantalla | Archivo | Control |
|---|---|---|
| Cargar actuación (modal) | `Frontend/src/Containers/CargarActuaciones/Components/CargarActuacionNuevaModal.tsx` | `AppSelect` “Motivo comprobación” |
| Cargar actuación (Glide) | `columnDefinitions.ts` + `dropdownOptions.ts` | dropdown de una celda |
| Completar trabajo | `Frontend/src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx` | `AppSelect`; auto-completa “No Permite la Inspección” si hay contra + acta |
| Editar actuación | `Frontend/src/Containers/Actuaciones/Components/ActuacionDetalleDialog.tsx` | `AppSelect` “Motivo de comprobación”; se bloquea con el acta si hay expediente/oficio |

Validación cliente compartida: `actuacionFormValidation.ts` (acta ⇒ motivo; pairing con contraproducencia «No permite inspección»).

### 1.5 Vistas consumidoras (solo lectura o export)

| Superficie | Archivo(s) | Uso |
|---|---|---|
| Ver actuación | `ActuacionDetalleDialog.tsx` (`LecturaDato`) | Un string |
| Gestión (listado) | `TableActuaciones.tsx` columna oculta “Motivo Comprob.”; `actuacionesCompositeColumns.tsx` | Un string |
| Pendientes | `TablaPendientes*.tsx`, `PendientesOficioView.tsx` | Un string |
| Historial documental de comprobaciones | `comprobacionOperativoBlocks.tsx`, `recorridoOficioExpLabels.ts`, `ActasComprobacionPage.tsx` | Display-only |
| Oficios / respuestas del Tribunal | `ComprobacionOficioOperativoDialog.tsx` copia `doc.acta_comprobacion.motivo` al snapshot; **no edita** el motivo del oficio | Display-only |
| Impresión / PDF | `ComprobacionesListadoPdfDocument.tsx` (`row.motivo`); `comprobacionesExportPdfResumen.ts`; `actuacionesExportVisualRows.ts` (omite `PENDIENTE`); dashboard PDF `top_motivos_comprobacion` | Un string / ranking |
| Excel | `comprobacionesExportNormalizedRows.ts`, `actuacionesExportNormalizedRows.ts`, `exportExcelDashboard.ts` | Un string |
| Seguimiento de notificación | `seguimientoNotificacionLabels.ts` | Un string de la visita |
| Filtros operativos | `buildOperativaComprobacionFiltroPayload.ts`, `ActuacionesListFilters` | **No filtran por motivo** (sí por número de acta) |
| Reportes SQL | `query_top_motivos_comprobacion` / `_comprobacion_labarda_filter` en `indicadores_resumen_service.py` | `GROUP BY comprobacion.motivo`; excluye vacío y `PENDIENTE` |
| Catálogo admin | `GestionSistemaPage.tsx` | Lista el catálogo, no las actas |

### 1.6 Acoplamiento especial: «No Permite la Inspección»

No es el mismo string que la contraproducencia:

| Catálogo | Valor persistido |
|---|---|
| `catalog_contraproducencia` | `NO PERMITE INSPECCION` |
| `catalog_motivo_comprobacion` | `No Permite la Inspección` |

Regla: con esa contraproducencia la comprobación es **opcional**; si se carga, número y motivo son obligatorios y el motivo **debe** ser ese valor. Completar trabajo lo auto-completa. En 1:N este valor tiene que seguir siendo reconocible (exclusivo o al menos presente) para no romper el bucket de cierre.

---

## 2. Contrato técnico propuesto para 1:N

### 2.1 Relación

```text
Comprobación 1 ── N Motivos de comprobación  (catálogo)
```

Oficios y expedientes **siguen independientes** de los motivos.

### 2.2 Tabla / modelo recomendado

Nombre: **`comprobacion_motivo`** (espejo de `notificacion_motivo`).

No reutilizar `motivo.id` (catálogo de **notificación**). La FK debe apuntar a `catalog_motivo_comprobacion.id`.

| Columna | Tipo | Notas |
|---|---|---|
| `comprobacion_id` | `INT NOT NULL` | FK `comprobacion.id` `ON DELETE CASCADE`. Parte de PK. |
| `catalog_motivo_comprobacion_id` | `INT NOT NULL` | FK `catalog_motivo_comprobacion.id` `ON DELETE RESTRICT`. Parte de PK. Nombre explícito para no chocar con `notificacion_motivo.motivo`. |
| `created_at` | `DATETIME NOT NULL` | `CURRENT_TIMESTAMP` |
| `updated_at` | `DATETIME NOT NULL` | `CURRENT_TIMESTAMP` + onupdate |
| `deleted_at` | `DATETIME NULL` | Soft delete, igual que `notificacion_motivo` |

**Restricción única / duplicados:** PK compuesta `(comprobacion_id, catalog_motivo_comprobacion_id)`. Impide repetir el mismo motivo en la misma comprobación. Reactivar un par soft-deleted = limpiar `deleted_at` (mismo patrón que `attach_comprobacion` al reusar el acta).

No tocar `uq_acomp_numero_anio`.

SQLAlchemy: `db.Table` asociativa, igual que `Backend/app/models/notificacion_motivo.py`, más `Comprobacion.motivos_catalogo` relationship. Mantener `Comprobacion.motivo` (texto) como **columna legado** hasta MOTIVOS.3.

### 2.3 Reglas de negocio propuestas

| Regla | Detalle |
|---|---|
| Alta nueva | Si hay `acta_comprobacion_num`, hace falta **al menos un** motivo de catálogo. |
| Máximo | No hay tope fijo. |
| Duplicados | El mismo `catalog_motivo_comprobacion_id` no puede repetirse en la misma comprobación. |
| Origen válido | Solo filas de `catalog_motivo_comprobacion`. Cerrar el hueco actual: Completar trabajo **también** debe coercear. |
| Históricos vacíos | `motivo` NULL / `''` → **cero filas** en la puente. No inferir. |
| Placeholder `PENDIENTE` | No migrar a la puente (no es catálogo). Dejar el texto legado. KPI sigue excluyéndolo. |
| Oficios | Ni leen ni escriben motivos. Un oficio nuevo no altera la puente. |
| «No Permite la Inspección» | Si la contraproducencia es ese bucket y hay acta, el conjunto de motivos debe **incluir** (y en la práctica ser solo) ese valor canónico. Definición exacta en MOTIVOS.1. |

### 2.4 Forma de devolver los datos

Contrato de API (GET grid, GET gestión, GET documental, Completar detalle):

```json
{
  "motivos_comprobacion": [
    { "id": 1, "nombre": "Falta de Higiene" },
    { "id": 6, "nombre": "Sin Certificado de Desinfección" }
  ],
  "comprobacion_motivo": "Falta de Higiene · Sin Certificado de Desinfección"
}
```

- `motivos_comprobacion`: arreglo ordenado por `nombre` (estable para UI e impresión).
- `comprobacion_motivo`: **texto derivado** para consumidores históricos (Excel, PDF, chips, Glide). Separador ` · `. `null` si no hay motivos activos.
- Escritura nueva (MOTIVOS.2): preferir `motivos_comprobacion: string[] | {id|nombre}[]`. Si llega solo el string legado, interpretarlo como un único motivo (compatibilidad).

PUT/POST de Completar y Cargar en MOTIVOS.1 pueden seguir aceptando `comprobacion_motivo` (un string) y, si llega `motivos_comprobacion`, usarlo con prioridad.

### 2.5 Estrategia de compatibilidad (sin borrar el legado todavía)

1. MOTIVOS.1 crea la tabla, sincroniza `comprobacion.motivo` como join de nombres al persistir, y rellena la puente **solo** donde el texto matchea catálogo (exacto o `_loose_key`).
2. Lectores siguen usando `comprobacion_motivo` derivado.
3. MOTIVOS.3 deja de escribir el legado; la columna permanece hasta un ticket de drop explícito (fuera de esta serie, salvo decisión en MOTIVOS.3).

---

## 3. Reporte de datos históricos y riesgos de migración

### 3.1 Resultado en `digitaliza_migracion` (2026-11-09, solo lectura)

| Caso | Resultado | Acción de migración |
|---|---|---|
| Total de comprobaciones | **3** (0 soft-deleted) | Conteo de control. **No usar como estimación de prod.** |
| Con motivo de catálogo (match exacto) | **3** (2× `Incumplimiento`, 1× `Falta de Higiene`) | Migrar a `comprobacion_motivo`. |
| Sin motivo | **0** | Preservar vacío. |
| `PENDIENTE` | **0** | No migrar a catálogo. |
| Motivo no encontrado en catálogo | **0** | Listar exacto; no inventar equivalencia. |
| Duplicados / anómalos (whitespace, casing) | **0** | Listar exacto. |
| Oficios activos | **0** | Parte B sin ejemplos live en esta base. |

Catálogo local: los 10 nombres canónicos, ids 1–10.

### 3.2 Riesgos (independientes del volumen)

1. **Completar trabajo no coercea catálogo.** En un dump real pueden aparecer alias (`NO PERMITE INSPECCION` vs `No Permite la Inspección`), espacios o el placeholder `PENDIENTE`.
2. **`PENDIENTE` de previas** no es un motivo de infracción. Meterlo en la puente ensuciaría ranking e impresión.
3. **Un string legado no expresa N motivos.** No hay datos 1:N que recuperar: cada fila histórica aporta **0 o 1** motivo.
4. **Match laxo vs exacto.** MOTIVOS.1 debe reportar por separado: exacto / `_loose_key` / desconocido. Los desconocidos **no se mapean**.
5. **KPI `GROUP BY comprobacion.motivo`.** Tras 1:N el top tiene que contar **filas de la puente** (una comprobación con 2 motivos suma en dos barras), no el string concatenado.
6. **Base local no es prod.** Reejecutar el SQL del apéndice sobre el dump de piloto/producción **antes** de escribir Alembic.

### 3.3 Consultas de control (solo SELECT)

Ver apéndice A. No se ejecutó `UPDATE`/`INSERT`/`DELETE`.

---

## 4. Matriz de estados y permisos de oficios

### 4.1 Pregunta de salida

> ¿Cuál es la regla actual de bloqueo y cuál debería ser la regla administrativa esperada?

**Regla actual (código):** un oficio es editable sii `evaluar_editable_oficio(oficio_id)` no junta motivos de bloqueo. Eso es **por oficio**, no por comprobación.

Bloquea si:

1. Oficio inexistente o `deleted_at` → `"Oficio no encontrado o eliminado."`
2. Su iniciador (`iniciador_reinspeccion_por_oficio`) está en `CUMPLIDO`, `ANULADO`, `CERRADO` o `CERRADO_NO_EXISTE_LOCAL` → `"Iniciador en estado {estado}."`
3. Tiene un `RutaItem` **abierto** (`PENDIENTE_ASIGNACION` / `ASIGNADO` / `EN_PROCESO`) en ruta `PUBLICADA` / `EN_CURSO` / `CERRADA` → `"Oficio incorporado en ruta {estado}."`
4. Ese ítem abierto ya tiene `estado_ejecucion` `REALIZADO` / `NO_REALIZADO` → `"Trabajo ya ejecutado en ruta."` (segundo motivo; la UI muestra el primero)

**No bloquea:**

- `resultado_cumplimiento_oficio` (`CUMPLE` / `NO_CUMPLE`) — el servicio **no lo lee**.
- Ítem `FINALIZADO` (visita ya cerrada). Comentario explícito en `iniciador_en_ruta_operativa`.
- Ruta `BORRADOR` (editable; `estado_operativo: ruta_borrador`).
- La existencia de otro oficio, expediente o iniciador en la **misma** comprobación.

Por eso, después de una reinspección:

| Cierre de la visita | Qué le pasa al iniciador | ¿El mismo oficio queda editable? |
|---|---|---|
| Cumple (flujo de cumplimiento) | Se queda `CUMPLIDO` | **No** — `"Iniciador en estado CUMPLIDO."` |
| No cumple (tipo aún `REINSPECCION_OFICIO` / ratificación) | Reencolado a `PENDIENTE` (`cerrado_motivo=OFICIO_NO_CUMPLE`), ítem `FINALIZADO` | **Sí** — es el hueco STAB-3 |
| Local cerrado / clima / otros (reencolado) | `PENDIENTE` + ítem `FINALIZADO` | **Sí** |
| Verificar e informar con visita hecha | En general se queda `CUMPLIDO` (el reencolado de cumplimiento **no** aplica a `VERIFICAR_INFORMAR_OFICIO`) | **No** |
| Visita en ruta publicada, ítem aún abierto | — | **No** — `"Oficio incorporado en ruta PUBLICADA."` |

**Regla administrativa esperada (hipótesis a implementar en V1.1-OFICIOS.1, no ahora):**

1. Un oficio **cerrado/cumplido no se edita ni se reabre**.
2. La comprobación **puede** admitir un oficio **nuevo** después.
3. El oficio nuevo **no modifica ni desbloquea** oficios ya cerrados.
4. El estado de la reinspección de un oficio **no debe bloquear por accidente** otro oficio independiente.

Hoy (1) falla para **No cumple / reencolado**: el mismo oficio documental vuelve a `editable=true`. (2) y (3) ya se cumplen (`acciones_permitidas` siempre incluye `agregar_otro_oficio`; la UI siempre muestra «Agregar otro oficio»; `test_dos_oficios_uno_resuelto_otro_pendiente`). (4) ya se cumple a nivel de PATCH por `oficio_id`; el flag legado `edicion.puede_editar_bloque_oficio` mira **solo el último oficio** y no debe usarse como lock compartido (la UI prefiere `item.editable`).

### 4.2 Capas de permiso (no confundir)

| Capa | Qué decide | Archivo |
|---|---|---|
| Backend por oficio | `evaluar_editable_oficio` | `oficio_editable_service.py` |
| Lista / card | `item.editable` + `item.bloqueado_motivo` | `oficio_list_service.oficio_comprobacion_item_payload` |
| Flag documental legado | `puede_editar_bloque_oficio` del **último** oficio | `evaluar_comprobacion_edicion_documental` |
| UI card | `oficioEditable={item.editable}` gana sobre el flag legado | `ComprobacionOficiosTribunalSection.tsx`, `ComprobacionOficioOperativoDialog.tsx` |
| Expediente de **envío** | Cualquier iniciador activo en esa `comprobacion_id` | `comprobacion_usada_como_iniciador` |
| OPER-RUTA (bandeja) | `en_pool` / `en_ruta_borrador` / `en_ruta_publicada` deshabilita **Gestionar oficio** | `operRutaPoolAcciones.ts` — distinto de `item.editable`. Un oficio en BORRADOR puede ser editable en API y estar bloqueado en la bandeja. |

Editar oficio y editar expediente de respuesta van en el **mismo PATCH**. Eliminar el bloque usa la misma policy. Alta de otro oficio es independiente.

### 4.3 Casos mínimos

La base `digitaliza_migracion` **no tiene oficios**. Los ejemplos operativos viven en tests (mismos estados que producción). Cada fila indica qué haría el código hoy.

| Caso | ¿Hay ejemplo? | Fuente | Oficio editable hoy | Editar respuesta | Agregar otro oficio |
|---|---|---|---|---|---|
| Oficio pendiente, sin reinspección | Sí | `test_oficio_sin_ruta_es_editable`, `test_oficio_sin_ruta_muestra_sin_programada_y_editable` | Sí (`pendiente` / `sin_iniciador`) | Sí | Sí |
| Oficio con reinspección realizada, sin resultado final | Sí (típico: Completar marca `CUMPLIDO` aunque no haya `CUMPLE`/`NO_CUMPLE`) | `test_oficio_visita_no_realizada` (fixture fuerza `CUMPLIDO`); recorrido “Reinspección realizada” | **No** si el iniciador quedó `CUMPLIDO` | No | Sí |
| Oficio con resultado Cumple | Sí | `test_oficio_promovido_verificar_informar_no_sin_programada` | No (`cumplido`) | No | Sí |
| Oficio con resultado No cumple | Sí | `test_no_cumple_reencola_iniciador_a_pendiente` | **Sí** (iniciador `PENDIENTE`, ítem `FINALIZADO`). No hay assert directo de `evaluar_editable_oficio`; el estado coincide con editable. | Sí | Sí |
| Oficio bloqueado luego de cierre | Sí | `test_delete_oficio_bloque_bloqueado_por_iniciador_cumplido`, ratificación resuelta | No | No | Sí |
| Oficio que sigue editable luego de reinspección | Sí | Reencolado No cumple / LOCAL CERRADO (`test_reinspeccion_oficio_reencolado`, STAB-3). **Este es el desvío respecto de la regla administrativa esperada.** | Sí | Sí | Sí |
| Acta con dos o más oficios en estados distintos | Sí | `test_dos_oficios_uno_resuelto_otro_pendiente` | Independiente: A no, B sí | Igual, por ítem | Sí |

Campos a anotar en QA de OFICIOS.1 (cuando haya dump): acta de comprobación, `numero_oficio`/`anio`/`causa`, expediente de respuesta, `estado_iniciador`, `tipo_iniciador`, `estado_ruta` / `estado_ruta_item`, `resultado_cumplimiento_oficio`.

### 4.4 Cómo se engancha el iniciador

`get_or_create_iniciador_from_oficio` (tras `complete_oficio_from_actuacion`):

| FK | Apunta a |
|---|---|
| `oficio_id` | **Este** oficio |
| `comprobacion_id` | El acta |
| `actuacion_id` | Actuación **ancla** (la de la comprobación), no la visita de reinspección |
| `domicilio_id` | Domicilio operativo de esa actuación |

Sin domicilio no hay iniciador (`PENDIENTE_DOMICILIO`) → oficio `sin_iniciador` y **editable**.  
La visita de reinspección es `RutaItem.actuacion_id`; ahí vive `resultado_cumplimiento_oficio`.

---

## 5. Archivos previstos para cada ticket posterior

No modificarlos en COMP-MOTIVOS.0.

### V1.1-COMP-MOTIVOS.1 — modelo, Alembic y compatibilidad backend

- `Backend/app/models/comprobacion.py`, `Backend/app/models/__init__.py`
- Nuevo: `Backend/app/models/comprobacion_motivo.py` (o Table en el mismo módulo)
- Alembic nuevo (no editar a mano `05a3b9d35a32_sdsd.py`)
- `Backend/app/domains/actuaciones/attach/comprobacion.py`
- `Backend/app/domains/actuaciones/mappers/grid/actuacion_row_mapper.py`
- `Backend/app/domains/actuaciones/mappers/completar_trabajo_cierre_mapper.py`
- Schemas: `actuacion_row_in.py`, `completar_trabajo_cierre_completo_in.py`, `actuacion_inspector_patch_in.py`
- Presenters: `actuacion_presenters.py`, `comprobacion_actas_presenters.py`, `comprobacion_documental_service.py`, `pendientes_service.py`, `completar_trabajo_presenters.py`
- `previas_service.py` (seguir con `PENDIENTE` **fuera** de la puente)
- Tests: `test_act_hist_1_carga_solo_comprobacion.py`, attach/update de comprobación, nuevo test de puente + unicidad

### V1.1-COMP-MOTIVOS.2 — formularios, detalle, historial e impresión

- `CargarActuacionNuevaModal.tsx`, `columnDefinitions.ts`, `dropdownOptions.ts`
- `CompletarTrabajoModal.tsx`, `buildCompletarTrabajoCierreBody.ts`
- `ActuacionDetalleDialog.tsx`, `actuacionFormValidation.ts`
- `comprobacionOperativoBlocks.tsx`, `recorridoOficioExpLabels.ts`, `seguimientoNotificacionLabels.ts`
- `ComprobacionesListadoPdfDocument.tsx`, `comprobacionesExportPdfResumen.ts`, `actuacionesExportVisualRows.ts`
- Tipos: `actuacionesListApi.ts`, `completarTrabajoApi.ts`, `actuacionesPendientesApi.ts`

### V1.1-COMP-MOTIVOS.3 — exportaciones, filtros y QA integral

- `comprobacionesExportNormalizedRows.ts`, `comprobacionesExportMappers.ts`, `actuacionesExportNormalizedRows.ts`
- `indicadores_resumen_service.py` (`query_top_motivos_comprobacion`, `_comprobacion_labarda_filter`)
- `exportExcelDashboard.ts`, `dashboardPdfMappers.ts`
- `TableActuaciones.tsx` / columnas compostas
- QA: Cargar, Completar, Editar, historial, PDF, Excel, ranking, histórica vacía, `PENDIENTE`, «No Permite la Inspección»
- Decidir (sin ejecutar aquí) si se deja de escribir `comprobacion.motivo`

### V1.1-OFICIOS.1 — regla explícita de bloqueo post-reinspección

- `oficio_editable_service.py` (`evaluar_editable_oficio`)
- `comprobacion_documental_service.py` (dejar de usar el último oficio como lock global)
- `actuacion_reencolado_service.py` / cierre Completar: reencolar **iniciador** no debe reabrir el bloque documental del oficio ya visitado
- UI: `ComprobacionOficiosTribunalSection.tsx`, `ComprobacionOficioOperativoDialog.tsx`, `comprobacionOficiosUtils.ts`
- Tests: `test_oficio_editable_pr4b.py`, `test_comprobacion_recorrido_oficio_resuelto_hotfix.py`, `test_completar_trabajo_stab4.py` (assert de editable tras `NO_CUMPLE`), `test_comprobacion_documental.py`
- Conservar: alta de otro oficio; independencia entre oficios; lock de expediente de envío por iniciador de la comprobación

---

## 6. Plan de implementación recomendado

```text
V1.1-COMP-MOTIVOS.1  → modelo, Alembic y compatibilidad backend
V1.1-COMP-MOTIVOS.2  → formularios, detalle, historial e impresión
V1.1-COMP-MOTIVOS.3  → exportaciones, filtros y QA integral
V1.1-OFICIOS.1       → regla explícita de bloqueo post-reinspección
```

Orden: **1 → 2 → 3**. OFICIOS.1 puede ir **en paralelo** a 2/3 (no comparte tabla de motivos). No mezclar ambos productos en un solo PR.

Antes de MOTIVOS.1: correr el SQL del apéndice sobre el dump real y pegar los conteos en el ticket de implementación.

### Qué no hacer todavía

- No crear la tabla ni Alembic.
- No backfill ni equivalencias inventadas.
- No borrar `comprobacion.motivo`.
- No cambiar `evaluar_editable_oficio` ni reencolado.
- No habilitar ni bloquear oficios en UI.
- No tocar actas, expedientes, rutas, contribuyentes ni media.

---

## Apéndice A — SQL de control (solo lectura)

```sql
-- Totales
SELECT
  COUNT(*) AS total,
  SUM(deleted_at IS NOT NULL) AS soft_deleted,
  SUM(deleted_at IS NULL) AS activas
FROM comprobacion;

-- Casos brutos
SELECT
  CASE
    WHEN deleted_at IS NOT NULL THEN 'soft_deleted'
    WHEN motivo IS NULL OR TRIM(motivo) = '' THEN 'sin_motivo'
    WHEN UPPER(TRIM(motivo)) = 'PENDIENTE' THEN 'placeholder_pendiente'
    ELSE 'con_texto'
  END AS caso,
  COUNT(*) AS n
FROM comprobacion
GROUP BY caso;

-- Match exacto a catálogo (candidatos a migrar)
SELECT COUNT(*) AS con_motivo_catalogo_exacto
FROM comprobacion c
INNER JOIN catalog_motivo_comprobacion cat
  ON cat.nombre = TRIM(c.motivo)
WHERE c.deleted_at IS NULL
  AND c.motivo IS NOT NULL
  AND TRIM(c.motivo) <> ''
  AND UPPER(TRIM(c.motivo)) <> 'PENDIENTE';

-- Sin motivo (preservar vacío)
SELECT COUNT(*) AS sin_motivo
FROM comprobacion
WHERE deleted_at IS NULL
  AND (motivo IS NULL OR TRIM(motivo) = '');

-- No encontrados en catálogo (listado exacto; no mapear)
SELECT c.id, c.numero_acta, c.anio, c.motivo
FROM comprobacion c
LEFT JOIN catalog_motivo_comprobacion cat
  ON cat.nombre = TRIM(c.motivo)
WHERE c.deleted_at IS NULL
  AND c.motivo IS NOT NULL
  AND TRIM(c.motivo) <> ''
  AND UPPER(TRIM(c.motivo)) <> 'PENDIENTE'
  AND cat.id IS NULL
ORDER BY c.motivo, c.id;

-- Anómalos: whitespace / PENDIENTE / duplicados de etiqueta
SELECT motivo, COUNT(*) AS n
FROM comprobacion
WHERE deleted_at IS NULL AND motivo IS NOT NULL
GROUP BY motivo
ORDER BY n DESC, motivo;

SELECT id, numero_acta, anio, CONCAT('[', motivo, ']') AS motivo_bracket
FROM comprobacion
WHERE deleted_at IS NULL
  AND motivo IS NOT NULL
  AND (motivo <> TRIM(motivo) OR motivo <> TRIM(BOTH ' ' FROM motivo));
```

---

## Criterio de cierre (COMP-MOTIVOS.0)

- Inventario de consumidores de `comprobacion_motivo`: §1.  
- Contrato 1:N (tabla, FKs, unique, timestamps, payload, texto derivado): §2.  
- Reporte de datos + riesgos + SQL: §3 y apéndice A.  
- Matriz de oficios y respuesta a la pregunta de bloqueo: §4.  
- Archivos y plan 1/2/3 + OFICIOS.1: §5–6.

Queda listo para implementar motivos múltiples **sin perder vacíos ni inventar equivalencias**, y queda explícito **por qué** un oficio queda editable o bloqueado después de la reinspección.
