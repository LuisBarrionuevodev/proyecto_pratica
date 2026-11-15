# V1.1-ESTABLECIMIENTOS-TITULARIDAD.0 — Corrección de identidad vs cambio de titular

**Fecha:** 2026-11-15  
**Alcance:** diagnóstico y propuesta (sin cambios de código productivo, migraciones ni datos).  
**HEAD analizado:** `9b430ecd` (`HOTFIX-ESTABLECIMIENTOS-TITULAR.1`).  
**Antecedentes:**  
- `Frontend/docs/v1_1_establecimientos_edicion_0_relevamiento.md` (corrección in-place; caso 10 “cambio real de titular” fuera de alcance)  
- `Frontend/docs/v1_1_establecimientos_vinculacion_0_relevamiento.md` y VINCULACION.1 / UX.1–UX.2 (asociación a contribuyente **existente**)  
- `Backend/docs/hotfix_establecimientos_titular_1.md` (UPDATE accidental de la fila compartida)

**Este ticket no levanta el hotfix `CAMBIO_DOCUMENTO`.** No se restauran casos de producción.

---

## Resumen ejecutivo

1. El titular operativo **casi siempre se lee en vivo** (`actuaciones.domicilio_id` → `domicilio.contribuyente_id`). Notificación, comprobación, oficio, expediente e iniciador **no tienen titular propio**. Si se reasigna el contribuyente del domicilio, Gestión, ficha e historial por CUIT **cambian de persona** para visitas viejas y nuevas. Los PDF y `titular_*_historico` (solo carga histórica) no se reescriben.
2. La identidad lógica de ficha es **contribuyente + calle + número** (sin rubro). El mismo local físico con dueños sucesivos **no es una entidad**. Dos titulares en la misma dirección son **dos fichas**. No hay periodo de titularidad.
3. Hay **tres operaciones**, no dos. Mezclarlas reproduce el incidente del hotfix:

| Operación | Intención | Qué muta hoy | Efecto en historial live |
|-----------|-----------|--------------|--------------------------|
| **A. Corregir contribuyente** | Sigue siendo la misma persona; datos mal cargados | UPDATE de la **misma** fila `contribuyente` | Los locales de esa persona siguen juntos; un CUIT nuevo movería **todo** su historial al documento nuevo |
| **A'. Asociar establecimiento** (ya implementada) | Este local **siempre** correspondía a otra persona ya registrada | `domicilio.contribuyente_id` de **esta** ficha | Las visitas de **esta** ficha pasan al CUIT destino (deseable para el error de carga; **no** para una sucesión) |
| **B. Cambiar titularidad** | El local **pasó** a otra persona desde una fecha | **No existe** | Haría falta no reescribir el domicilio de las visitas anteriores |

4. El hotfix vigente es correcto: el canal A no puede cambiar el documento normalizado (salvo formato). Si el CUIT ya existe y es único, se ofrece **A'** (asociación). Un CUIT que todavía no existe **no** se corrige por A hasta un flujo con confirmación “es la misma persona” y preview de **todos** sus locales.
5. Reutilizar A' para B violaría “las actuaciones anteriores conservan el titular”. La vía alineada al modelo actual es **nueva ficha / nuevo domicilio** (mismas coordenadas, otro `contribuyente_id`), **sin** transferir trámites pendientes. Una tabla de periodos sería otra etapa, más cara.

---

## 1. Qué soporta el modelo actual y qué no

### 1.1 Identidad lógica y filas físicas

Fuente: `Backend/app/domains/establecimientos/utils/establecimiento_identidad_logica.py`.

```text
contribuyente 1 ──< domicilio >── 0..1 establecimiento_operativo   (domicilio_id UNIQUE)
                      │
                      ├── actuaciones.domicilio_id          ← titular LIVE
                      ├── actuaciones.establecimiento_operativo_id  (nullable; historial de ficha NO filtra solo por esto)
                      ├── denuncia / relevamiento / iniciador_ruta.domicilio_id
                      └── DomicilioGeocode, distrito_id (no se recalculan en corrección/vinculación)
```

Business key: `(doc:{CUIT normalizado} | cid:{id}, calle lógica, número/esquina)`. **Sin rubro.**

Varios `domicilio` / EO pueden ser la **misma ficha lógica** (forks COW). El listado muestra `MIN(eo.id)`. El historial de ficha une por `domicilio_ids_misma_identidad_logica`.

`contribuyente.documento` está indexado, **no UNIQUE**. Pueden coexistir literales distintos con el mismo normalizado (`DOCUMENTO_AMBIGUO`).

### 1.2 Dónde se obtiene el titular

| Superficie | Fuente | ¿Live? |
|------------|--------|--------|
| Ficha y listado de establecimientos | `eo.domicilio.contribuyente` | Sí |
| Gestión / Ver actuación / export grilla | `resolve_titular_grid_fields`: 1º contribuyente del domicilio, 2º snapshot si `carga_solo_comprobacion` | Sí, salvo histórica |
| Historial de ficha | Sin columna titular; filas por `domicilio_id` de la identidad | El contexto de la ficha es live |
| Historial por DNI/CUIT | `Domicilio.contribuyente_id IN ids_del_documento` + iniciadores por cadena de domicilio | Sí |
| Planificación de ruta | Dirección/rubro/geo; **sin** nombre de titular en pendientes | N/A |
| Completar trabajo | Prefill desde actuación / `iniciador.domicilio.contribuyente` | Sí |
| Notificación, comprobación, oficio, expediente | **Sin** `contribuyente_id` | Titular = el de la actuación ancla |

Snapshots: `titular_nombre_historico`, `titular_apellido_historico`, `titular_razon_social_historica` se escriben en **carga histórica solo comprobación**, no en Cargar actuación ni Completar trabajo normales. La mayoría de las actas **no** tienen titular congelado en la fila.

PDF / Excel ya emitidos: archivo en el momento de generación; corrección y vinculación **no** los regeneran.

### 1.3 ¿El mismo local con titulares sucesivos?

**Hoy no.** Cambiar `domicilio.contribuyente_id` cambia la business key y, en lectura live, **todas** las actuaciones de esos `domicilio_id`. No hay `titular_desde` / `titular_hasta` ni historial de dueños en EO.

Datos que faltan para representar sucesión con certeza:

- Titular al momento de cada visita (snapshot incompleto).
- Fecha efectiva del cambio de dueño (la auditoría de vinculación guarda *cuándo se operó*, no *desde cuándo es el dueño*).
- Puntero de “ficha vigente del local físico” distinto de “ficha del contribuyente + dirección”.

Sin migración de modelo, la sucesión se puede **simular** con dos fichas en la misma dirección (identidad distinta). El listado las muestra separadas. Eso coincide con “no asumir que compartir domicilio es compartir titular”.

### 1.4 Canales que ya existen (no reutilizar mal)

| Canal | Archivos | Hace | No hace |
|-------|----------|------|---------|
| `resolve_contribuyente` | `actuaciones/attach/contribuyente.py` | Upsert por documento **literal**; puede actualizar nombre y reasignar domicilio (Cargar / Completar / Gestión) | No es seguro para la ficha |
| Corrección | `correccion_establecimiento_*` | UPDATE in-place mismo `contribuyente_id`; nombre/razón sí; **CUIT normalizado bloqueado** (`CAMBIO_DOCUMENTO`) | No crea persona; no reasigna titular |
| Asociación | `vinculacion_establecimiento_*` | Reasigna `domicilio_ids_ficha` a un destino **existente y único**; fingerprint; no edita al destino | No crea contribuyente; no es sucesión |
| Hotfix | `validar_documento_propuesto` | Formato equivalente OK; ajeno único → `DOCUMENTO_AJENO` + `ofrece_vinculacion`; si no existe → 409 | — |

`limpiar_contribuyente` sigue prohibido en el schema de corrección (`extra=forbid`).

---

## 2. Cómo se conservaría el historial (establecimiento vs CUIT)

### 2.1 Corregir la misma persona (A), incluido CUIT mal tipeado

**Nombre / apellido / razón (ya vigente):** UPDATE de la fila. Todos los locales de ese `contribuyente_id` muestran el texto nuevo. Historial por CUIT **no cambia de documento**. Preview actual ya cuenta establecimientos y actuaciones afectados.

**CUIT mal tipeado que aún no existe (hoy bloqueado):** la corrección correcta **es** UPDATE de esa misma fila, **después** de confirmar “es la misma persona” y listar **todos** los locales que se enterarán. Entonces:

- Historial por CUIT **viejo**: deja de listar esas visitas (el join usa el documento actual).
- Historial por CUIT **nuevo**: las gana todas (los dos locales del caso 1).
- Historial de **cada ficha**: mismas actuaciones (`domicilio_id` igual).
- Gestión: live → nuevo CUIT.
- PDF / `titular_*_historico`: intactos (pueden mostrar el CUIT viejo).

Eso es coherente con “era un error de carga”. Es **incoherente** si en realidad era un cambio de dueño: de ahí el hotfix.

**CUIT correcto ya registrado (A'):** no UPDATE. Asociación de **esta** ficha (canal existente). El otro local del titular anterior **sigue en A**. Historial CUIT de B gana solo esta ficha. No fusionar personas.

### 2.2 Cambiar titularidad (B) — propuesta alineada al modelo

No reasignar el `domicilio` de las visitas hechas.

Propuesta de etapa 1 de B:

1. Resolver o **crear** el contribuyente destino (alta dedicada; nunca `resolve_contribuyente`).
2. **Clonar** el domicilio ancla (calle, número, rubro, lat, lng, distrito) con `contribuyente_id` del destino. No geocode.
3. Crear **nuevo** `establecimiento_operativo` (nombre de local a definir: copiar vs vacío).
4. Dejar la ficha anterior intacta: mismas actuaciones, mismos iniciadores.
5. No mover `actuaciones.domicilio_id` ni iniciadores.
6. Auditoría `TITULARIDAD`: fecha (`created_at`), usuario JWT, titular anterior, titular nuevo, EO origen, EO nuevo.

Efecto:

| Vista | Después |
|-------|---------|
| Ficha vieja | Sigue con el titular anterior y su historial |
| Ficha nueva | Titular nuevo; historial vacío (o solo visitas posteriores) |
| Historial CUIT anterior | Conserva las visitas de ese local (siguen en el domicilio viejo) |
| Historial CUIT nuevo | Solo lo que ocurra en el domicilio nuevo |
| Misma dirección, dos titulares | Dos filas de listado (keys distintas). No fusionar |
| Pin / distrito | Copiados, no recalculados |

**Costo UX:** el inspector abre “el local de ahora” (ficha nueva) y consulta el pasado en la ficha anterior, o un enlace “titular anterior / historial previo” si producto lo pide. Eso **no existe** hoy; sería UI, no cambio de join.

**Etapa posterior (opcional, migración):** `establecimiento_titularidad` (eo o “lugar” + `contribuyente_id` + `desde`/`hasta`) y/o backfill de snapshots en actuaciones. Hasta no tener titular por visita, Gestión **no puede** mostrar dueños sucesivos sobre el mismo `domicilio_id`.

---

## 3. Impacto en trámites pendientes y realizados

Lectura común: acta/trámite → actuación → `domicilio_id` → contribuyente live. Estados (`estado_iniciador`, `estado_ruta`, `estado_ejecucion`, plazos de notificación, oficios) **no** se tocan en corrección ni vinculación.

### Hoy, si se reasigna el domicilio (asociación A')

| Pieza | Qué se ve |
|-------|-----------|
| Notificación / comprobación realizadas | Mismos ids y estados; titular live = destino |
| Expediente / oficio | Igual; no se recrean |
| Reinspección pendiente (notificación vencida u oficio) | El iniciador **sigue el mismo `domicilio_id`** → aparece como trabajo del **nuevo** titular en live; la ruta no se republica |
| Ítems borrador / publicados / completados | Mismo ítem; ubicación live |
| Completar trabajo | Prefill del contribuyente del domicilio actual |
| Export / PDF ya bajados | Texto viejo |

### Qué haría B (clonar domicilio), si se adopta

Pendientes **permanecen en la ficha vieja** (titular anterior). No hay transferencia automática — alineado al ticket. Producto debe decidir más adelante, caso a caso:

- ¿La reinspección de una notificación al dueño anterior la hace el nuevo? (en general **no** sin decisión jurídica/operativa)
- ¿Un oficio “verificar e informar” sigue al local físico o a la persona?

**Decisión pendiente (no definir transferencia automática en este ticket).**

### Cargas nuevas (Cargar / Completar)

Siguen `resolve_contribuyente` + `resolve_establecimiento_por_domicilio`. Con B-clonado, una visita nueva con el CUIT nuevo y la misma calle cae en la **ficha nueva**. Una visita con el CUIT viejo cae en la **vieja**. Eso es correcto si el inspector carga el titular real del día.

---

## 4. Riesgos y datos que no se reconstruyen con certeza

- Actuaciones operativas **sin** `titular_*_historico`: no se puede afirmar el titular “de entonces” si alguien reasignó el domicilio. La auditoría de vinculación/corrección ayuda solo si el cambio pasó por esos canales.
- Historial por CUIT es una foto **actual** del join, no una línea de tiempo.
- Duplicados de documento normalizado: no se puede asociar ni corregir CUIT con seguridad (`DOCUMENTO_AMBIGUO`).
- Identidad de domicilio incompleta o lookalikes: `AMBIGUEDAD_DOMICILIO`.
- `resolve_contribuyente` en Cargar/Completar/Gestión **sigue** pudiendo reasignar y actualizar nombres por documento literal. Fuera de este epic, pero es un canal paralelo de riesgo.
- Casos ya afectados por el UPDATE pre-hotfix: ver `Backend/docs/hotfix_establecimientos_titular_1.md`. No asumir que todo cambio de documento fue error. No revertir en lote.

---

## 5. Propuesta de UX y seguridad

Dos acciones visibles en la ficha (roles `admin` / `usuario`; relevador sin POST). Distinguir **todos los locales de una persona** vs **un solo local**.

### A — Corregir contribuyente

*“Es la misma persona; sus datos estaban mal.”*

- Sigue el modal actual: nombre, apellido, razón, CUIT/DNI.
- **Hotfix vigente:** si el normalizado cambia y no hay destino único, mensaje de titularidad; no guardar.
- Si hay destino único → fluir a **asociación** (UX.1), no al UPDATE.
- Cuando se habilite corregir CUIT inexistente (etapa A2, **después** de este ticket):
  - Preview: persona actual, datos propuestos, **lista/conteo de todos los establecimientos** de esa fila.
  - Checkbox o confirmación explícita: “Confirmá que es la misma persona. El CUIT se actualizará en todos sus locales.”
  - No crear persona. Transacción + auditoría `CONTRIBUYENTE`. Rollback total si falla.
  - Permisos iguales. JWT `created_by_user_id`.

### A' — Asociación (ya en producción)

No es un tercer botón en la ficha (UX.1 lo integró). Sigue siendo “este establecimiento siempre fue de [B]”. Preview y fingerprint actuales. No usarla como sucesión.

### B — Cambiar titularidad

*“Este local tiene un nuevo titular.”*

- Entrada **aparte** de Corregir (otro botón o selector de intención). Copy de alcance: **solo este local**.
- Pasos: buscar por CUIT → existente (solo lectura, como asociación) **o** alta mínima (nombre/razón + documento) si no existe.
- Preview: ficha actual; titular actual; titular nuevo; “se abrirá una ficha nueva en la misma dirección”; “el historial anterior queda en la ficha actual”; “los demás locales no se modifican”; “los trámites pendientes no se transfieren”; “documentos emitidos no se modifican”; coordenadas no se recalculan.
- Si el destino **ya tiene** ficha lógica en esa dirección: no clonar a ciegas; mostrar conflicto y pedir decisión (usar esa ficha vs bloquear). **No fusionar.**
- Documento ambiguo / domicilio lookalike: un mensaje, sin confirmar.
- Confirmar → transacción atómica + auditoría `TITULARIDAD`. Cancelar o error: nada persistido.
- Post-éxito: navegar a la ficha nueva, con enlace a la anterior.

---

## 6. Casos mínimos

| # | Caso | Hoy | Propuesta |
|---|------|-----|-----------|
| 1 | CUIT mal tipeado, persona con dos locales | `CAMBIO_DOCUMENTO`; ningún local cambia | A2: UPDATE de la fila, preview de **2** locales, confirmación “misma persona” |
| 2 | Documento correcto ya registrado | `DOCUMENTO_AJENO` + asociación de **esta** ficha | Mantener A'; el otro local no se mueve. Si ambos eran error, asociar dos veces o revisar a mano (no merge) |
| 3 | Cambio de dueño; el anterior tiene otro local | No hay canal B. Asociación movería el historial live de **este** local al nuevo CUIT y dejaría el otro local en A | B-clonar: historial de este local **sigue en A**; el otro local de A intacto; ficha nueva para B |
| 4a | Nuevo titular con otros locales | Asociación agrupa solo si misma dirección lógica | B: si B ya tiene esa dirección → conflicto/agrupación explícita, no fork silencioso |
| 4b | Nuevo titular sin otros locales | Asociación OK si B existe | B: clonar domicilio + EO nuevo |
| 5 | Titular que no existe | Corrección bloqueada; asociación `SIN_DESTINO` | B: alta dedicada + clonar. **Fuera de A.** No `resolve_contribuyente` |
| 6 | Notificación o comprobación con reinspección pendiente | Asociación: el iniciador queda en el mismo domicilio → live del destino | B: el pendiente **se queda** en la ficha vieja hasta decisión de producto |
| 7 | Historial por CUIT antes/después | Live | A2 mueve **todas** las visitas de la persona. A' mueve las de **esta** ficha. B **no** mueve las anteriores |
| 8 | Misma dirección, titulares distintos en el tiempo | Dos keys si hay dos contribuyentes; o una sola si se reasignó el domicilio (historial mezclado en live) | B-clonar deja dos fichas. No fusionar |
| 9 | Ambiguo / incompleto | 409 `DOCUMENTO_AMBIGUO` / `AMBIGUEDAD_DOMICILIO` / identidad incompleta | Igual: no adivinar |
| 10 | Cancelar o fallo | Corrección y asociación ya hacen rollback y no auditan éxito | B igual: un commit |

---

## 7. Plan de implementación por etapas

**Etapa 0 (este ticket):** este documento. Hotfix **sigue**.

**Etapa A1 (sin levantar el hotfix):** copy de ficha que separe “misma persona” vs “otro titular”; el CUIT nuevo inexistente sigue bloqueado; asociación intacta.

**Etapa A2 — Corregir documento de la misma persona:**  
Preview + confirmación explícita + UPDATE in-place **solo** si el normalizado **no** pertenece a otro id. Si pertenece, seguir A'. Tests del hotfix invertidos con el nuevo contrato. Auditoría igual (`CONTRIBUYENTE`). **Migración: no.**

**Etapa B1 — Titularidad sin alta:** destino debe existir (reutilizar lookup de vinculación, **otro** apply: clonar domicilio+EO, no reasignar). Tipo de auditoría nuevo. **Migración:** ampliar enum `correccion_establecimiento_tipo_enum` (`TITULARIDAD`). Valorar `created_by_user_id` en `contribuyente` si B2 crea filas.

**Etapa B2 — Alta del titular nuevo:** insert explícito (documento + nombre/razón), sin upsert. Unicidad por documento normalizado; si existe, no crear, ir a B1.

**Etapa B3 (opcional):** enlace “Historial del titular anterior” / línea de tiempo. Sin cambiar joins.

**Etapa C (opcional, cara):** periodos de titularidad o backfill masivo de snapshots + cambiar `resolve_titular_grid_fields`. No hace falta para un MVP de B-clonar.

**Qué no entra:** quitar el hotfix antes de A2; merge de contribuyentes; recalcular coordenadas; reescribir PDF; transferir oficios/notificaciones; tocar Cargar actuación / Completar trabajo en el primer corte (riesgo paralelo de `resolve_contribuyente`: backlog aparte).

---

## 8. Casos de prueba y QA manual (cuando se implemente)

### A2 (corregir CUIT misma persona)

1. Dos locales, CUIT inexistente, confirmar “misma persona”: ambos muestran el nuevo documento; historial CUIT nuevo une las dos fichas; el CUIT viejo queda vacío para esas visitas.
2. Sin confirmar / cancelar / 500: nada cambia, sin auditoría de éxito.
3. Documento de otro único: no UPDATE; oferta de asociación.
4. Duplicado normalizado: un mensaje, no guardar.
5. Solo formato (`33.445566` vs `33445566`): permitido como hoy.
6. Relevador: 403.
7. Request directo a correcciones con CUIT nuevo **antes** de A2: sigue 409 `CAMBIO_DOCUMENTO`.

### B (titularidad)

8. Titular anterior con otro local: ese local intacto; historial CUIT anterior conserva visitas del local cedido.
9. Destino existente sin esa dirección: ficha nueva; geo igual; ficha vieja intacta.
10. Destino ya con esa dirección: no clonar silencioso; conflicto o agrupación explícita.
11. Destino inexistente (B2): alta + ficha nueva; no pisa otra persona.
12. Pendiente de reinspección: sigue en ficha vieja; Completar no prefill del nuevo.
13. Ruta publicada con ítem en el domicilio viejo: estados iguales.
14. Escritorio y celular: dos acciones distinguibles; preview dice “todos los locales” vs “solo este”.

QA manual: nombres/domicilios largos; volver atrás; fallo a mitad (rollback); PDF viejo vs pantalla live.

---

## 9. Decisiones pendientes (bloquean implementación de B y de A2)

1. **¿Tres nombres en UI o dos?** Asociación ya está dentro de Corregir. ¿B es botón propio “Cambiar titularidad”? (recomendado: sí.)
2. **A2:** ¿el UPDATE de CUIT exige checkbox “misma persona” además de Guardar corrección?
3. **Pendientes al cambiar dueño:** ¿siempre quedan en la ficha anterior? (recomendado para el MVP: sí.)
4. **Destino ya tiene la misma dirección:** ¿bloquear, o abrir esa ficha canónica sin clonar?
5. **Nombre del local** en el EO nuevo: ¿se copia o queda vacío?
6. **Fecha del cambio:** ¿`created_at` de auditoría alcanza o hay que pedir “dueño desde”?
7. **¿Se documenta en Gestión** que el titular live puede no coincidir con el PDF?
8. Canal `resolve_contribuyente` (Cargar/Completar): ¿queda como deuda o se alinea en el mismo epic?

---

## Referencias de código

- Identidad: `establecimiento_identidad_logica.py`, `resolve_establecimiento_por_domicilio`
- Titular grilla: `titular_actuacion_resolver.py`
- Historial CUIT: `historial_contribuyente_service.py`
- Corrección / hotfix: `correccion_establecimiento_scope_service.validar_documento_propuesto` (`CAMBIO_DOCUMENTO`)
- Asociación: `vinculacion_establecimiento_apply_service.py` (UPDATE `contribuyente_id` en `domicilio_ids_ficha`)
- Auditoría: `correccion_establecimiento_audit`
- Reinspección notificación: `notificacion_iniciador_service.sync_iniciadores_reinspeccion_notificacion`
- Oficio iniciador: `oficio_iniciador_service.py`
- COW domicilio: `domicilio_operativo_shared.py`
