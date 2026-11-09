# V1.1-ACT-EDIT.0 — Relevamiento de bloqueos de edición

**Fecha:** 2026-11-09  
**Alcance:** diagnóstico. Sin cambios funcionales de frontend ni backend.  
**Canal analizado:** edición posterior en Gestión / Ver actuación (`PUT /actuaciones/:id`) frente a la carga original (Cargar actuación vs Completar trabajo).

Este documento responde, por cada campo investigado: **¿está bloqueado por diseño, por UI, por payload o por backend; y es seguro habilitarlo para corregir datos del contribuyente existente (punto 1)?**

No cubre desvinculación (punto 2) ni reasignación a otro contribuyente (punto 3).

---

## 1. Alcance y registros de prueba utilizados

### Qué se comparó

| Caso | Origen | Estado verificado |
|---|---|---|
| A | Cargar actuación con Inspección + Notificación | Edición posterior en Gestión |
| B | Cargar actuación con Inspección + Comprobación | Edición posterior en Gestión |
| C | Completar trabajo equivalente (visita de origen con las mismas actas) | Formulario de cierre y edición posterior |
| D | Actuación con contribuyente ya vinculado | Guardar sin cambios |
| E | Actuación histórica (`carga_solo_comprobacion`) | Lectura y edición sin inventar contribuyente |

### Qué no se tocó

- Ningún registro de producción.
- Ningún schema, servicio, migración, endpoint ni modelo.
- El hotfix de `limpiar_contribuyente`.
- Multimedia, permisos, impresión, historial, exportaciones ni catálogos.

### Evidencia usada (desarrollo / pruebas controladas)

El relevamiento es estático y de tests ya existentes. No se mutó la base de desarrollo.

| Fuente | Qué cubre |
|---|---|
| `Frontend/src/Containers/Actuaciones/utils/actuacionEditRules.ts` | Flags visuales `canEdit*` |
| `Frontend/src/Containers/Actuaciones/Components/ActuacionDetalleDialog.tsx` | `disabled` / readonly del modal Editar |
| `Frontend/src/Containers/Actuaciones/utils/submitActuacionRow.ts` | Armado del PUT, strip de identidad y domicilio |
| `Frontend/src/Containers/Actuaciones/utils/contribuyenteCrudOptions.ts` | Identidad touched + veto de `limpiar_contribuyente` |
| `Frontend/src/Containers/Actuaciones/utils/buildActuacionUpdatePayload.ts` | Allowlist del PUT |
| `Frontend/src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx` | Campos editables al cerrar trabajo |
| `Backend/app/domains/actuaciones/services/actuacion_domicilio_edit_service.py` | `can_edit_domicilio` / `can_edit_rubro` |
| `Backend/app/domains/actuaciones/services/update_service.py` | Persistencia de identidad y domicilio |
| `Backend/app/domains/actuaciones/services/expediente_actas_edit_guard.py` | Lock de acta notif/comp por expediente |
| `Backend/app/domains/actuaciones/attach/contribuyente.py` | Upsert por documento |
| `Backend/tests/test_actuacion_domicilio_edit_pr7_15.py` | A/B/C domicilio con y sin circuito posterior |
| `Backend/tests/test_acta_identidad_gestion_1.py` | D: PUT sin identidad conserva vínculo |
| `Backend/tests/test_act_hist_1_carga_solo_comprobacion.py` | E: histórica sin contribuyente formal |
| `Frontend/src/Containers/Actuaciones/utils/submitActuacionRow.identidad1.test.ts` | D: frontend nunca manda `limpiar_contribuyente` |

---

## 2. Matriz de campos por caso A–E

Leyenda de resultado:

| Resultado | Significado |
|---|---|
| Editable correctamente | Se puede modificar y persiste sin desvincular. |
| Bloqueado intencionalmente | Hay regla de negocio documentada. |
| Bloqueado por error visual | El backend podría aceptarlo, pero la UI no deja editarlo. |
| Descartado por frontend | Se edita visualmente (o queda en el draft) pero no viaja en el PUT. |
| Rechazado por backend | El PUT responde 4xx con causa identificada. |
| Riesgoso | El cambio puede alterar relaciones, actas o contribuyente. |

Cuando un caso depende de un estado posterior (expediente, iniciador en uso, sync de vencimiento) se indica en la celda.

### 2.1 Identidad del contribuyente

| Campo | A Cargar + Notif | B Cargar + Comp | C Completar equivalente | D Guardar sin cambios | E Histórica |
|---|---|---|---|---|---|
| `doc_nro` | UI editable en modo `normal`. PUT solo si el usuario tocó o cambió el campo. Backend upsert por documento. **Riesgoso** si se cambia el documento a otro existente (punto 3, fuera de alcance). | Igual que A, mientras no sea circuito Oficio. | En el cierre de visita de origen el campo está habilitado (`showContribuyenteDomicilioEditable` = true, salvo RN / Oficio). En edición posterior, igual que A si el iniciador de la visita es Relevamiento. | **Descartado por frontend** a propósito: no viaja. El vínculo se conserva. | GET muestra snapshot histórico, **sin** `doc_nro`. El payload histórico **prohíbe** `contribuyente` / `doc_nro`. No inventa contribuyente. |
| `contrib_apellido` | Editable en modo `normal`. Persistencia in-place sobre el mismo `Contribuyente` si el documento no cambia. | Igual que A. | Editable al completar visita de origen. | No viaja. Conserva valor. | Snapshot `titular_apellido_historico`. No crea `Contribuyente`. |
| `contrib_nombre` | Igual que apellido. | Igual que A. | Igual que C apellido. | No viaja. Conserva valor. | Snapshot `titular_nombre_historico`. |
| `razon_social` | Igual que apellido. | Igual que A. | Igual que C apellido. | No viaja. Conserva valor. | Snapshot `titular_razon_social_historica`. |

**Bloqueo duro de identidad (no es A/B normales):** circuito Oficio / ratificación / Verificar-reinspección. `getActuacionEditableFields` pone `canEditContribuyente = false` y el PUT residual **borra** identidad del body (`applyCircuitoResidualOperationalStrip`). Completar trabajo, en esos circuitos, también deja titular en solo lectura salvo `COMPLETE_HISTORICAL`.

### 2.2 Establecimiento y domicilio

| Campo | A | B | C | D | E |
|---|---|---|---|---|---|
| `nombre_local` | Editable en modo `normal`. Va en allowlist. Persiste en `actuaciones.nombre_local`. | Igual que A. | Editable al completar visita de origen. | Si no se toca, el PUT puede reenviarlo porque no tiene guardia “solo si cambió”; el valor es el mismo. | Prohibido en payload histórico. |
| Rubro | Sigue a `can_edit_rubro` (mismo criterio que domicilio, salvo Denuncia). Ver §3.2. | Igual, hasta que la comprobación tenga expediente/oficio o iniciador derivado en uso. | Al completar visita de origen: editable. En edición posterior: Relevamiento sí; Denuncia sí para rubro (FIX.6) y no para domicilio. | Si no cambia, el mapper lo puede reenviar; no desvincula contribuyente (test IDENTIDAD.1). | Prohibido. Domicilio histórico se crea **sin rubro**. |
| Calle / número / `numero_tipo` | Ver §3.2. Recién cargada, **sin** iniciador de reinspección en la visita: editable. Si el sync de notificación vencida deja `IniciadorRuta.actuacion_id` apuntando a esta actuación base, la UI y el backend **bloquean domicilio** con mensaje de reinspección, aunque el iniciador esté `PENDIENTE` sin ruta. Eso **no** está cubierto por el test PR7.15e (el fixture no setea `actuacion_id`). | Recién cargada sin expediente: editable (test PR7.15e). Con expediente de envío u oficio: **bloqueado intencionalmente** (`MSG_ACTAS_DOCUMENTALES`). | Completar visita de origen: editable. Edición posterior Relevamiento: editable mientras el acta no haya entrado a circuito posterior. | Si `can_edit_domicilio === true` y no hubo cambio de calle/número, el frontend **omite** calle/número del PUT (no es error). | Calle/número sí se editan como domicilio histórico, **sin** contribuyente ni rubro. |

### 2.3 Actas

| Campo | A | B | C | D | E |
|---|---|---|---|---|---|
| `acta_inspeccion_num` | Editable en modo `normal` (allowlist + `attach_inspeccion`). OT y fecha de la visita siguen bloqueadas en Gestión. | Igual. | Se carga en Completar (visita realizada). En edición posterior, mismo criterio que A. | Si no se toca, puede ir en el PUT si el draft lo trae; no afecta contribuyente. | Prohibido. |
| `acta_notificacion_num` + motivos | Editable **salvo** `notificacion_editable === false` (expediente de plazo asociado). Bloqueo **solo del bloque notificación**, no de toda la actuación (FIX.10A). | Si también hay notificación, misma regla independiente. | Completar visita de origen: el formulario de notificación está habilitado (`showNotificacionEditableEnCompletarTrabajo`). No crea expediente. | Sin cambios: si el acta sigue en el draft, el mapper la reenvía; el guard de expediente rechaza mutación si ya hay expediente. | Prohibido. |
| `acta_comprobacion_num` + motivo | Independiente de la notificación. | Editable **salvo** `comprobacion_editable === false` (expediente de envío u oficio). Cargar actuación **no** crea expediente. | Completar tampoco crea expediente. El lock aparece después, en el canal de expedientes. | Igual que notificación. | Es el único acta del modo histórico. Se persiste. GET no inventa contribuyente. |

OT y fecha de visita en Gestión están **siempre** `disabled` (bloqueo visual de diseño). Completar trabajo también los marca readonly (`orden_trabajo_y_fecha_readonly`). No son el problema de este ticket.

---

## 3. Evidencia del recorrido UI → payload → backend → persistencia

Recorrido común de edición posterior (Gestión):

```text
GET /actuaciones/:id/gestion  (present_actuacion_gestion_detalle)
→ draft del modal (mergeActuacionIdentidadFromApiRow)
→ disabled según getActuacionEditableFields + notificacion_editable / comprobacion_editable
→ submitActuacionRow
   → strip identidad residual
   → reinserta identidad solo si touched/changed
   → applyDomicilioCalleSubmitGuard
   → delete limpiar_contribuyente
   → buildActuacionUpdatePayload (allowlist)
→ PUT /actuaciones/:id
→ ActuacionGridRowIn (rechaza limpiar_contribuyente)
→ map_actuacion_row (IDENTIDAD.2: nunca emite contribuyente: null)
→ actualizar_actuacion → aplicar_payload_actuacion
→ GET posterior
```

### 3.1 Identidad — punto 1 (corrección del contribuyente existente)

| Etapa | Comportamiento |
|---|---|
| GET | `doc_nro`, `contrib_*`, `razon_social` salen de `domicilio.contribuyente`. Histórica: snapshot, `doc_nro` null. |
| Formulario | `disabled={!canEditContribuyente}`. En Inspección normal (A/B) `canEditContribuyente = true`. |
| PUT frontend | `buildGestionIdentidadPutFields`: solo si hubo toque o cambio semántico. Vaciar todos los campos **no** manda `limpiar_contribuyente`; manda `{}`. Un `limpiar_contribuyente: true` interno se borra siempre antes del fetch. |
| Allowlist | `doc_nro`, `contrib_apellido`, `contrib_nombre`, `razon_social` están en `ACTUACION_ADMIN_PUT_ALLOWED_KEYS`. `limpiar_contribuyente` **no**. |
| Schema | `ActuacionGridRowIn.limpiar_contribuyente` si llega `true` → 422 *«La desvinculación de contribuyente no está permitida desde la edición general»*. La ruta PUT corta igual de entrada. |
| Mapper | Emite `contribuyente` solo si hay identidad útil. **Nunca** `contribuyente: null` (IDENTIDAD.2). |
| Servicio | Si el fragmento no está identificado (sin documento), **no** desvincula ni reasigna (`_contribuyente_payload_identificado`). Si hay documento: `resolve_contribuyente` actualiza apellido/nombre/razón **in-place** en la misma fila. |
| Persistencia D | Tests `test_put_solo_observaciones_conserva_contribuyente`, `test_put_identidad_incompleta_sin_limpiar_no_desvincula`, `test_put_cambia_solo_apellido_conserva_resto`. |

Conclusión identidad A/B en modo normal: **no está bloqueada por UI**. El hueco real es de producto (domicilio/rubro, §3.2) y de riesgo si se cambia el documento (punto 3).

### 3.2 Domicilio y rubro — diferencia Cargar vs Completar

Backend (`puede_editar_domicilio_actuacion`):

1. Si el iniciador “operativo” es RN / Oficio / Verificar / Ratificación / Denuncia → bloquea (`MSG_REINSPECCION`).
2. Si el tipo de actuación es reinspección / ratificación / verificar → bloquea.
3. Si la notificación o comprobación **ya se usó** en circuito posterior (reinspección usada, expediente/oficio, iniciador derivado en ejecución o en ruta) → bloquea (`MSG_ACTAS_DOCUMENTALES`).
4. Si no hay iniciador → **permite**.
5. Si el iniciador es `RELEVAMIENTO` → **permite**.
6. Cualquier otro iniciador → bloquea (`MSG_SOLO_RELEVAMIENTO`).

Resolución del iniciador (`resolve_iniciador_operativo_actuacion`):

1. Primero `RutaItem.actuacion_id` (visita publicada). Es lo correcto: el presenter documenta que `IniciadorRuta.actuacion_id` en notificación/oficio vencidos apunta a la actuación **base**.
2. Si no hay ítem de ruta, **fallback** `IniciadorRuta.actuacion_id == actuación`.

Cargar actuación no crea `RutaItem`. El sync post-commit `sync_iniciadores_reinspeccion_notificacion` materializa un iniciador `REINSPECCION_NOTIFICACION` con `actuacion_id = actuación base` cuando la notificación está vencida.

Ese fallback hace que el caso A, una vez corrido el sync, se clasifique como reinspección y **bloquee calle/número/rubro**, incluso con iniciador `PENDIENTE` sin ruta.

El test `test_actuacion_con_notificacion_iniciador_pendiente_sin_ruta_permite` **no asigna** `actuacion_id` al iniciador, así que no reproduce el fallback de producción.

Completar trabajo equivalente (caso C, Relevamiento):

- Existe `RutaItem.actuacion_id` → iniciador `RELEVAMIENTO`.
- El fallback no se usa.
- `can_edit_domicilio = true` hasta que el acta entre a circuito posterior.
- En el modal de Completar, calle/titular/rubro están habilitados de entrada (`showContribuyenteDomicilioEditableEnCompletarTrabajo`).

Frontend, si `can_edit_domicilio !== true`:

- UI: `disabled={!canDom}` + motivo `domicilio_edit_blocked_reason`.
- PUT: `applyDomicilioCalleSubmitGuard` **borra** `calle`, `numero`, `numero_tipo`. No es un descarte accidental de un campo habilitado: coincide con el flag.

Clasificación A (domicilio, tras sync de notificación vencida): **bloqueado por backend + UI**, con regla aplicada al iniciador **derivado** en lugar de a la visita base. Para el usuario se parece a un error: Completar sí dejó editar esos datos, Cargar después no.

Clasificación B (domicilio, comprobación sin expediente): **editable correctamente**. Con expediente: **bloqueado intencionalmente**.

### 3.3 Actas de notificación / comprobación

| Etapa | Notificación | Comprobación |
|---|---|---|
| GET | `notificacion_editable = not notificacion_tiene_expediente_asociado` | `comprobacion_editable = not (expediente envío u oficio)` |
| UI | `lockedNotif` deshabilita número y motivos | `lockedComp` deshabilita número y motivo |
| PUT | Si el payload trae `notificacion` y hay expediente → `ValueError` 400/422 | Igual con expediente de envío |
| Alta Cargar / Completar | No crean expediente | No crean expediente |

Cargar y Completar quedan alineados al día siguiente de labrar el acta. El lock aparece cuando el trámite administrativo avanza, no por el origen de carga.

FIX.10A: expediente en un acta **no** bloquea el modal entero (`actuacion_bloqueada_por_expediente_desde_canal_actas()` retorna `False`).

### 3.4 `limpiar_contribuyente` (hotfix vigente — no reactivar)

| Capa | Garantía |
|---|---|
| UI Gestión | No hay control que setee el flag en edición general. Vaciar campos pide confirmación de desvinculación en código auxiliar, pero `applyContribuyenteClearFlag` **no infiere** el flag. |
| `submitActuacionRow` | `delete rowWithInspectores.limpiar_contribuyente` siempre. |
| Allowlist PUT | La clave no existe. |
| Tests frontend | `submitActuacionRow.identidad1.test.ts`, `buildActuacionUpdatePayload.test.ts`, `contribuyenteCrudOptions.test.ts`. |
| Ruta + schema | 422 si llega `true`. |

Puntos 2 y 3 permanecen fuera de alcance. No se propone reactivar el flag.

---

## 4. Diferencias encontradas entre Cargar actuación y Completar trabajo

| Tema | Completar trabajo (visita de origen) | Cargar actuación → Editar en Gestión |
|---|---|---|
| Titular, documento, rubro, calle | Formulario operativo habilitado (Relevamiento / Denuncia / primera visita). | Titular habilitado en modo `normal`. Calle/rubro dependen de `can_edit_domicilio`. |
| Iniciador asociado | Siempre hay `RutaItem` con el iniciador de la visita. | No hay `RutaItem`. Si más tarde existe un iniciador RN con `actuacion_id` en la base, el fallback lo trata como reinspección. |
| Expediente | No se crea al cerrar. | No se crea al cargar. |
| OT / fecha | Readonly de política de cierre. | Readonly de política de Gestión. |
| Identidad Oficio / RN | Solo lectura, salvo completar histórico. | `canEditContribuyente = false` + strip de PUT. Alineado. |
| Histórica | Completar histórico (`COMPLETE_HISTORICAL`) pide documento y rubro para **materializar** identidad. | `carga_solo_comprobacion` guarda snapshot y **prohíbe** `contribuyente` en el payload. No materializa. |

La asimetría que explica el ticket no es “Cargar no manda identidad”. Es:

1. **Domicilio/rubro de una actuación cargada a mano con notificación** pueden quedar bloqueados por el iniciador derivado de vencimiento, cosa que no ocurre en la visita de Relevamiento equivalente.
2. **Completar trabajo muestra esos campos habilitados en el cierre**; Gestión posterior, en el caso A contaminado por el fallback, los muestra deshabilitados.
3. Los números de acta de notificación/comprobación **no** están bloqueados por el origen Cargar vs Completar; se bloquean después, por expediente.

---

## 5. Riesgos detectados

| Riesgo | Detalle | ¿Habilitar en ACT-EDIT.1? |
|---|---|---|
| Fallback `IniciadorRuta.actuacion_id` | Bloquea domicilio de la actuación **base** (Cargar + notif vencida) como si fuera la visita de reinspección. | Corregir la resolución del iniciador. No “habilitar todo”. |
| Cambio de `doc_nro` a otro documento existente | `resolve_contribuyente` + `hay_cambio_real_contrib` **reasigna** `domicilio.contribuyente_id`. Punto 3. | No habilitar como corrección silenciosa. Fuera de alcance. |
| Corregir nombre/apellido/razón con el mismo documento | Actualiza la fila `Contribuyente` global. Otras actuaciones que compartan el titular ven el cambio. Es el punto 1, aceptable si se documenta. | Sí, con tests de `contribuyente_id` estable. |
| Domicilio compartido | Si hay conflicto de rubro/contrib, el update clona domicilio (`domicilio_operativo_shared`). No borra el vínculo; puede crear otra fila. | Mantener. No es desvinculación. |
| Acta con expediente | Mutar número/motivos desde Gestión está prohibido a propósito. El trámite vive en Notificaciones / Comprobaciones. | Seguir bloqueado. |
| Histórica | Mandar identidad formal 422/ValueError. Inventar `Contribuyente` rompería E. | Seguir sin materializar desde edición general. |
| Reactivar `limpiar_contribuyente` | Desvincularía domicilio. Hotfix vigente. | No. |

---

## 6. Recomendación concreta para `V1.1-ACT-EDIT.1`

Objetivo del próximo ticket: **corrección de datos del contribuyente existente y paridad de domicilio/rubro** entre Cargar y Completar, sin reabrir desvinculación ni reasignación.

### 6.1 Campos a habilitar (o a dejar de bloquear por error)

| Campo | Acción |
|---|---|
| `contrib_nombre`, `contrib_apellido`, `razon_social` | Ya editables en Inspección normal. En ACT-EDIT.1: confirmar que un cambio con **el mismo** `doc_nro` persiste y conserva `contribuyente_id`. No hace falta un flag nuevo. |
| `doc_nro` | Editable solo como corrección del documento **del mismo** titular. No tratar un documento distinto como “typo” automático (eso es reasignación). |
| `nombre_local` | Ya editable en modo `normal`. Incluir en la batería de regresión. |
| Calle, número, `numero_tipo`, rubro | Habilitar en actuaciones **base** de Cargar (sin `RutaItem`) aunque exista iniciador RN/Oficio **derivado** `PENDIENTE` cuya `actuacion_id` apunte a esa base. Seguir bloqueando cuando el acta ya esté en circuito posterior (expediente, oficio, iniciador en ejecución/ruta). |
| `acta_inspeccion_num` | Seguir editable en modo `normal`. |
| `acta_notificacion_num` / motivos | Seguir editable mientras `notificacion_editable !== false`. |
| `acta_comprobacion_num` / motivo | Seguir editable mientras `comprobacion_editable !== false`. |

### 6.2 Campos que deben continuar bloqueados

| Campo / acción | Motivo |
|---|---|
| `limpiar_contribuyente` y vaciar identidad como desvinculación | Hotfix. Punto 2. |
| Reasignar a otro `Contribuyente` cambiando el documento | Punto 3. |
| OT, fecha de visita, tipo de actuación en Gestión | Diseño. Completar también es readonly. |
| Identidad / domicilio / `nombre_local` en circuito Oficio, ratificación y RN **como visita de reinspección** (cuando hay `RutaItem` de ese iniciador) | Paridad con Completar. |
| Número y motivos de notificación con expediente | Canal Notificaciones. |
| Número y motivo de comprobación con expediente de envío u oficio | Canal Comprobaciones. |
| Domicilio cuando el acta ya alimentó un circuito posterior | PR7.15e, `MSG_ACTAS_DOCUMENTALES`. |
| Materializar `Contribuyente` desde histórica | Caso E. Snapshot solamente. |

### 6.3 Archivos afectados (solo el próximo ticket)

No modificarlos en ACT-EDIT.0.

**Backend (fix mínimo de iniciador operativo para domicilio/rubro):**

- `Backend/app/domains/actuaciones/services/actuacion_domicilio_edit_service.py` — `resolve_iniciador_operativo_actuacion`: no usar el fallback `IniciadorRuta.actuacion_id` cuando el tipo es RN/Oficio y no hay `RutaItem` de esa visita (esa FK es la actuación base).
- `Backend/tests/test_actuacion_domicilio_edit_pr7_15.py` — fixture con `actuacion_id` en iniciador RN `PENDIENTE` sin ruta; la actuación **base** debe seguir `puede_editar_domicilio = True`. Conservar los tests de bloqueo con expediente / `EN_EJECUCION` / ítem de ruta.
- `Backend/tests/test_acta_identidad_gestion_1.py` — no relajar; son la red del hotfix.

**Frontend (solo si el GET ya trae `can_edit_domicilio: true` y la UI aún deshabilita):**

- `Frontend/src/Containers/Actuaciones/utils/actuacionEditRules.ts` — no copiar el hard-block de Oficio a Inspección normal.
- `Frontend/src/Containers/Actuaciones/utils/submitActuacionRow.ts` — no enviar calle/número si `can_edit_domicilio !== true`; no cambiar esa guarda, solo alinearla al flag corregido.
- Tests: `actuacionEditRules.test.ts`, `submitActuacionRow.test.ts`, `submitActuacionRow.identidad1.test.ts`, `ActuacionDetalleDialog.domicilio.test.tsx`.

No tocar: schemas de desvinculación, `contribuyenteCrudOptions.ts` (salvo tests de punto 1), multimedia, permisos, exportaciones.

### 6.4 Pruebas de regresión necesarias

1. **A** — Cargar Inspección + Notificación, sin expediente: Editar permite titular y, si el iniciador RN está `PENDIENTE` sin ruta, también calle/rubro. PUT con mismo `doc_nro` y apellido corregido → 200, mismo `contribuyente_id`.
2. **A posterior** — Notificación con iniciador RN `EN_EJECUCION` o en ruta: domicilio sigue bloqueado (`MSG_ACTAS_DOCUMENTALES` o reinspección de la **visita** RN, no de la base).
3. **B** — Cargar Inspección + Comprobación sin expediente: domicilio y acta de comprobación editables. Con expediente de envío: acta y domicilio bloqueados; titular de Inspección normal sigue editable.
4. **C** — Completar Relevamiento con las mismas actas: cierre con titular/calle habilitados; edición posterior sigue permitiendo domicilio (regresión PR7.15 Relevamiento).
5. **D** — Guardar sin cambios: el PUT no incluye `limpiar_contribuyente` ni identidad; `contribuyente_id` no cambia. Mandar `limpiar_contribuyente: true` → 422.
6. **E** — Histórica: GET sin `doc_nro`; edición no crea `Contribuyente`; payload con `doc_nro` se rechaza.
7. **Oficio / RN visita** — identidad sigue bloqueada en UI y en PUT (FIX.7).
8. **Punto 1 vs 3** — mismo documento, cambia nombre → actualiza la misma fila. Documento distinto → no tratarlo como corrección automática en este ticket.

### 6.5 Qué no hacer en ACT-EDIT.1

- No “habilitar todo”.
- No reactivar `limpiar_contribuyente`.
- No anular validaciones de backend de expediente sobre actas.
- No usar Completar trabajo como canal para desbloquear Gestión.
- No materializar contribuyente desde históricas.

---

## Respuestas de cierre (por campo)

| Campo | ¿Por qué se bloquea hoy? | ¿Es seguro habilitarlo para el punto 1? |
|---|---|---|
| `doc_nro` | No está bloqueado en A/B normal. El riesgo es reasignación si el valor apunta a otro titular. | Corrección del **mismo** documento: sí. Cambio a otro documento: no (punto 3). |
| `contrib_nombre` / `contrib_apellido` / `razon_social` | No están bloqueados en A/B normal. Oficio/RN visita: bloqueo de diseño. | Sí, con el mismo `doc_nro`. |
| `nombre_local` | No está bloqueado en A/B normal. Oficio: sí, de diseño. | Sí en Inspección normal. |
| Calle / número / tipo | Backend `can_edit_domicilio`. En A, el fallback de iniciador derivado puede bloquear de más. En B, expediente/oficio bloquean con regla válida. | Sí en actuación base sin circuito posterior. No cuando el acta ya alimentó expediente/ruta/ejecución. |
| Rubro | Misma política que domicilio (Denuncia puede editar rubro aunque el domicilio no). | Igual que domicilio, más Denuncia FIX.6. |
| `acta_inspeccion_num` | No bloqueado en modo `normal`. | Sí. |
| `acta_notificacion_num` | UI + backend por expediente de plazo. | Sí sin expediente. No con expediente. |
| `acta_comprobacion_num` | UI + backend por expediente de envío u oficio. | Sí sin documentación administrativa. No con expediente/oficio. |

Con estas respuestas el ticket V1.1-ACT-EDIT.0 queda cerrado. El fix mínimo corresponde a **V1.1-ACT-EDIT.1**.
