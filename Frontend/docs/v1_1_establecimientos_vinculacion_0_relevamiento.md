# V1.1-ESTABLECIMIENTOS-VINCULACION.0 — Vincular ficha a contribuyente existente

**Fecha:** 2026-11-15  
**Alcance:** diagnóstico y propuesta (sin cambios de código productivo, migraciones ni datos).  
**HEAD analizado:** `0fe3484` (`main`).  
**Antecedente:** `Frontend/docs/v1_1_establecimientos_edicion_0_relevamiento.md` (caso 10: “cambio real de titular” quedó **fuera** de la corrección). Este ticket cubre ese hueco: CUIT mal cargado en una ficha cuyo documento correcto **ya pertenece a otro contribuyente**.

---

## Resumen ejecutivo

1. Las **cargas nuevas** (Cargar actuación y Completar trabajo) resuelven el titular con `resolve_contribuyente`: si el documento **literal** ya existe, **usan esa fila** y pueden actualizar nombre/apellido/razón. La ficha operativa se resuelve después por **identidad lógica** (contribuyente + calle + número, sin rubro). Mismo CUIT + mismo domicilio → misma ficha; mismo CUIT + domicilio distinto → otra ficha. Eso coincide con el QA de Luis.
2. La **corrección desde la ficha** es otro canal: actualiza **in-place** el mismo `contribuyente_id`. Si el documento propuesto (normalizado) ya es de **otro** id, preview pone `puede_aplicar: false` con `DOCUMENTO_AJENO` y apply responde **409**. No reasigna `domicilio.contribuyente_id`. Ese es el caso a resolver, y el bloqueo **debe permanecer** hasta un flujo de vinculación dedicado.
3. Vincular no es “corregir el CUIT de la persona equivocada”. Es **cambiar el titular del establecimiento**: los `domicilio` de **esta** ficha lógica apuntan al contribuyente correcto, sin pisar sus datos personales ni sus otros locales, y sin fusionar ni borrar filas.
4. El historial por DNI/CUIT lee actuaciones e iniciadores por `domicilio.contribuyente_id` (documento **normalizado**). En cuanto el domicilio se reasigne, las visitas de esa ficha aparecen bajo el CUIT correcto y dejan de aparecer bajo el anterior. Gestión / Ver actuación leen el titular **en vivo**. PDF emitidos y `titular_*_historico` **no** se reescriben.
5. Si el contribuyente destino ya tiene la misma identidad lógica (mismo CUIT + mismo domicilio), las dos fichas físicas **se agrupan** en el listado (`MIN(eo.id)`) y el historial de ficha une por `domicilio_id` de esa business key. No hace falta borrar ni fusionar EO. La UI debe decirlo en la preview y, si hay ambigüedad, **bloquear**.

---

## 1. QA de Luis vs código (ambos canales)

| Caso observado | Cargar actuación / Completar trabajo | Corrección desde la ficha |
|---|---|---|
| Mismo CUIT y mismo domicilio → la actuación entra a la ficha existente | **Sí.** `resolve_establecimiento_por_domicilio` devuelve el EO canónico (`MIN(id)`) si la identidad lógica es completa. Tests: `test_resolve_mismo_eo_para_cow_forks` (`test_gestion_fix_7.py`); cierre Completar: `*_vincula_eo_canonico`. | No aplica (no crea visitas). |
| Mismo CUIT y domicilio distinto → otra ficha | **Sí.** Business key distinta → otro EO. Test: `test_misma_persona_distinto_domicilio_dos_fichas`. | Corregir domicilio de una ficha **no** toca las otras (`test_5_domicilio_no_toca_otro_establecimiento`). Si la dirección nueva iguala otra ficha del **mismo** titular → `FUSION_FICHA` (409). |
| Se corrige el nombre del contribuyente existente → se refleja en asociados | **Sí, con matices.** `resolve_contribuyente` actualiza in-place apellido/nombre/razón **si la clave viene en el payload**. Lookup por documento **literal** (`strip`), no normalizado. Completar puede omitir titular y reutilizar el del domicilio. | **Sí.** UPDATE in-place del mismo `contribuyente_id`. Todas las fichas de esa persona ven el nombre nuevo (lectura en vivo). Test: `test_1_contribuyente_varios_establecimientos`. |
| Se corrige desde una ficha un CUIT por otro que ya existe → preview de conflicto, no guarda | **No es este canal.** Si Cargar/Completar envían el CUIT existente, `resolve_contribuyente` **devuelve la otra fila** y el domicilio puede **reasignarse** (posible fork COW). Es el riesgo que EDICION.0 evitó en la ficha. | **Sí, bloqueado a propósito.** `validar_documento_propuesto` + `contribuyente_ids_por_documento`. Preview: `conflicto.codigo = DOCUMENTO_AJENO`. Apply: 409. Test: `test_2_documento_ajeno_409_sin_fusion`. UI: Confirmar deshabilitado. |

**Conclusión:** no se puede reutilizar `resolve_contribuyente` como motor de vinculación desde la ficha: haría upsert/reasignación silenciosa y podría reescribir nombre/apellido/razón del contribuyente destino.

---

## 2. Mapa de vínculos (lo que realmente cuelga de la ficha)

```text
contribuyente 1 ──< domicilio >── 0..1 establecimiento_operativo   (domicilio_id UNIQUE en EO)
                      │
                      ├── actuaciones.domicilio_id          (titular LIVE)
                      ├── actuaciones.establecimiento_operativo_id  (nullable; historial de ficha NO filtra solo por esto)
                      ├── denuncia.domicilio_id
                      ├── relevamiento.domicilio_id
                      └── iniciador_ruta.domicilio_id       (obligatorio; sin contribuyente_id ni EO)

iniciador_ruta ── tipo + origen opcional:
  relevamiento | denuncia | notificacion + actuacion
  | comprobacion | oficio + comprobacion + actuacion

ruta_item ── iniciador_ruta_id
          ── actuacion_id / orden_trabajo_id (opcionales)
          ── estado_ruta_item / estado_ejecucion

actuaciones ── notificacion_id / comprobacion_id / inspeccion / clausura / decomiso
            ── orden_trabajo_id
            ── snapshots: titular_*_historico, nombre_local
comprobacion ── oficio ── expediente
notificacion ── expediente
```

**Identidad lógica** (`establecimiento_identidad_logica.py`):

| Pieza | Clave |
|-------|--------|
| Contribuyente | `doc:{normalizar_documento}` o, sin documento, `cid:{contribuyente_id}` |
| Calle | `slug_key(calle_key \|\| calle_normalizada \|\| calle)` |
| Número | `NUMERO` → slug; `ESQUINA` → `ESQ:{slug}` |

Varios `domicilio` / varios EO pueden ser **la misma ficha lógica** (forks COW). El listado muestra el canónico (`MIN(id)`). Alcance de corrección y historial de ficha usan `domicilio_ids_misma_identidad_logica`.

**Alcance ya calculado hoy** (`cargar_ficha_para_correccion` / `_llenar_conteos`):

- `domicilio_ids_ficha` — ancla + forks de la misma business key
- `lookalike_ids` — mismo texto de calle/número, **fuera** de la identidad (ambigüedad)
- actuaciones / notificaciones / comprobaciones / oficios de esos domicilios
- iniciadores con `domicilio_id IN domicilio_ids_ficha` y `ruta_item` + estados
- además, todos los EO y actuaciones del **contribuyente actual** (para advertir impacto de una corrección de nombre; en vinculación ese conjunto **no** debe mutar entero)

---

## 3. Flujo existente de carga y resolución

### 3.1 Contribuyente

| | Cargar actuación | Completar trabajo |
|---|------------------|-------------------|
| Entrada | `crear_actuacion_desde_payload` | `cerrar_completar_trabajo_por_ruta_item` → `_resolve_contribuyente_para_domicilio_cierre` |
| Helper | `resolve_contribuyente(payload["contribuyente"])` | El mismo helper **si** hay `doc_nro` o datos de titular; si no, reutiliza `act.domicilio.contribuyente` o puede omitir según el iniciador |
| Lookup | `Contribuyente.documento == str(doc).strip()` y `deleted_at IS NULL` | Igual |
| ¿Normaliza `. - espacio`? | **No** | **No** |
| Si existe | UPDATE apellido/nombre/razón **solo si la clave está en `data`** (vacío borra el campo) | Igual, cuando arma el dict |
| Si no existe | INSERT + flush | Igual |
| PUT Gestión | `aplicar_payload_actuacion`: solo llama al helper si hay identidad identificada; no desvincula si el payload viene incompleto | Cierre no envía `limpiar_contribuyente` |

`normalizar_documento` se usa en **identidad de ficha** e **historial**, no en el upsert de carga.

### 3.2 Domicilio

| | Cargar actuación | Completar trabajo |
|---|---|---|
| Helper | `get_or_create_domicilio` — match exacto `(calle, numero)` | `resolver_domicilio_real_desde_completar_trabajo` → `aplicar_edicion_domicilio_operativo` (`COMPLETAR_TRABAJO`) |
| Conflicto de titular/rubro en fila compartida | Fork PR12 (`debe_fork_domicilio_operativo`) **sin** `exclude_actuacion_id` | Fork con política de compartido / `exclude_actuacion_id` |
| Tras escribir | `normalizar_domicilio_en_sesion` (calle_key, etc.) | Igual |

La fila física de domicilio **no** es la business key de la ficha. Dos filas con la misma calle normalizada + mismo contribuyente se agrupan; dos literales distintos que normalizan igual también.

### 3.3 Ficha canónica

Ambos canales, al final, pueden llamar a `resolve_establecimiento_por_domicilio`:

1. Si identidad lógica completa → `eo_canonico_id_para_domicilio` (`MIN` de los EO de esa key).
2. Si no, 1:1 por `domicilio_id`.
3. Si no hay EO, lo crea.

**Cargar actuación** envuelve eso en `try_vincular_establecimiento_operativo_desde_actuacion`: **no vincula** si falta tipo de actuación (registro mínimo solo contraproducencia). **Completar trabajo** llama directo si la identidad está completa, **sin** ese gate de tipo.

### 3.4 Qué se puede reutilizar con seguridad en vinculación

| Reutilizar | Para qué |
|------------|----------|
| `contribuyente_ids_por_documento` + `normalizar_documento` | Buscar el destino y detectar duplicados normalizados |
| `cargar_ficha_para_correccion` / `domicilio_ids_misma_identidad_logica` | Alcance de **esta** ficha (forks incluidos) |
| Lookalikes + `AMBIGUEDAD_DOMICILIO` | No adivinar por texto |
| Conteos de `_llenar_conteos` (actuaciones, actas, iniciadores, rutas) | Preview |
| `eo_canonico_id_para_domicilio` | Detectar situación B (ya hay ficha lógica destino) **sin** borrar filas |
| Auditoría `CorreccionEstablecimientoAudit` (nuevo tipo) | Quién, cuándo, alcance |
| Roles `admin` / `usuario` | Mismos que corrección |
| Transacción única del apply actual | Nada parcial |
| Bloqueo de `limpiar_contribuyente` | Intocable |

| No reutilizar como motor | Por qué |
|--------------------------|--------|
| `resolve_contribuyente` | Upsert + puede **reescribir** datos del destino y devolver otra fila |
| Apply actual de corrección de contribuyente | Mutaría el documento **del contribuyente equivocado** |
| `_aplicar_rubro_contrib_seguro` / PUT actuación | Mezcla corrección, COW y posible `limpiar_contribuyente` |
| Fusión física de EO / contribuyentes | Fuera de alcance; el listado ya colapsa por identidad |
| `on_domicilio_changed` / geocode | No recalcular coordenadas |

---

## 4. Corrección de una ficha ya existente (hoy)

### 4.1 Qué muta la corrección

| Bloque | Mutación | Qué no toca |
|--------|----------|-------------|
| Contribuyente | Misma fila: `documento`, `apellido`, `nombre`, `razon_social` | `domicilio.contribuyente_id`, otros contribuyentes |
| Domicilio | In-place en `domicilio_ids_ficha`: calle/número/tipo | `contribuyente_id`, `rubro_id`, distrito, geocode, estados |
| Local (1B) | `domicilio.rubro_id` ancla + `eo.nombre_local` | `actuaciones.nombre_local`, otros EO |

Schema **prohíbe** `contribuyente_id` y `limpiar_contribuyente`.

### 4.2 El caso a resolver

```
Ficha F  → domicilio D  → contribuyente A  (CUIT incorrecto, p. ej. 20111111119)
Contribuyente B ya existe (CUIT correcto 20222222229), con o sin otros locales
Usuario quiere que F quede bajo B
```

Hoy: propuesto `documento = CUIT de B` → ids normalizados incluyen a B ≠ A → `DOCUMENTO_AJENO`:

> El documento propuesto ya pertenece a otro contribuyente. No se fusionan registros ni se reasigna el titular.

Apply no escribe (`test_2_documento_ajeno_409_sin_fusion`: `a.documento` igual, `d.contribuyente_id` sigue siendo A).

### 4.3 Qué integra la ficha **antes** de vincular

- Domicilio ancla del EO (`eo.domicilio_id`, UNIQUE).
- Forks COW con la **misma** business key de A + esa dirección (`domicilio_ids_ficha`).
- No incluye otros locales de A (otra calle/número).
- No incluye lookalikes (mismo texto, distinta `calle_key`) — si existen, el alcance ya se marca inseguro.

### 4.4 Qué referencias deben cambiar vs permanecer

**Deben cambiar (propuesta):**

- `domicilio.contribuyente_id` de **todos** los `domicilio_ids_ficha` → `B.id`.
- Lecturas en vivo que JOIN ese domicilio (ficha, bandejas, historial por CUIT, Completar trabajo, iniciadores de ese domicilio).

**Deben permanecer:**

- Ids de actuaciones, actas, oficios, expedientes, OT, iniciadores, `ruta_item`.
- `estado_iniciador`, `estado_ruta`, `estado_ejecucion`.
- FKs `notificacion_id` / `comprobacion_id` / `oficio_id` / `actuacion_id` en iniciadores.
- `actuaciones.domicilio_id` (sigue siendo el mismo local físico).
- `actuaciones.establecimiento_operativo_id` en V1 (el historial de ficha une por domicilio lógico; no hace falta reescribir masivamente). Decisión pendiente: ¿actualizar a EO canónico después?
- `eo.domicilio_id` (el ancla 1:1 no se mueve de fila).
- Coordenadas, distrito, rubro (salvo que producto pida otra cosa).
- `titular_*_historico`, `actuaciones.nombre_local`, PDF ya emitidos.
- Otros domicilios/EO de A y **todos** los de B salvo el agrupamiento lógico en el caso B.
- Fila A: no se le pisa el CUIT ni se borra.

### 4.5 Contribuyente anterior (A)

| Situación de A | Efecto de vincular solo esta ficha |
|----------------|-------------------------------------|
| Tiene otros locales | Esos EO y sus visitas **siguen en A** (CUIT mal cargado intacto). |
| Solo tenía esta ficha | A queda sin establecimientos en el listado. No borrar A. |
| Mismo domicilio compartido con relevamiento/denuncia | Esos iniciadores cuelgan del `domicilio_id`: **se mueven con la ficha** (lectura en vivo). Si eso no es deseable, hay que forkear antes (decisión). |

### 4.6 Contribuyente destino (B)

No actualizar `apellido` / `nombre` / `razon_social` / `documento` de B.  
No tocar sus otros `domicilio` / EO.  
No crear un contribuyente nuevo.

---

## 5. Las dos situaciones de destino

Tras reasignar `domicilio.contribuyente_id` de la ficha, la business key pasa de `doc:{CUIT_A}|calle|nro` a `doc:{CUIT_B}|calle|nro`.

### A — B tiene otros domicilios, pero no esta ficha lógica

- La ficha F **sigue siendo independiente** (otra business key que los demás locales de B).
- Historial de F: mismas actuaciones (mismos `domicilio_id`).
- Historial por CUIT de B: **gana** esas actuaciones e iniciadores (join por `contribuyente_id`).
- Historial por CUIT de A: **pierde** esas filas; conserva las de otros locales de A.
- No hay colisión de EO canónico. `resolve_establecimiento_por_domicilio` en visitas nuevas seguirá a F.

### B — Ya existe ficha lógica de B en ese domicilio

Hoy el listado **ya agrupa** EO con la misma key y muestra `MIN(id)`. El historial de ficha **ya une** actuaciones cuyo `domicilio_id` está en `domicilio_ids_misma_identidad_logica` (no exige `establecimiento_operativo_id = :id`).

Después de vincular, F y la ficha previa de B **comparten key**:

- Listado: una sola fila canónica.
- Historial canónico: unión de visitas de ambos domicilios físicos, **sin duplicar** filas de `actuaciones` (el filtro es `domicilio_id IN (...)`).
- Ambas filas `establecimiento_operativo` **siguen existiendo**. GET por id no canónico sigue respondiendo.
- **No** borrar, fusionar físicamente ni reescribir actas.

**Preview obligatoria:** “Este CUIT ya tiene establecimiento en la misma dirección lógica (ficha canónica #X). Al confirmar, el listado las agrupará. No se eliminan registros.”

**Ambigüedad → bloqueo (no elegir):**

- Más de un contribuyente con el documento normalizado equivalente.
- Lookalikes de dirección en A o en B (`AMBIGUEDAD_DOMICILIO`).
- Ficha origen sin `contribuyente_id` (`MSG_SIN_CONTRIB`).
- Documento vacío o > 11 caracteres (mismas reglas actuales).
- No se puede decidir si el domicilio está compartido con un local **distinto** de A que no entra en `domicilio_ids_ficha`.

---

## 6. Ambas vistas — antes / después esperado

Lectura **en vivo** = JOIN `domicilio` → `contribuyente`.  
**Snapshot** = columnas históricas o archivo ya generado.

| Superficie | ¿Live? | Caso A después | Caso B después |
|------------|--------|----------------|----------------|
| Ficha Ver establecimiento | Live titular, domicilio, rubro; `nombre_local` del EO (fallback última actuación) | Titular = B; mismo local; mismas visitas | Igual; el listado puede mostrar el canónico. Historial une ambas series |
| Historial por DNI/CUIT correcto (B) | Live por `contribuyente_id` + iniciadores por cadena | Aparecen visitas e ítems pendientes de F | Aparecen las de F **y** las que B ya tenía en esa dirección, sin duplicar id de actuación |
| Historial por documento anterior (A) | Live | Ya no lista F; sí otros locales de A | Igual |
| Gestión / Ver actuación | Titular live (`resolve_titular_grid_fields`), salvo `carga_solo_comprobacion` | Muestra datos de B | Igual |
| Notificaciones / comprobaciones / oficios / seguimientos | Sin FK de titular; leen actuación → domicilio | Texto/titular live; **mismos** ids y estados | Igual |
| Iniciadores e ítems (pendiente / publicado / completado) | `domicilio_id` + estados propios | Siguen el domicilio; no se republica ni se cambia `estado_*` | Igual |
| PDF / Excel ya emitidos | Snapshot de generación | Intactos | Intactos |
| `titular_*_historico` | Snapshot | Intactos | Intactos |
| `actuaciones.nombre_local` | Snapshot | Intacto | Intacto |
| Pin / distrito | No recalcular | Igual que ahora | Igual |

---

## 7. Propuesta de interacción (sin implementar)

Canal **nuevo**, separado de “Corregir contribuyente”. El bloqueo `DOCUMENTO_AJENO` de la corrección **se mantiene**.

1. En la ficha, el usuario elige **Vincular a contribuyente existente** (roles `admin` / `usuario`).
2. Ingresa el documento correcto (se normaliza para buscar; se muestra también el literal).
3. Lookup `contribuyente_ids_por_documento`:
   - **0** → no es vinculación: mensaje para usar “Corregir contribuyente” (typo del mismo titular) o alta nueva. No crear B desde este flujo.
   - **>1** → bloqueo: “Hay más de un contribuyente con ese documento. Revisión manual.”
   - **1** y es A → no hay nada que vincular (es corrección de formato / el mismo id).
   - **1** y es B → mostrar **solo lectura**: nombre y apellido o razón social, CUIT/DNI, cantidad de otros establecimientos. **No** editar datos de B.
4. El usuario confirma explícitamente “Vincular **este** establecimiento a [B]”.
5. Preview (reutilizar conteos de alcance):
   - Ficha origen (EO id, domicilio texto, CUIT actual A).
   - Destino B (id, datos, otros locales que **no** se tocan).
   - Actuaciones, notificaciones, comprobaciones, oficios, iniciadores, ítems de ruta (con estado), **sin** cambiarlos.
   - Otros locales de A: “permanecen en A”.
   - Snapshots/PDF: no se actualizan.
   - Si hay ficha lógica de B en esa dirección: **situación B**, ficha canónica #X, “el listado agrupará; no se borran filas”.
   - Si hay lookalike / duplicado de documento / alcance inseguro: `puede_aplicar: false`, sin Confirmar.
6. Confirmar → transacción:
   - `UPDATE domicilio.contribuyente_id = B.id` en `domicilio_ids_ficha`.
   - No tocar fila B ni otros domicilios de B/A.
   - Auditoría tipo `VINCULACION` (valores anteriores/nuevos + alcance JSON).
   - Un commit; si falla, rollback total (mismo criterio que `test_12_fallo_durante_guardado_rollback`).
7. UI post-éxito: recargar ficha; si situación B, **navegar al canónico** y avisar que el id anterior sigue existiendo pero el listado muestra uno.

Botones primarios azules solo dentro del modal (Ver alcance / Confirmar), alineado a la ficha UX.1.

---

## 8. Propuesta de implementación (etapas)

**Etapa 0 (este ticket):** este documento.

**Etapa 1 — Preview de vinculación (solo lectura)**  
`POST /establecimientos-operativos/:id/vinculaciones/preview`  
Input: documento. Output: destino, alcance, `situacion: "A" | "B" | "BLOQUEO"`, canónico si B. Cero writes. Tests de detección A/B/duplicado normalizado/lookalike.

**Etapa 2 — Apply atómico + auditoría**  
`POST /establecimientos-operativos/:id/vinculaciones` con `confirmado: true`.  
Servicios nuevos bajo `app/domains/establecimientos/services/` (no meter lógica en routes).  
No llamar `resolve_contribuyente`. Schema `extra=forbid`, sin `limpiar_contribuyente`, sin `contribuyente_id` enviado por el cliente (el destino sale del documento + lookup servidor). JWT para `created_by_user_id`.

**Etapa 3 — UI**  
Acción discreta en la ficha (mismo permiso). Si el usuario intenta “Corregir contribuyente” y el preview sigue siendo `DOCUMENTO_AJENO`, el mensaje actual permanece y puede **ofrecer** ir a Vincular (sin autoaplicar).

**Etapa 4 — Regresión de lecturas**  
Ficha, historial por CUIT (A y B), Gestión, notificaciones, comprobaciones, oficios, iniciadores pendientes/publicados/completados, Completar trabajo. Cargas nuevas **sin** cambiar comportamiento.

Cada etapa: commit propio. Sin quitar el 409 de corrección hasta que la etapa 2 esté cubierta por pruebas.

---

## 9. Pruebas que debe incluir el ticket de implementación

| # | Caso | Esperado |
|---|------|----------|
| 1 | Mismo contribuyente destino y mismo domicilio lógico (B) | Preview situación B. Tras apply: historial canónico muestra ambas series; ninguna actuación duplicada por id; EO físicos intactos; listado 1 fila. |
| 2 | Mismo contribuyente, domicilio distinto (A) | Dos fichas de B; historial por CUIT conjunto; F independiente. |
| 3 | A tiene otros locales | Esos EO, visitas e iniciadores de A intactos; CUIT de A no se reescribe. |
| 4 | B tiene otros locales | Datos personales de B y sus otros domicilios intactos. |
| 5 | Notificación y comprobación con reinspecciones pendientes y realizadas | Mismos `notificacion_id` / `comprobacion_id` / `oficio_id` / OT; mismos estados de iniciador e ítem. |
| 6 | Documento con separadores vs duplicado literal | Lookup normalizado encuentra a B; dos ids activos con el mismo normalizado → bloqueo, sin apply. |
| 7 | Cancelar preview / error a mitad de apply | Cero cambios; sin fila de auditoría si no persistió. |
| 8 | Rol `relevador` | 403; no ve la acción. |
| 9 | Confirmación y auditoría | Apply exige `confirmado`; audit `VINCULACION` con alcance y user de sesión (no del body). |
| 10 | `limpiar_contribuyente` | Sigue 422 en PUT actuación y prohibido en este schema. Corrección `DOCUMENTO_AJENO` sigue 409. |
| 11 | Cargas nuevas (regresión) | Mismo CUIT+domicilio → misma ficha; mismo CUIT+otra dirección → otra ficha. |
| 12 | `carga_solo_comprobacion` | `titular_*_historico` no cambia. |
| 13 | Geocode / distrito | Iguales. |
| 14 | Preview coincide con persistido | Mismos ids de alcance. |

---

## 10. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Usar `resolve_contribuyente` y pisar el nombre de B | Canal propio; destino de solo lectura |
| Reasignar un domicilio compartido con otro local de A | Solo `domicilio_ids_ficha`; lookalikes → bloqueo |
| Relevamiento/denuncia en el mismo `domicilio_id` “se muda” con F | Explicitarlo en preview; fork solo si producto lo pide (no automático en V1) |
| Duplicados de documento (`20-…` vs `20…`) | Lookup y conflicto **normalizados**; no UNIQUE todavía (deuda de EDICION.0) |
| Visitas nuevas a F no canónica en caso B | `resolve_establecimiento_por_domicilio` ya apunta al `MIN(id)`; no hace falta merge físico |
| GET `/establecimientos/:id` del EO no canónico | Aceptable; post-éxito navegar al canónico |
| Historial de A “vacío” para este local | Esperado; no es borrado de actuaciones |
| Completar trabajo / Cargar siguen pudiendo reasignar titular si editan el CUIT en grilla | Fuera de este ticket; no cambiar esas cargas. Documentar como riesgo residual |
| Auditoría enum sin valor `VINCULACION` | Migración Alembic **en el ticket de implementación**, no en este |

---

## 11. Decisiones pendientes (producto / técnico)

1. ¿La acción vive como flujo aparte o como rama de “Corregir contribuyente” cuando aparece `DOCUMENTO_AJENO`? (Recomendación: **aparte**, con CTA desde el conflicto.)
2. ¿Tras situación B se reescribe `actuaciones.establecimiento_operativo_id` al canónico o se deja y se confía en la unión por domicilio? (Recomendación V1: **no reescribir**.)
3. ¿Navegar siempre al EO canónico después de B?
4. Si A queda sin locales: ¿aviso de “contribuyente huérfano” o limpieza lógica posterior (otro ticket, sin delete físico)?
5. Relevamiento/denuncia colgado del mismo `domicilio_id`: ¿viaja con la ficha (V1) o exige fork explícito?
6. ¿Permiso solo `admin` o también `usuario` (hoy la corrección usa ambos)?
7. ¿Mostrar en preview los otros locales de B como lista (calle + EO id) para que el usuario verifique que no se tocan?

Ninguna se implementa en VINCULACION.0.

---

## 12. Qué no se hizo (este ticket)

- No se modificó código productivo, tests de comportamiento ni datos.
- No se ejecutaron migraciones ni se agregó enum de auditoría.
- No se quitó el bloqueo `DOCUMENTO_AJENO`.
- No se borraron ni fusionaron contribuyentes ni establecimientos.
- No se cambiaron estados, rutas, actas, expedientes, oficios ni coordenadas.
- No se alteró Cargar actuación ni Completar trabajo.
- No se tocó `limpiar_contribuyente`.
- No se implementó la UI de vinculación.
