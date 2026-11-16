# V1.1-CONTRIBUYENTE-UNICIDAD.1 — Documentos normalizados entre canales

**Fecha:** 2026-11-15  
**HEAD de referencia previo:** `8467b269` (UNICIDAD.0).  
**Alcance:** backend de resolución de contribuyente + mensajes de Cargar/Completar. Sin fusión de históricos, sin unique sobre `contribuyente.documento`, sin cambio de titularidad ni de la regla de nombre/apellido/razón social.

---

## Qué quedó cubierto

| Canal | ¿Escribe `contribuyente.documento`? | Protección |
|-------|--------------------------------------|------------|
| Cargar actuación (`create_service` → `resolve_contribuyente`) | Alta / reuso | Lookup normalizado + `GET_LOCK('corr_doc:{norm}')` hasta commit/rollback + reserva en `contribuyente_documento_unico` |
| Completar trabajo (cierre e identidad operativa) | Alta / reuso | Mismo helper |
| PUT de actuación (grilla / CRUD) | Alta / reuso | Mismo helper |
| PATCH HTTP | Deshabilitado (405). El service interno, si se reactivara, ya llama al mismo helper | |
| Corregir CUIT (A2, Establecimientos) | UPDATE in-place | Mismo `GET_LOCK` y la misma tabla de reserva (`reclamar_documento_normalizado`) |
| Vincular ficha | No crea ni cambia documento | Sin lock de documento (no es escritor). Varios ids → `DOCUMENTO_AMBIGUO` |
| Denuncia / relevamiento | No | — |

Escritores productivos de `contribuyente.documento`: **solo** `resolve_contribuyente` (INSERT) y el apply A2 (UPDATE). No hay otro `Contribuyente(...)` en código de producción.

---

## Comportamiento habitual (sin pasos nuevos)

1. El inspector carga documento y datos y guarda / completa.
2. Si hay **una** coincidencia activa por documento normalizado (sin `.` `-` espacios), se reutiliza esa fila.
3. El establecimiento sigue la identidad lógica vigente: mismo titular + mismo domicilio → misma ficha; otro domicilio → otra ficha del mismo titular.
4. El historial por DNI/CUIT no cambia: sigue uniendo por normalizado.
5. Si no existe, se crea como hoy, con lock compartido frente a altas simultáneas.
6. Nombre, apellido y razón social: **misma regla de siempre**. Clave presente (incluido `None`/vacío) pisa el campo; clave ausente no lo toca. Completar sigue mandando las cuatro claves.

---

## Estrategia de lock / constraint

**No** se agregó UNIQUE sobre `contribuyente.documento` ni columna generada normalizada. En copia pueden existir duplicados activos; un unique global **fallaría** o exigiría fusionar. El ticket pide no fusionar.

### `GET_LOCK('corr_doc:{norm}', 10)`

- Misma clave que CUIT.1, ahora también en `resolve_contribuyente`.
- Se toma **antes** de buscar/crear.
- Si esta sesión ya lo tiene, no se vuelve a pedir (evita deadlock reentrante).
- Timeout 10 s → Cargar/Completar: `DOCUMENTO_EN_USO` 409; A2 conserva el mensaje de corrección.

### Duración real del bloqueo

GET_LOCK vive en la **conexión MySQL**, no en la transacción InnoDB.

| Momento | Qué pasa |
|---------|----------|
| Hasta `commit` del service llamador | Lock retenido (Cargar/Completar/PUT/A2) |
| `after_commit` de SQLAlchemy | `RELEASE_LOCK` sobre el DBAPI fijado al adquirir |
| `after_rollback` (error, teardown, `session.rollback`) | `RELEASE_LOCK` |
| Apply A2 | Sigue liberando en `finally` además de los eventos (doble `RELEASE_LOCK` es inocuo) |
| Cierre de la conexión MySQL | El servidor suelta GET_LOCK si quedó alguno |

No se usa `PoolEvents.reset`: en SQLAlchemy 2 ese evento también corre en resets transaccionales y soltaría el lock **antes** del commit del llamador.

Tras tomar el lock:

1. `SELECT ... FOR UPDATE` sobre `contribuyente_documento_unico` (PK del normalizado).
2. Carga del titular con `SELECT ... FOR UPDATE` por `id` (no `session.get`: en REPEATABLE READ el get por PK usa el snapshot y **no ve** el alta que el otro hilo acaba de confirmar).

Un `SELECT` normal reusa el snapshot de la transacción (p. ej. el INSERT de la OT en Cargar). La lectura locking ve lo commitido.

No se libera dentro de `resolve_contribuyente` antes del commit del llamador: si se soltara ahí, el segundo hilo podría insertar otra fila antes de que el primero confirme.

### Tabla `contribuyente_documento_unico`

PK = documento normalizado. Coherencia:

| Operación | Qué hace |
|-----------|----------|
| Alta nueva en `resolve` | INSERT de la reserva en la misma transacción |
| Reuso de coincidencia única | Backfill si faltaba la fila |
| Cambio de CUIT A2 | `reclamar`: INSERT del nuevo + DELETE de la reserva anterior de **ese** id |
| Rollback | INSERT/DELETE de reserva se deshacen con la transacción |
| Varios activos con el mismo normalizado | **No** se inserta reserva; error `DOCUMENTO_AMBIGUO` |
| Reserva de un id con `deleted_at` | Se reasigna al id activo único (no fusiona personas) |

No es garantía frente a un canal futuro que haga `INSERT`/`UPDATE` de documento **sin** pasar por el helper o por A2. Hoy no hay ese canal.

---

## Excepción: documento ambiguo

Varios contribuyentes activos con el mismo normalizado:

- No se crea otro, no se elige, no se fusiona.
- `DocumentoIdentidadError` / HTTP 409, `codigo=DOCUMENTO_AMBIGUO`.
- Mensaje: *«No pudimos identificar este documento con seguridad. Contactá a administración para revisarlo.»*
- Cargar: commit `ok=false` con `errors.doc_nro`; no hay toast de éxito ni reset del formulario.
- Completar: 409 con `errors.doc_nro`; el catch solo marca el campo, no cierra el trabajo.

---

## Migraciones

Ninguna. Se reutiliza `contribuyente_documento_unico` de CUIT.1 (`h1i2j3k4l5m6`).

---

## Datos existentes

Consultas de solo lectura: `Backend/scripts/diagnostico_contribuyente_documento_duplicados.sql`.

No se consultó producción. Sobre `digitaliza_test` el relevamiento .0 ya había reproducido duplicados de formato (`33445566` / `33.445566`) y de carrera; esas filas de diagnóstico se revirtieron. Este ticket **no** corrige ni fusiona históricos. Los duplicados que existan seguirán disparando `DOCUMENTO_AMBIGUO` hasta revisión administrativa.

---

## Plan de despliegue

1. Correr el SQL de solo lectura en una **copia** (o `digitaliza_test`). Anotar cantidad de `doc_norm` con `COUNT(*)>1`. No escribir.
2. Desplegar backend (helper + eventos de sesión + HTTP 409) y frontend (mapeo del mensaje al campo DNI).
3. Verificar Cargar / Completar habitual y un caso ambiguo de prueba.
4. No aplicar unique generado en esta entrega.

**Reversión:** revertir el commit. La tabla de reserva puede quedar (CUIT.1 la necesita). No hace falta borrar filas de `contribuyente_documento_unico`.

---

## Limitaciones

1. Sin UNIQUE de MySQL sobre el normalizado, un writer **nuevo** que evite el helper podría volver a duplicar. Hoy los escritores productivos pasan por el helper o A2.
2. Duplicados históricos no se unen: el usuario ve el mensaje de administración.
3. Completar/CRUD en UI siguen rechazando puntos y guiones (`validateDocNro`); Cargar puede mandar `33.445566` y ahora reutiliza al equivalente `33445566` si es único.
4. `20-12345678-9` (13 caracteres) se rechaza en backend **sin truncar**; no entra en `VARCHAR(11)`.
5. La regla de overwrite de nombres no se tocó: Completar con las cuatro claves vacías puede limpiar el titular compartido. Eso es otro ticket.

---

## Pruebas

Backend `tests/test_contribuyente_unicidad_1.py` y extensión de `test_resolve_contribuyente.py`. Frontend: Cargar (`ok=false` ambiguo sin reset) y Completar (`errors.doc_nro`).
