# V1.1-ESTABLECIMIENTOS-EDICION.0 — Corrección de identidad y domicilio

**Fecha:** 2026-11-14  
**Alcance:** diagnóstico (sin cambios de código, migraciones ni datos).  
**HEAD analizado:** `d96f1714` (`main`).  
**Relacionado:** `Frontend/docs/v1_1_act_edit_0_relevamiento.md` (edición posterior en Gestión / Ver actuación). Este ticket se centra en **corregir desde la ficha** sin reconstruir el recorrido.

---

## Resumen ejecutivo

1. La ficha operativa (`establecimiento_operativo`) ancla **1:1** a un `domicilio`. La identidad de negocio es **contribuyente lógico + calle lógica + número/esquina** (sin rubro). El historial de la ficha **no** filtra solo por `establecimiento_operativo_id`: agrupa actuaciones cuyos `domicilio_id` comparten esa identidad.
2. Titular y dirección en casi todas las pantallas se **leen en vivo** por FK (`domicilio.contribuyente_id` y el propio `domicilio`). Corregir **en el lugar** el mismo `Contribuyente` o el mismo `Domicilio` se refleja en actuaciones, bandejas, rutas y Completar trabajo **sin republicar ni cambiar estados**.
3. Hay **tres excepciones** que no se actualizan solas: snapshots históricos (`titular_*_historico` en `carga_solo_comprobacion`), PDFs ya descargados, y **coordenadas / distrito** (la corrección documental de calle **no debe** recalcular geocode; el pin y el distrito pueden quedar desfasados respecto del texto).
4. **No existe** hoy un canal de corrección en Ver establecimiento: la ficha es solo lectura. Editar titular o calle desde Gestión de una actuación usa `resolve_contribuyente` / `aplicar_edicion_domicilio_operativo`, con riesgos de **reasignar titular** (si cambia el documento a uno existente) o de **fork COW** (si el domicilio está compartido).
5. Cambio de titular (otro contribuyente) y fusión de personas **quedan fuera**. El hotfix de `limpiar_contribuyente` debe permanecer.

**Dirección de la futura solución:** un flujo dedicado en la ficha, con vista previa de alcance, confirmación, transacción atómica y auditoría. Dos operaciones distintas:

| Operación | Qué muta | Alcance |
|-----------|----------|---------|
| Corregir identidad del mismo contribuyente | Fila `contribuyente` (mismo `id`) | Todos los domicilios/fichas/actuaciones que apuntan a ese `contribuyente_id` (y equivalentes por documento normalizado, solo para contar alcance) |
| Corregir domicilio de **esta** ficha | Fila `domicilio` ancla del EO (in-place; sin geocode) | Actuaciones e iniciadores que apuntan a **ese** `domicilio_id` (y forks de la misma identidad lógica, ver §C) |

---

## 1. Mapa de entidades y vínculos reales

```text
contribuyente 1 ──< domicilio >── 0..1 establecimiento_operativo
                      │
                      ├── actuaciones.domicilio_id
                      ├── actuaciones.establecimiento_operativo_id  (ficha canónica, a menudo MIN id)
                      ├── denuncia.domicilio_id
                      ├── relevamiento.domicilio_id
                      └── iniciador_ruta.domicilio_id

iniciador_ruta ── tipo + un origen:
  relevamiento_id | denuncia_id | notificacion_id + actuacion_id(base)
  | oficio_id + comprobacion_id + actuacion_id(origen)

ruta_item ── iniciador_ruta_id
          ── actuacion_id (desde publicar)

actuaciones ── notificacion_id / comprobacion_id  (actas del día)
comprobacion ── oficio ── expediente
notificacion ── expediente
```

**No hay** calle, CUIT ni nombre copiados en notificación, comprobación, oficio, expediente, `ruta_item` ni `iniciador_ruta` (salvo el FK de domicilio).

**Identidad lógica** (`establecimiento_identidad_logica.py`):

| Pieza | Clave |
|-------|--------|
| Contribuyente | `doc:{documento_normalizado}` o, sin documento, `cid:{contribuyente_id}` |
| Calle | `slug_key(calle_key \|\| calle_normalizada \|\| calle)` |
| Número | `NUMERO` → slug del número; `ESQUINA` → `ESQ:{slug(esquina_normalizada\|\|numero)}` |

Varios `domicilio` / varios EO pueden pertenecer a la **misma** ficha lógica (forks COW). El listado muestra el EO **canónico** (`MIN(id)`). El historial une por `domicilio_ids_misma_identidad_logica`.

### Cómo se abre la ficha

`ActuacionDetalleDialog` (modo lectura) muestra **Ver establecimiento** solo si `establecimiento_operativo_id` no es null. Navega a `/establecimientos/:id` **sin query params**.

Fuentes:

- `Frontend/src/Containers/Actuaciones/Components/ActuacionDetalleDialog.tsx`
- `GET /establecimientos-operativos/:id`
- `GET /establecimientos-operativos/:id/actuaciones`

El historial **no** exige `actuaciones.establecimiento_operativo_id = :id`. Una actuación histórica puede verse en la ficha aunque su FK de EO sea otra o nula, si su `domicilio_id` comparte la business key.

---

## 2. A — Establecimiento e identidad

### Conjunto afectado por cada corrección

**Corregir contribuyente (mismo `contribuyente_id`):**

| Recurso | Cómo entra |
|---------|------------|
| Otros domicilios del titular | `domicilio.contribuyente_id` |
| Otras fichas EO | 1:1 con esos domicilios |
| Actuaciones | `actuaciones.domicilio_id` → esos domicilios |
| Iniciadores / ruta items | `iniciador.domicilio_id` o domicilio efectivo del origen |
| Denuncias / relevamientos | si su domicilio tiene el mismo `contribuyente_id` |
| Historial por documento | `contribuyente_ids_por_documento` (normaliza puntos/guiones/espacios) |

**Corregir domicilio de la ficha abierta (`eo.domicilio_id`):**

| Recurso | Cómo entra |
|---------|------------|
| Esta ficha | ancla 1:1 |
| Actuaciones con ese `domicilio_id` | lectura en vivo |
| Otras actuaciones de la identidad lógica en **otro** `domicilio_id` (fork) | **no** cambian el texto, salvo que se decida actualizar también los forks (decisión pendiente, §11) |
| Otros establecimientos del mismo contribuyente (otra calle/número) | **fuera de alcance** |
| Iniciador con el mismo `domicilio_id` | lectura en vivo; si está desalineado, el domicilio **efectivo** puede seguir el origen |

### Si la identidad corregida coincide con otra ficha

Hoy `resolve_establecimiento_por_domicilio` no crea un EO nuevo si ya hay canónico para esa business key: **une lógicamente**. Quedan EO duplicados físicos (1:1 por domicilio). El listado los colapsa; el historial se mezcla.

Una corrección de calle/número que **iguale** otra ficha existente del mismo titular tendría el mismo efecto. La futura UI debe **advertir y bloquear o pedir confirmación explícita de unión lógica**, sin fusionar filas ni borrar EO.

### Actuaciones históricas vs ficha física

Es el caso 4: historial por identidad lógica, FK de EO distinta. Corregir el `domicilio` ancla del EO canónico **no** reescribe las filas fork. El texto de cada actuación sigue el `domicilio_id` de esa actuación. Hay que mostrar en la vista previa cuántas actuaciones leen **este** domicilio vs cuántas están en forks.

---

## 3. B — Contribuyente compartido

### Modelo

`contribuyente`: `apellido`, `nombre`, `razon_social`, `documento` (NOT NULL, índice **no único**), `created_at`, `updated_at`, `deleted_at`. **No** hay `created_by_user_id`.

FK directa: `domicilio.contribuyente_id`, `solicitud_carnet_manipulador.contribuyente_id`. El resto llega por domicilio.

### Escritura actual (`resolve_contribuyente`)

Archivo: `Backend/app/domains/actuaciones/attach/contribuyente.py`.

- Lookup: `documento == strip(doc_nro)` y `deleted_at IS NULL` (match **exacto**, no normalizado).
- Si existe: actualiza nombre/apellido/razón **in-place** en esa fila.
- Si no existe: INSERT.
- Si el `doc_nro` nuevo ya es de **otra** fila: **devuelve esa otra fila**. El update de actuación entonces **reasigna** `domicilio.contribuyente_id` (posible COW). **No fusiona.** Es el cambio de titular accidental que este ticket debe evitar.

`contribuyente_ids_por_documento` (historial / identidad lógica) sí normaliza `. - espacio`. Pueden existir dos filas (`20-33344455-5` vs `20333444555`) que el historial trata como la misma persona y el upsert no.

### Lectura vs copia

| Superficie | Fuente |
|------------|--------|
| Gestión, bandejas, ficha, Completar trabajo, planificación | JOIN `domicilio.contribuyente` (`resolve_titular_grid_fields`) |
| `carga_solo_comprobacion` | `actuaciones.titular_*_historico` — **no** se actualiza al corregir `contribuyente` |
| Solicitud de carnet | FK congelada al crear |
| Relevamiento / denuncia **sin** titular en el domicilio | no muestran titular hasta el cierre (`titular_operativo_visible_para_iniciador`) |

### Estrategia segura (mismo contribuyente)

1. Operar **siempre** sobre el `contribuyente_id` del domicilio ancla de la ficha abierta.
2. Nombre / apellido / razón social: `UPDATE` in-place de esa fila.
3. Documento: `UPDATE` in-place **solo si** ningún otro `contribuyente` activo (normalizado) tiene ese documento. Si hay conflicto → 409 con datos del otro registro, **sin** reasignar FK ni fusionar.
4. No llamar a `resolve_contribuyente` desde este flujo (ese helper es upsert/reasignación).
5. Vista previa: contar domicilios, EO y actuaciones que cuelgan de ese `contribuyente_id` (y avisar si hay otros IDs con el mismo documento normalizado, sin unirlos).
6. No tocar `limpiar_contribuyente`. No poner `contribuyente_id = NULL` en domicilios.

---

## 4. C — Domicilio

### Campos a corregir

`calle`, `numero`, `numero_tipo` (`NUMERO` / `ESQUINA`), `esquina_*`. Al guardar, el canal actuación ya corre `normalizar_domicilio_en_sesion` (`calle_key`, `calle_normalizada`, catálogo). Eso **sí** debe mantenerse para búsquedas e identidad lógica.

**No** recalcular ni reemplazar `domicilio_geocode.lat/lng`. El patrón existente es `preservar_geocode_existente_al_editar_domicilio`: actualiza `addr_hash` al texto nuevo y marca `source=MANUAL` para que `on_domicilio_changed` no reprocese.

### Qué queda coherente y qué no (restricción de coordenadas)

| Dato | Tras corrección in-place sin geocode |
|------|--------------------------------------|
| Texto en ficha, actuaciones, bandejas, PDF **nuevo** | Nuevo (normalizado) |
| Pin del mapa | **Viejo** lat/lng |
| `distrito_id` | **No se recalcula** (el backfill solo llena NULL) |
| Filtros por distrito / mapa operativo | Siguen el distrito/coords viejos |
| Identidad lógica (calle_key / número) | Cambia con el texto → la ficha puede **separarse o unirse** a otro grupo |

**Tratamiento propuesto:** advertencia explícita en la confirmación: *“El mapa y el distrito no se actualizarán. Si la dirección nueva no corresponde al punto actual, hay que corregir geolocalización por el canal de gestión de domicilios (fuera de este flujo).”* No disparar `on_domicilio_changed` ni `schedule_geocode_after_grid_commit`.

### Alcance de filas domicilio

El EO abierto tiene **un** `domicilio_id`. Las actuaciones de la ficha pueden estar en **forks**. Opciones (decisión pendiente):

- **A (recomendada para V1):** mutar solo `eo.domicilio_id`. Alcance = actuaciones/iniciadores con ese id. Mostrar cuántas actuaciones de la ficha **no** se actualizarán porque están en otro fork.
- **B:** mutar todos los `domicilio_id` de `domicilio_ids_misma_identidad_logica` **antes** del cambio de clave. Más completo; más riesgo de tocar un fork creado a propósito (otro rubro/contrib).

No clonar domicilio en este flujo si el objetivo es **corregir el error de carga**. El COW de gestión de actuaciones existe para no contaminar relevamiento/denuncia compartidos; aquí el usuario eligió **esta** ficha.

### Otros establecimientos del mismo titular

Otra business key (otra calle/número) = otro `domicilio_id`. No se toca.

---

## 5. D — Actuaciones y trámites

Relaciones reales (no unir por domicilio compartido):

| Trámite | Vínculo |
|---------|---------|
| Acta inspección / notificación / comprobación / clausura / decomiso | `actuacion_id` |
| Reinspección por notificación | `iniciador.notificacion_id` + `iniciador.actuacion_id` = actuación **base** |
| Oficio / reinspección oficio | `oficio.comprobacion_id` → actuación origen; `iniciador.oficio_id` |
| Expediente | `notificacion_id` / `comprobacion_id` / `oficio_id` |

Notificación, comprobación, oficio y expediente **no** guardan dirección ni titular. Se ven actualizados en bandejas e historial documental porque el presenter hace JOIN a `act.domicilio`.

Antecedentes de reinspección: la visita nueva tiene su propio `actuaciones.domicilio_id` (en publicar se copia el domicilio efectivo del iniciador). Si ese id es el mismo que el de la ficha, la corrección se ve; si hubo fork al cerrar, no.

---

## 6. E — Iniciadores e ítems de ruta

| Estado | ¿Se ve sola la corrección de ficha? | Notas |
|--------|--------------------------------------|--------|
| Pendiente de asignación | Sí, si `iniciador.domicilio_id` (o el efectivo del origen) es el domicilio corregido | Titular puede seguir oculto en relevamiento/denuncia hasta el cierre |
| Planificado / ruta borrador | Sí (join en vivo). PR2 aún **puede** propagar origen → iniciador | No republicar |
| Ruta publicada | La visita ya tiene `act.domicilio_id`. Si es el mismo id → sí. PR2 **no** pisa el iniciador en PUBLICADA/EN_CURSO | No cambiar estado ni republicar |
| Trabajo en proceso | Completar trabajo lee `item.actuacion.domicilio` | Igual que publicada |
| Trabajo completado | Sí sobre el `domicilio_id` final de la actuación | No reabrir |
| Reinspección notificación | Bandeja usa domicilio de la **actuación base** | Corregir el domicilio de esa base / ficha se ve en pendientes |
| Reinspección oficio | Bandeja usa domicilio de la actuación origen | Igual |

No actualizar `estado_iniciador`, no recrear `RutaItem`, no llamar a publicar.

Si el iniciador quedó desalineado (PR5 domicilio efectivo ≠ `iniciador.domicilio_id`), la ficha corrige el origen; el efectivo ya prefiere origen cuando aplica. No hace falta sync masivo.

---

## 7. F — Superficies

| Superficie | Automático si UPDATE in-place | Copiado / aparte |
|------------|-------------------------------|------------------|
| Ficha Establecimientos (listado y detalle) | Sí | Hoy **sin** edición |
| Ver / Editar actuación | Sí (JOIN) | Histórica: snapshot titular |
| Gestión de actuaciones | Sí | PUT actual puede reasignar titular si cambia documento |
| Notificaciones e historial | Sí | — |
| Comprobaciones, recorrido, historial documental | Sí | — |
| Pendientes de reinspección | Sí (domicilio de actuación origen) | — |
| Rutas y Completar trabajo | Sí (join / domicilio efectivo) | `nombre_fantasia` / `angulo_esquina` viven en **relevamiento**, no en domicilio |
| Búsquedas y filtros (calle, contrib, distrito) | Calle/contrib sí; **distrito no** si no se toca geocode | Identidad lógica cambia con `calle_key` |
| Exportaciones / PDF **nuevos** | Sí (se arman al generar) | PDF ya guardado en disco del usuario: no |
| Mapa | Pin viejo | Advertir |

---

## 8. G — Seguridad de una futura implementación

### Permisos

La UI de establecimientos es de **admin** y **usuario**. Inspector (`relevador`) y perfil `relevamiento` no entran a `/establecimientos`. El GET de API **no** filtra por rol (solo JWT).

Propuesta: corrección de identidad/domicilio **solo admin** (o un permiso nuevo). Inspector no corrige datos compartidos. El hotfix de `limpiar_contribuyente` sigue en PUT de actuaciones.

### Vista previa + confirmación

Antes de guardar, mostrar:

- Operación: *corregir contribuyente* vs *corregir domicilio de esta ficha* (nunca mezcladas en un solo submit).
- Valores anteriores → nuevos.
- Conteos: establecimientos, actuaciones, iniciadores pendientes/en ruta, denuncias/relevamientos que cuelgan del mismo id.
- Si hay forks: cuántas actuaciones de la ficha **no** usarán el domicilio que se edita.
- Si el documento nuevo choca con otro `contribuyente_id`.
- Si la nueva business key coincide con otra ficha.
- Aviso de mapa/distrito no actualizados.

Confirmación explícita (checkbox o modal). Sin “guardar” silencioso.

### Auditoría

No hay tabla de auditoría de contribuyente/domicilio. `contribuyente` no guarda actor.

Hace falta una tabla nueva, por ejemplo `correccion_establecimiento_audit`:

- `id`, `created_at`, `created_by_user_id` (sesión JWT, **nunca** del body)
- `tipo`: `CONTRIBUYENTE` \| `DOMICILIO`
- `contribuyente_id` / `domicilio_id` / `establecimiento_operativo_id`
- `payload_antes` / `payload_despues` (JSON)
- `alcance` (conteos al momento de confirmar)

Migración Alembic **sí** (solo esta tabla). No alterar tablas operativas.

### Atómico

Un único `commit` de servicio: UPDATE de la fila + INSERT de auditoría. Si el 409 de documento o la unión de ficha se detecta **antes** del commit, no escribir nada. Helpers sin commit (regla de arquitectura del repo).

### Conflictos

| Conflicto | Tratamiento |
|-----------|-------------|
| Documento ya usado por otro `contribuyente_id` | 409, mostrar nombre/documento/id del otro. No fusionar. No reasignar domicilios. |
| Business key de domicilio igual a otra ficha | 409 o confirmación de “unión lógica” (decisión). No borrar EO. |
| Domicilio compartido con relevamiento/denuncia | Advertir; preferir in-place porque el usuario corrigió **esta** ficha. No desvincular contribuyente. |
| Intento de vaciar titular | Rechazar (misma semántica que `limpiar_contribuyente`). |

### Protección contribuyente–domicilio

No usar `resolve_contribuyente` ni `_aplicar_rubro_contrib_seguro` en este canal. No enviar `limpiar_contribuyente`. No cambiar `domicilio.contribuyente_id` en la corrección de identidad (el id permanece). En la corrección de domicilio, no tocar `contribuyente_id` ni `rubro_id`.

---

## 9. Casos 1–11

| # | Caso | Qué haría la solución futura |
|---|------|------------------------------|
| 1 | Un contribuyente, un EO, una actuación | UPDATE contribuyente y/o domicilio ancla. Alcance: 1 ficha, 1 actuación. |
| 2 | Varios EO; se corrige nombre/CUIT | UPDATE de la fila contribuyente. Todos los EO y actuaciones de esos domicilios leen el nuevo valor. |
| 3 | Corrección de domicilio en uno de varios EO | Solo el `domicilio_id` de esa ficha. Los demás EO intactos. |
| 4 | Varias actuaciones agrupadas por identidad lógica | Historial sigue unido. El texto nuevo aparece en las que apuntan al domicilio editado; las de forks se listan en la vista previa. |
| 5 | Notificación pendiente de reinspección | El iniciador no copia dirección. La bandeja lee la actuación base → se ve el cambio. Estado del iniciador igual. |
| 6 | Comprobación + oficios / reinspecciones | Oficio/expediente sin dirección propia. Origen y visitas con el mismo `domicilio_id` se actualizan. No se recrean oficios. |
| 7 | Ítem en ruta publicada | El item no copia calle. Completar trabajo / PDF de ruta **nuevo** leen el domicilio de la actuación/iniciador. No republicar. |
| 8 | Dirección corregida con coordenadas | `preservar_geocode`. Pin y distrito iguales. Advertencia en UI. |
| 9 | Documento que ya existe | 409, sin merge ni reasignación. |
| 10 | Cambio real de titular | Fuera de alcance. UI: si el documento es de otra persona, no es “typo”; no hay botón de reasignar en este ticket. |
| 11 | Falla a mitad de corrección | Un commit; rollback total. Auditoría solo si el UPDATE persistió. |

---

## 10. Propuesta técnica (límites)

### Canal nuevo (no reutilizar PUT `/actuaciones/:id`)

El PUT de actuación mezcla corrección de nombre (deseable) con reasignación por documento (indeseable) y puede forkar domicilio. La ficha necesita un servicio propio, por ejemplo:

- `POST /establecimientos-operativos/:id/correcciones/preview`
- `POST /establecimientos-operativos/:id/correcciones` (contribuyente **o** domicilio, no ambos)

Servicios bajo `app/domains/establecimientos/services/`, con JWT `created_by_user_id`, preview de alcance, 409 de conflictos.

### Qué reutilizar

- `normalizar_documento` + `contribuyente_ids_por_documento` (detección de colisión **normalizada**, más estricta que el upsert actual).
- `domicilio_ids_misma_identidad_logica` / `count_actuaciones_identidad_logica` (alcance).
- `preservar_geocode_existente_al_editar_domicilio` + `normalizar_domicilio_en_sesion`.
- Bloqueos existentes de `limpiar_contribuyente`.

### Qué no reutilizar

- `resolve_contribuyente` como motor de este flujo.
- `on_domicilio_changed` / cola de geocode.
- Propagación masiva a iniciadores (`propagar_domicilio_a_iniciadores_activos`) como paso automático.
- Fusión de EO (`audit_establecimiento_duplicados.py` sigue siendo solo auditoría).

### Migraciones / fuera de foco

| Ítem | ¿Este epic? |
|------|-------------|
| Tabla de auditoría de correcciones | Sí (Alembic) |
| UNIQUE de `contribuyente.documento` | **No** en el primer corte: hay duplicados literales; el 409 debe usar normalización. UNIQUE queda como deuda |
| Backfill de geocode/distrito | Fuera. Canal de gestión de domicilios |
| Reescribir `titular_*_historico` | No (snapshot a propósito) |
| Unificar EO duplicados físicos | No |
| ACT-EDIT.1 (edición en Gestión de actuación base) | Paralelo; no sustituye este flujo |
| Permiso de rol en GET establecimientos | Fuera, salvo cerrar el POST de corrección a admin |

---

## 11. Plan por etapas

**Etapa 0 (este ticket):** diagnóstico. Cerrado con este documento.

**Etapa 1 — Preview de alcance (solo lectura)**  
Endpoint de preview: conteos y conflictos **sin** persistir. UI en la ficha (admin): dos acciones, “Corregir contribuyente” y “Corregir domicilio”. Tests de conteo (casos 1–4, 9).

**Etapa 2 — Corregir contribuyente**  
UPDATE in-place + auditoría + 409 documento existente. Tests: mismo id, todos los EO, no merge, no `limpiar_contribuyente`, transacción.

**Etapa 3 — Corregir domicilio**  
UPDATE in-place del ancla + normalización de calle + preservar geocode + advertencia mapa/distrito. Tests: otros EO intactos, coords iguales, `source=MANUAL`, identidad lógica, forks informados.

**Etapa 4 — Superficies de lectura**  
Regresión: ficha, gestión, notificaciones, comprobaciones, pendientes, ruta publicada, Completar trabajo, PDF/Excel **nuevos**. No tocar Completar trabajo ni reinspecciones.

Cada etapa: commit propio, sin push implícito, sin migrar datos operativos.

---

## 12. Pruebas de regresión mínimas (futuras)

- Hotfix: PUT actuación con `limpiar_contribuyente: true` sigue 422 (`test_acta_identidad_gestion_1.py`).
- Nombre corregido en ficha aparece en GET actuación, listado EO y bandeja de notificación **sin** cambiar `contribuyente_id`.
- Documento colisionante → 409; ambos `contribuyente_id` y todos los `domicilio.contribuyente_id` iguales que antes.
- Domicilio de ficha A no altera ficha B del mismo titular.
- Tras corregir calle, `domicilio_geocode.lat/lng` y `distrito_id` iguales; `calle_key` actualizado.
- Iniciador `PENDIENTE` / ítem `PUBLICADA` / `FINALIZADO`: mismos `estado_iniciador` / `estado_ruta` / `estado_ejecucion`.
- Reinspección notificación y oficio: siguen vinculados por `notificacion_id` / `oficio_id`, no se crean iniciadores nuevos.
- Histórica `carga_solo_comprobacion`: `titular_*_historico` no cambia.
- Preview coincide con el persistido (mismos conteos) o no hay persistencia si preview falló.

---

## 13. Decisiones pendientes (producto / técnico)

1. ¿El documento se corrige en V1 o solo nombre/apellido/razón (CUIT más tarde, con 409)?
2. ¿Al corregir domicilio se toca solo el ancla del EO o también los forks de la identidad lógica?
3. Si la nueva dirección iguala otra ficha: ¿bloquear (409) o confirmar unión lógica sin borrar filas?
4. ¿Quién puede corregir: solo `admin` o también `usuario`?
5. ¿Hay que mostrar en la ficha un aviso permanente de “mapa no recalculado” después de corregir calle?

Ninguna de estas decisiones se implementa en ESTABLECIMIENTOS-EDICION.0.

---

## 14. Qué no se hizo (este ticket)

- No se modificó código productivo ni tests de comportamiento.
- No se ejecutaron migraciones ni correcciones masivas.
- No se cambiaron coordenadas, estados, rutas, actas, expedientes ni oficios.
- No se fusionaron contribuyentes ni establecimientos.
- No se alteró Completar trabajo ni reinspecciones.
- No se tocó la protección contra `limpiar_contribuyente`.
