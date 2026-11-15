# V1.1-ESTABLECIMIENTOS-TITULARIDAD.1-RELEVAMIENTO — Corrección de CUIT y sucesión en una ficha

**Fecha:** 2026-11-15  
**Alcance:** relevamiento y diseño (sin código productivo, datos ni migraciones).  
**HEAD analizado:** `3ea4be5e` (`TITULARIDAD.0`). El hotfix `CAMBIO_DOCUMENTO` en `9b430ecd` **sigue vigente**.  
**Base:** `Frontend/docs/v1_1_establecimientos_titularidad_0_relevamiento.md`. Este ticket **cambia la meta de B**: una **sola vista del local** con historial por titular, no dos fichas sueltas.

No se desactiva el hotfix. No se fusionan ni borran registros. No se inventan fechas ni titulares.

---

## Resumen ejecutivo

1. Confirmar TITULARIDAD.0: el titular operativo es **live** (`domicilio.contribuyente_id`). La ficha se agrupa por **contribuyente + calle + número**. Asociación reasigna **solo** los domicilios de la ficha elegida y, en live, esas visitas “cambian de dueño”. El hotfix impide UPDATE de CUIT normalizado distinto; si el documento es de otro id único, ofrece asociación de **esa** ficha.
2. Corregir CUIT de la **misma persona** (todos sus locales) y **asociar fichas** a un contribuyente ya existente son operaciones distintas. La asociación actual **no** corrige sola todos los locales del CUIT mal cargado.
3. Cambiar titularidad **no** puede reutilizar esa asociación: mezclaría el pasado con el dueño nuevo. Tampoco alcanza clonar una segunda ficha si el usuario debe ver **un solo local**.
4. **Recomendación B:** introducir un **lugar físico** (dirección lógica, sin titular) + **periodos de titularidad** + **congelar el titular vigente** en las actuaciones de ese lugar **en el momento del cambio** (no backfill con fechas inventadas). Listado y ficha se agrupan por lugar; cada visita muestra el titular de su etapa.
5. **Recomendación A2 (CUIT inexistente):** UPDATE de la misma fila `contribuyente`, con preview de **todos** los establecimientos y confirmación explícita de misma persona. Fingerprint. Hotfix hasta que eso exista.
6. **Recomendación A3 (CUIT ya existente):** no pisar al destino. Preview del encontrado **y** de los locales del origen. El usuario elige el alcance (esta ficha / un subconjunto / todos los del origen). Reasignar solo esos `domicilio.contribuyente_id`. Sin merge físico.

---

## 1. Limitaciones confirmadas del modelo actual

Verificado en código vigente (mismos símbolos que TITULARIDAD.0).

### 1.1 Titular por vista

| Vista | Qué usa hoy |
|-------|-------------|
| Ficha / listado EO | Join `eo.domicilio.contribuyente` |
| Gestión, Ver actuación, export | `resolve_titular_grid_fields`: domicilio.contribuyente; si no hay, snapshot solo si `carga_solo_comprobacion` |
| Historial de ficha | Actuaciones con `domicilio_id` en la identidad lógica; **sin** columna titular |
| Historial DNI/CUIT | `Domicilio.contribuyente_id` del domicilio de la visita + iniciadores por ese domicilio |
| Ruta pendiente | Dirección/rubro; **sin** titular |
| Completar trabajo | Prefill live del domicilio del iniciador/actuación |
| Notificación, comprobación, oficio, expediente | Sin titular; cuelgan de la actuación |

`titular_*_historico` se escribe en carga **histórica** de comprobación, no en Cargar/Completar normales. La mayoría de las actas **no** tienen titular congelado.

Auditoría de ficha (`correccion_establecimiento_audit`): valores anteriores/nuevos, usuario, fecha de **operación**, alcance JSON. No guarda “dueño desde” ni titular por actuación. PDF emitidos no se reescriben.

**No reconstruible con certeza:** titular real de una visita operativa si alguien reasignó el domicilio después; si un cambio de CUIT pre-hotfix pisó la fila compartida; fechas de sucesión no registradas.

### 1.2 Identidad lógica

`business_key_tuple` = contribuyente lógico (`doc:{norm}` o `cid:{id}`) + calle + número. **El local no existe aparte del titular.** `eo_canonico` = `MIN(id)` del grupo. Historial de ficha = `domicilio_ids_misma_identidad_logica`.

Consecuencia: dos dueños en la misma calle son dos grupos. Un `UPDATE domicilio.contribuyente_id` mueve el grupo entero de visitas de esos domicilios al CUIT nuevo.

### 1.3 Asociación de ficha (A')

`vinculacion_establecimiento_apply_service`: `UPDATE contribuyente_id` en `domicilio_ids_ficha` (ancla + forks de **esa** identidad). No edita al destino. Fingerprint. Situación B si el destino ya tiene la misma dirección lógica: el listado agrupa; no borra filas.

Historial live de **esas** visitas pasa al CUIT destino. Otros locales del origen **no** se tocan. Por eso **no** sirve como “corregí el CUIT de la persona en todos sus locales”.

### 1.4 Hotfix

`validar_documento_propuesto`: mismo normalizado → OK (formato). Normalizado distinto y otro id único → `DOCUMENTO_AJENO` + `ofrece_vinculacion`. Si no hay otro id → `CAMBIO_DOCUMENTO` (409 en apply, sin auditoría de éxito). Request directo incluido.

---

## 2. Alternativas para el mismo local con titulares sucesivos

Criterio de producto: **una ficha**, historial con etapas, visitas viejas **no** como si siempre hubieran sido del nuevo, otros locales intactos, sin transferencia automática de pendientes, sin geocode.

| Alternativa | Cómo se identifica el local | Titular de cada actuación | Ficha única | Historial por CUIT | Migración | Rendimiento / mantenimiento |
|-------------|----------------------------|---------------------------|-------------|--------------------|-----------|-----------------------------|
| **0. Reusar asociación** | Sigue contrib+dirección | Live del domicilio (cambia todo el pasado) | Una ficha, historial **incorrecto** | Anterior pierde visitas; nuevo las gana como propias | Ninguna | Barato y **inválido** para B |
| **1. Clonar ficha** (TITULARIDAD.0) | Dos keys (dos titulares) | Live de cada domicilio | **Dos** vistas | Correcto por CUIT; el local se parte | EO+domicilio nuevos | Barato; choca con “una sola vista” |
| **2. Snapshot masivo + seguir live** | Igual que hoy | Snapshot si existe, si no live | Sigue atada al titular actual | Sigue el join live | Backfill incompleto | Exports/Gestión hay que cambiar el resolver; datos viejos vacíos |
| **3. Lugar físico + periodos** (recomendada) | Dirección lógica **sin** titular (`lugar` o clave calle+nro+depto) | Periodo vigente en `fecha` de la visita **si** el periodo tiene `desde` cierto; si no, snapshot congelado en el cambio / vacío | Listado y GET agrupan por lugar; cabecera = titular **vigente** | CUIT = visitas cuyo titular (periodo o snapshot) es esa persona, **no** el dueño actual del lugar | Tabla lugar y/o `establecimiento_titularidad`; enum auditoría; lecturas de listado/historial | Un join más en ficha/listado; búsquedas por CUIT dejan de ser “todos los domicilio.contribuyente_id actuales” |
| **4. Periodos sin lugar, sobre el EO actual** | Sigue el EO 1:1 domicilio | Igual que 3, anclado al EO | Una URL `/establecimientos/:id` | Igual que 3 si el historial de ficha **deja** de filtrar solo por contrib+calle | Solo `titularidad` + ampliar historial a “mismo lugar” (hay que definir lugar igual) | Parece menos migración y **reintroduce** el problema: el EO hoy **es** contrib+domicilio |

**Descartes:** 0 por regla de historial; 1 por regla de ficha única; 2 solo no alcanza (sin periodo la cabecera no cuenta etapas y el CUIT live sigue mintiendo).

**Recomendación: alternativa 3.** El local tiene identidad de **lugar**. El titular es una **etapa**. Las actuaciones no cambian de `domicilio_id` al suceder el dueño (o el domicilio del lugar se mantiene como ancla física y el contribuyente vigente va en el periodo, no pisando el pasado).

Modelo propuesto (nombres tentativos):

```text
establecimiento_lugar          — id, clave_direccion (calle+número/esquina), geo/distrito de referencia
establecimiento_operativo      — sigue 1:1 domicilio (compatibilidad); + lugar_id
establecimiento_titularidad    — lugar_id, contribuyente_id, vigente_desde, vigente_hasta NULL,
                                 origen (CAMBIO_TITULARIDAD), created_by_user_id, created_at
actuaciones                    — se agrega titular_contribuyente_id_historico nullable
                                 (además de los strings ya existentes)
```

Al **cambiar titularidad**:

1. Congelar en cada actuación del lugar **sin** snapshot: copiar el contribuyente **vigente ahora** (el anterior), no una fecha de dueño inventada.
2. Cerrar el periodo abierto (`vigente_hasta = now()` o fecha **informada por el usuario** si la carga; si no la hay, usar la de operación y **mostrarla como “registrado el…”**, no “dueño desde…”).
3. Abrir periodo del nuevo contribuyente (`vigente_desde` = misma marca).
4. Actualizar el `contribuyente_id` **solo** del domicilio ancla **vigente** del lugar (para Cargar/Completar/geo actuales) **o** mantener el ancla y que las cargas nuevas resuelvan por lugar+titular vigente. La segunda es más limpia y exige tocar `resolve_establecimiento_por_domicilio` (etapa B2). En B1 se puede actualizar el ancla vigente **después** de congelar snapshots: el pasado ya no depende del live.

Registros históricos sin datos: etapa sin `vigente_desde` cierto → en UI **no** poner año inventado; etiqueta “Titular al registrar el cambio” / “Sin fecha de inicio”. Visitas sin snapshot ni periodo que las cubra: titular “No registrado” (`—`), nunca el dueño actual por defecto.

Listado: agrupar por `lugar_id` (o clave de dirección). Una fila, titular = periodo abierto. Rendimiento: índice `(lugar_id, vigente_hasta)` y `(clave_direccion)`. El listado actual ya agrupa en memoria por business key; pasar a SQL por `lugar_id` es más estable, no más pesado.

Búsquedas por CUIT: filtrar actuaciones por `titular_contribuyente_id_historico` **o** por periodo que cubre `actuaciones.fecha` **o** (solo si no hay snapshot ni periodo) por `domicilio.contribuyente_id` **deprecado** — este último fallback es el riesgo actual; hay que apagarlo en el lugar una vez migrado.

Exportaciones: misma regla que Gestión (`resolve_titular_grid_fields` pasa a: snapshot/historico_id → periodo por fecha → vacío). PDF viejos no se tocan.

---

## 3. Diseño de corrección segura de CUIT (A)

Hotfix **activo** hasta A2/A3 en producción. `resolve_contribuyente` no se usa.

### 3.1 Casos

| # | Situación | Qué cambiaría | Fichas / historial CUIT | Preview | ¿Bloqueo? |
|---|-----------|---------------|-------------------------|---------|-----------|
| 1 | Un local, mismo id, CUIT nuevo **inexistente** | UPDATE `contribuyente.documento` (y nombre si vino) de **esa** fila | Esa ficha igual; CUIT viejo deja de listar esas visitas; el nuevo las lista | Actual vs propuesto; **1** establecimiento; texto de misma persona | No, si confirma |
| 2 | Varios locales del mismo `contribuyente_id`, CUIT inexistente | Igual UPDATE de **una** fila | **Todos** esos locales; historial CUIT se mueve **entero** | Lista de locales (dirección + nombre de local si hay); conteo de actuaciones por local; frase acordada | No, si confirma el alcance completo |
| 3 | CUIT de **otro id único** | **No** UPDATE de B. Reasignar `domicilio.contribuyente_id` solo de los locales **marcados** | Locales no marcados siguen en A; marcados: historial live pasa a B (error de carga: el pasado **sí** debía ser B) | Datos de A; datos de B (solo lectura); locales de A y de B; alcance elegido | Si nombres muy contradictorios: advertir, no auto-elegir qué nombre sobrevive (B no se edita) |
| 4 | Varios ids con el mismo normalizado | Nada | Nada | Mensaje único `DOCUMENTO_AMBIGUO` | Sí |
| 5 | Nombres contradictorios A vs B (caso 3) | Igual que 3; **no** copiar nombre de A sobre B | Igual | Mostrar ambos titulares; “No se modifican los datos personales del contribuyente encontrado” | No por el nombre solo; sí si además hay duplicado de documento o lookalike de domicilio |
| 6 | Locales/actuaciones mezclados o lookalike de dirección | Nada hasta revisar | — | `AMBIGUEDAD_DOMICILIO` / identidad incompleta | Sí |
| 7 | Preview obsoleta | Nada | Nada | `PREVIEW_STALE` / fingerprint | Sí; volver a consultar |

Cancelar = no writes. Fallo = rollback, sin auditoría de éxito.

¿Actualizar todos los locales confirmados sin borrar/fusionar? **Sí:** caso 2 es un UPDATE de persona; caso 3 es N UPDATEs de `domicilio.contribuyente_id` de las fichas elegidas. Filas A y B permanecen. Si A queda sin domicilios, **no** se borra.

### 3.2 Preview y confirmación (A2 — CUIT inexistente)

Texto fijo:

> Esta corrección se aplicará a todos los establecimientos asociados. Confirmá que se trata del mismo contribuyente.

Mostrar: nombre/CUIT actuales y propuestos; tabla de establecimientos alcanzados (domicilio, no IDs de entrada; detalle opcional); “Los documentos ya emitidos conservarán sus datos.”

Fingerprint: hash de `contribuyente_id` + documento actual normalizado + documento propuesto + `establecimiento_ids` del alcance. Si alguien asocia un local entre medio → stale.

Permisos: `admin` / `usuario`. JWT. Transacción única. Auditoría `CONTRIBUYENTE` como hoy.

### 3.3 Preview y alcance explícito (A3 — CUIT existente)

No llamar “fusión”. Copy:

> Encontramos un contribuyente con ese documento. Elegí qué establecimientos de esta persona querés asociar. Los datos de la persona encontrada no se modifican.

Opciones de alcance (explícitas, default **solo esta ficha** — igual que hoy — para no sorprender):

- Solo este establecimiento (canal A' actual).
- Todos los establecimientos de esta persona (lista tildable, todos on si elige esa opción).
- Subconjunto.

Consecuencias: historial CUIT de B **gana** las visitas de los locales marcados (live). Es correcto **solo** si esas visitas siempre fueron de B (CUIT mal tipeado en A). **No** usar A3 para sucesión.

Si algún local marcado comparte dirección lógica con B: misma advertencia de agrupación que vinculación situación B.

Fingerprint incluye el set de `domicilio_id` elegidos + ids A y B + docs.

Implementación: extender vinculación a un apply “lote” reutilizando el service actual **por ficha** en una transacción, o un endpoint `asociaciones/lote` con el mismo validador. No un UPDATE ciego de “todos los de A” sin lista.

Request directo: mismo 409/validación; sin `confirmado` + fingerprint no hay write.

---

## 4. Diseño de ficha única con titulares sucesivos (B)

### 4.1 Cabecera

Un local: nombre, rubro, dirección, coordenadas (las vigentes, **sin** recálculo).  
Titular **actual** = periodo abierto.  
Si hay periodos cerrados: “Titulares anteriores” colapsado (nombre + CUIT + “Registrado el {fecha operación}”; “Dueño desde {fecha}” **solo** si el usuario la cargó).

Acciones: Corregir contribuyente (el **vigente**); Cambiar titularidad.

### 4.2 Historial en una sola ficha

Una lista cronológica de actuaciones del **lugar** (todos los `domicilio_id` ligados al lugar, no solo contrib+calle del vigente).

Cada fila: fecha, tipo, actas, **titular de esa visita** (snapshot / `titular_contribuyente_id_historico`). Agrupar visualmente por etapa si hay más de un titular, con encabezado de etapa sin inventar fechas.

Pendientes del titular anterior: sección **“Trámites del titular anterior”** (no mezclados con “pendientes del actual”). Estados intactos. Completar trabajo sigue el iniciador/domicilio original (prefill del anterior).

### 4.3 Historial por CUIT

Anterior: visitas cuyo titular histórico/periodo es A, **incluidas** las de este local anteriores al cambio.  
Nuevo: solo las posteriores (y otros locales suyos).  
No usar el join “domicilios que **hoy** tienen este contribuyente_id” como única fuente para ese lugar, una vez migrado.

### 4.4 Casos de destino

| Destino | Tratamiento |
|---------|-------------|
| Existe, otros locales | Periodo nuevo en **este** lugar. No tocar sus otros EO |
| Existe, ya tuvo actividad en **esta** dirección | Puede haber otro lugar/ficha o forks. Si es el **mismo lugar**, no crear otro: abrir periodo (si ya es titular vigente, no-op). Si es otra ficha lógica hoy (contrib+dir), **unificar en el lugar** es decisión: mostrar “Ya hay historial de esta persona en esta dirección” y asociar al mismo `lugar_id` sin fusionar filas físicas de EO |
| No existe | Alta dedicada (documento + nombre/razón), sin `resolve_contribuyente`. Luego el periodo. `created_by_user_id` en contribuyente si se agrega columna |
| Documento ambiguo | Bloqueo, un mensaje |

Otros establecimientos de A y B: intactos. Geo: copiar/conservar, no geocode.

---

## 5. Trámites pendientes y rutas

Hoy (asociación A'): el iniciador queda en el mismo `domicilio_id` → live del nuevo titular.

Con B (lugar + periodo + freeze):

| Situación | Hoy si se asociara | Propuesta B |
|-----------|--------------------|-------------|
| Notificación a reinspeccionar | Pendiente “del nuevo” en live | Sigue del **anterior**; visible en la ficha única bajo trámites anteriores |
| Comprobación + oficios | Igual | Igual: no se mueven FKs ni estados |
| Iniciador pendiente / en ruta publicada | Ítem y estado iguales; titular live nuevo | Ítem y estado iguales; titular de esa parada = anterior |
| Reinspección ya hecha | Acta live nuevo | Acta con snapshot del titular de entonces (congelado al cambiar o ya histórico) |

**Regla de implementación:** no `UPDATE` de `iniciador_ruta`, `ruta_item`, OT, resultados.  
**Decisión funcional pendiente:** ¿el inspector completa esa reinspección desde la misma ficha (recomendado: sí, bloque “titular anterior”) o solo desde Completar trabajo / bandeja? ¿Se permite cargar una visita **nueva** del titular actual el mismo día que sigue abierta la del anterior? (recomendado: sí, son etapas distintas).

---

## 6. Experiencia de usuario

### Corregir contribuyente

> Es la misma persona. Sus datos estaban mal.

1. Formulario actual (nombre, razón, CUIT).  
2. Ver alcance.  
3a. CUIT inexistente (A2, futuro): lista **todos** los establecimientos; frase de confirmación; Guardar.  
3b. CUIT de B único: pantalla de **asociación con alcance** (esta ficha / todos / elegir); Sí, asociar.  
3c. Ambiguo / hotfix (hoy): un mensaje; no guardar.  
Volver/Cancelar sin cambios.

### Cambiar titularidad

> Este local tiene un nuevo titular.

1. CUIT/DNI del nuevo; si no existe, alta corta.  
2. Preview: local (dirección); titular anterior; titular nuevo; “El historial anterior se mantiene a nombre de {anterior}”; “Los demás establecimientos de cada uno no se modifican”; “Los trámites pendientes no pasan al nuevo titular”; documentos emitidos conservan datos.  
3. Fecha de inicio **opcional** (“si la conocés”). Si falta, no se afirma “dueño desde”.  
4. Sí, registrar cambio.

Historial: una ficha; etapas con titular; fechas solo ciertas.

Sin IDs ni “iniciadores” de entrada; detalle de alcance opcional como en UX.2.

---

## 7. Migraciones, riesgos, etapas

### Migraciones (cuando se implemente B, no ahora)

1. `establecimiento_lugar` + `lugar_id` en EO (nullable al inicio).  
2. `establecimiento_titularidad`.  
3. `actuaciones.titular_contribuyente_id_historico` (nullable).  
4. Enum auditoría `TITULARIDAD`.  
5. Backfill **lugar**: agrupar EO actuales por clave de **dirección** (calle+número), **no** por contribuyente — o por contrib+dir y luego unir al cambiar titular. Unir de entrada todas las fichas de la misma calle **sin** mirar titular mezclaría dos comercios distintos en el mismo número: **peligro**. Backfill inicial: un `lugar` por identidad lógica **actual** (contrib+dir). La unión de dos periodos en el mismo lugar ocurre **solo** en un cambio de titularidad explícito, no en un job ciego.

Backfill de snapshots: **no** rellenar visitas viejas con el titular actual. Solo congelar en el apply de B, las de **ese** lugar, las que estén vacías, con el titular **antes** del cambio.

### Riesgos

- `resolve_contribuyente` en Cargar/Completar sigue reasignando por documento literal (canal paralelo).  
- Unificar lugares por dirección sola crea fichas falsas.  
- Historial CUIT mal migrado si se sigue filtrando solo por `domicilio.contribuyente_id`.  
- Periodos sin `desde` cierto mal etiquetados como “dueño desde”.  
- Rendimiento: índices en `lugar_id` y en `titular_contribuyente_id_historico`.

### Plan por etapas (implementación futura)

| Etapa | Qué | Hotfix |
|-------|-----|--------|
| 0 | Este documento | On |
| A1 | Copy: misma persona vs nuevo titular; CUIT nuevo sigue bloqueado | On |
| A2 | Corregir CUIT inexistente + confirmación todos los locales + fingerprint | Se **reemplaza** `CAMBIO_DOCUMENTO` solo por este contrato |
| A3 | Asociación con alcance multi-ficha | Asociación 1-ficha sigue |
| B0 | Congelar snapshot al asociar/cambiar (aunque B1 no esté) para no perder live | On |
| B1 | Tablas lugar+periodo; apply cambiar titularidad; ficha única lee periodos | On para A si A2 no salió |
| B2 | Cargar/Completar resuelven lugar+titular vigente; historial CUIT por titular histórico | — |
| B3 | Alta titular nuevo en B; fecha opcional “dueño desde” | — |

A2 puede ir **antes** de B. B no debe reusar A3.

---

## 8. Pruebas y QA (cuando haya implementación)

1. Corregir solo nombre, varios locales: todos live; CUIT igual; PDF igual.  
2. CUIT nuevo inexistente (A2): todos los locales; historial CUIT nuevo une; viejo no lista esas visitas.  
3. CUIT existente: default **esta** ficha; opción todos; B no cambia de nombre; locales no tildados en A intactos.  
4. Cambiar titular: otros locales de A intactos; visitas viejas con titular A en la **misma** ficha.  
5. Destino existente vs alta nueva.  
6. Dos etapas en la misma dirección, una ficha.  
7. Historial agrupado/identificado por titular; sin fechas inventadas.  
8. CUIT A y CUIT B: atribución correcta.  
9. Notificación y oficio pendientes: siguen del anterior, visibles en la ficha, estados iguales.  
10. Ruta publicada e ítem; reinspección hecha con titular congelado.  
11. Documento duplicado: bloqueo. Fecha desconocida: “Registrado el”, no “Dueño desde”.  
12. Fingerprint stale, cancelar, excepción: nada persistido.  
13. Relevador 403; `limpiar_contribuyente` 422; JWT.  
14. Lat/lng/distrito iguales; sin cola de geocode.

QA manual: escritorio/celular; nombres largos; dos acciones inconfundibles; Volver; no éxito en error de red.

---

## 9. Decisiones funcionales que siguen abiertas

1. En A3, ¿el default es “solo esta ficha” (recomendado) o “todos los locales de A”?  
2. ¿A3 se llama “asociar establecimientos” y nunca “fusionar personas”? (recomendado: sí.)  
3. Pendientes del anterior: ¿completables desde la ficha única?  
4. ¿Fecha “dueño desde” opcional en B1 o se pospone a B3?  
5. ¿Un `lugar` se crea solo en el primer cambio de titular, o se backfillea para todos los EO?  
6. ¿Se alinea `resolve_contribuyente` en el mismo epic o queda deuda?  
7. Nombres contradictorios A vs B: ¿solo advertencia (recomendado) o bloqueo?

Ninguna de estas se resuelve en este ticket. El hotfix permanece hasta A2.
