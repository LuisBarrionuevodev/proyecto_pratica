# V1.1-CONTRIBUYENTE-UNICIDAD.0 — Documentos entre canales

**Fecha:** 2026-11-15  
**Alcance:** solo diagnóstico. No se modificó código productivo, datos, migraciones ni el comportamiento de los flujos.  
**HEAD de referencia:** `687df4a8` (CUIT.1).  
**Entorno de las pruebas de este documento:** `digitaliza_test` (no producción). Las filas de diagnóstico se revirtieron o se borraron al terminar.

El uso habitual que el QA describió se conserva y **no se rediseña**: si el documento coincide de forma literal, Cargar / Completar reutilizan el contribuyente; el mismo domicilio cae en la misma ficha lógica; otro domicilio es otro establecimiento de la misma persona; el historial por DNI/CUIT junta esas visitas.

---

## Resumen ejecutivo

1. **Cargar actuación, Completar trabajo, PATCH y PUT de actuación** escriben contribuyente solo a través de `resolve_contribuyente`. Esa función busca `documento == valor_ingresado` (literal, con `strip`). Si existe, reutiliza y puede actualizar nombre/apellido/razón. Si no, crea otra fila. No hay `GET_LOCK`, ni unique de MySQL, ni `contribuyente_documento_unico`.
2. **Corregir contribuyente** (CUIT.1) y **vincular ficha** buscan por documento **normalizado**. La corrección de CUIT libre sí usa `GET_LOCK` + `contribuyente_documento_unico`. La vinculación no crea contribuyentes.
3. Los tres ejemplos del ticket (`20123456789`, `20-12345678-9`, `20 12345678 9`) **normalizan al mismo valor**, pero **2 y 3 no entran en la columna** `contribuyente.documento` (`VARCHAR(11)`): MySQL responde `Data too long`. No se da por hecho que el usuario pueda cargarlos.
4. **Sí se reprodujo** un duplicado activo con formatos que sí caben: `33445566` y `33.445566` (mismo normalizado, distinto literal) → dos filas; el historial las une.
5. **Sí se reprodujo** el hueco de concurrencia del mismo literal: dos `SELECT` que no ven fila + dos `INSERT` → dos activos con el mismo `documento`. En una corrida “libre” de `resolve_contribuyente` a veces gana el segundo y actualiza el primero; el hueco existe igual.
6. `GET_LOCK` y `contribuyente_documento_unico` **no son garantía global**: solo el apply A2 de corrección los usa.
7. Hace falta **tocar el helper compartido** `resolve_contribuyente` (lo llaman Cargar y Completar) para cerrar el hueco **sin cambiar la experiencia** de reutilización. Una protección solo en Establecimientos no alcanza.

No hay evidencia en este ticket de duplicados en producción: no se consultó producción.

---

## 1. Mapa por canal

### 1.1 `resolve_contribuyente` (núcleo de Cargar / Completar / PATCH / PUT)

Archivo: `Backend/app/domains/actuaciones/attach/contribuyente.py`.

| Tema | Comportamiento vigente |
|------|------------------------|
| Validación | `doc_nro` obligatorio si hay apellido, nombre o razón. `strip`. Sin tope de 11 en Python. |
| Búsqueda | **Literal:** `Contribuyente.documento == doc` y `deleted_at IS NULL`. `.first()`. |
| Existe | Reutiliza esa fila. Actualiza apellido/nombre/razón **solo si la clave vino en el payload** (un `None` borra el campo). `flush`. |
| No existe | `INSERT` + `flush`. No `commit` (lo hace el service llamador). |
| Bloqueos | Ninguno. Sin `for_update`, sin `GET_LOCK`. |
| Unique MySQL | Índice `ix_contribuyente_documento`, **`Non_unique = 1`**. |

Es el **único** `Contribuyente(...)` de código productivo (además de tests).

### 1.2 Cargar actuación

- UI (`CargarActuacionNuevaModal`): campo «CUIT / DNI» **sin `maxLength`**, sin `validateDocNro`. El valor se manda crudo al validate-row / commit.
- Backend: `ActuacionRowIn.doc_nro` sin `max_length`. Mapper arma `contribuyente.doc_nro` con `strip`. `crear_actuacion_desde_payload` → `resolve_contribuyente` → `get_or_create_domicilio` → `try_vincular_establecimiento_operativo_desde_actuacion` → `commit`.
- Domicilio: busca calle+número literales; si el titular no es el mismo y el domicilio está compartido, **fork** (PR12). Luego la ficha lógica es contribuyente **normalizado** + calle + número (`resolve_establecimiento_por_domicilio` / `eo_canonico`).
- Carga histórica solo comprobación: **prohíbe** `contribuyente` / `doc_nro`; no crea titular.

### 1.3 Completar trabajo

- UI: «CUIT / DNI» sin `maxLength`. El submit pasa por `validateActuacionFormForSubmit` → `validateDocNro`: **mínimo 7 dígitos, sin puntos ni guiones**.
- Backend: si el body trae titular, `_resolve_contribuyente_para_domicilio_cierre` llama a `resolve_contribuyente` con las cuatro claves (un vacío normalizado puede limpiar nombre). Si no trae titular, reutiliza el del domicilio de la actuación.
- Verificar e informar / identidad histórica: también `resolve_contribuyente`.
- Transacción: la del cierre (idempotencia de ítem aparte; no cubre documento).

### 1.4 Edición de actuación (PUT grilla / CRUD)

- UI: `validateDocNro` (rechaza separadores) y `normalizeActuacionRowForCrudSubmit` (deja solo dígitos si hay ≥7).
- Backend: `update_service` → `resolve_contribuyente` si el payload identifica titular.

### 1.5 PATCH de actuación

- Arma `doc_nro` / apellido / nombre (no razón social en este armado) y llama `resolve_contribuyente`. Misma búsqueda literal.

### 1.6 Corregir contribuyente (Establecimientos)

- UI: `maxLength={11}`.
- Schema: `max_length=11`.
- Búsqueda de conflicto: **normalizada** (`contribuyente_ids_por_documento`).
- CUIT libre: UPDATE de la **misma fila**, fingerprint, `GET_LOCK('corr_doc:{norm}')`, reserva en `contribuyente_documento_unico`.
- CUIT de otro id único: no UPDATE; ofrece vinculación de **esta** ficha.
- Varios ids: `DOCUMENTO_AMBIGUO`.
- No crea contribuyente.

### 1.7 Vincular establecimiento

- UI: `maxLength={11}`.
- Lookup **normalizado**. No crea ni edita al destino. Reasigna `domicilio.contribuyente_id` de la ficha. Fingerprint. Sin `GET_LOCK` de documento (no inserta titular).

### 1.8 Historial por DNI/CUIT

- `normalizar_documento` (quita `.` `-` espacios) y SQL `REPLACE` encadenado.
- Une actuaciones de **todos** los ids activos con ese normalizado (domicilio de la visita).
- Acepta en la **consulta** formatos con guiones/puntos aunque no quepan en la columna (prueba `test_api_busca_dni_con_puntos_y_guiones`).

### 1.9 Identidad lógica del establecimiento

`business_key_tuple` = `doc:{normalizado}` (o `cid:{id}`) + calle lógica + número/esquina. **Sin rubro.**  
`eo_canonico` = `MIN(id)` del grupo.  
Consecuencia: dos filas de contribuyente con el mismo normalizado y la misma dirección se **agrupan en una ficha** aunque sean dos personas en BD.

### 1.10 Otros

- Denuncia / relevamiento: no crean `Contribuyente`.
- No hay otro endpoint productivo que haga `Contribuyente(...)`.

---

## 2. Formatos de documento

`normalizar_documento` deja:

| Entrada | Longitud | Normalizado | ¿Cabe en `VARCHAR(11)`? |
|---------|----------|-------------|-------------------------|
| `20123456789` | 11 | `20123456789` | Sí |
| `20-12345678-9` | 13 | `20123456789` | **No** (`Data too long`) |
| `20 12345678 9` | 13 | `20123456789` | **No** (mismo límite) |
| `33.445566` | 9 | `33445566` | Sí |
| `33445566` | 8 | `33445566` | Sí |
| `20.12345678` | 11 | `2012345678` | Sí |
| `2012345678` | 10 | `2012345678` | Sí |

### Qué acepta cada formulario / endpoint

| Canal | Separadores | Tope |
|-------|-------------|------|
| Cargar actuación (UI + API fila) | No valida dígitos. Puede mandar puntos/guiones. | UI sin tope; BD 11 |
| Completar trabajo (UI) | `validateDocNro`: **rechaza** puntos y guiones | Implícito (solo dígitos, ≥7) |
| CRUD actuación (UI) | Rechaza separadores; al enviar deja solo dígitos | Solo dígitos |
| Corregir / Vincular | Cualquier texto ≤11 (puntos permitidos, p. ej. `33.445566`) | 11 |
| Historial (query) | Puntos, guiones y espacios | No escribe la columna |
| `resolve_contribuyente` | Lo que reciba, `strip`, igualdad literal | Falla MySQL si >11 |

Los tres valores del ticket **no se cargan los tres** por UI+BD. El caso real de “mismo CUIT, distinto tipeo” que **sí entra** es del estilo `33445566` vs `33.445566`, o Cargar con puntos y Completar/CRUD con solo dígitos.

---

## 3. Concurrencia y evidencias

### Qué cubre cada mecanismo hoy

| Mecanismo | Canales | Qué garantiza | Qué no |
|-----------|---------|---------------|--------|
| Índice `ix_contribuyente_documento` | Lecturas | Lookup por valor crudo | Unicidad |
| `GET_LOCK('corr_doc:{norm}')` | Solo apply A2 | Serializa correcciones de ese normalizado en este MySQL | Cargar, Completar, PATCH, PUT, vinculación |
| `contribuyente_documento_unico` | Solo apply A2 al **cambiar** CUIT | Un dueño de la reserva por normalizado | Altas de `resolve_contribuyente`; no hay backfill de todos los contribuyentes |
| Unique MySQL sobre `contribuyente.documento` | — | **No existe** | — |

### Pares

| Par | Resultado |
|-----|-----------|
| Corrección A2 ↔ Cargar | Código: Cargar no toma el lock ni mira la reserva. Puede crear otra fila con el CUIT recién corregido o el mismo normalizado en otro formato. **No corrido el par mixto a dos hilos.** |
| Corrección A2 ↔ Completar | Igual. Completar, si el UI manda solo dígitos, puede **no ver** un registro guardado con puntos. |
| Dos cargas nuevas (mismo literal) | **Reproducido** en test con la misma secuencia SELECT+INSERT de `resolve_contribuyente` y una barrera: dos filas `67516387` (ids 1274 y 1275), luego borradas. Una corrida directa de la función a veces serializa por timing y el segundo **actualiza** al primero. |
| Dos cierres | Mismo helper, mismo hueco. **No corrido** el cierre HTTP completo a dos hilos. |
| Dos correcciones A2 mismo CUIT libre | Cubierto por CUIT.1 (409 / un ganador). |

### Distinción pedida

| Hecho | Tipo |
|-------|------|
| Índice de `documento` no es unique (`Non_unique=1` en `digitaliza_test`) | Confirmado (SHOW INDEX) |
| `20-12345678-9` no se persiste (`Data too long`) | Confirmado en test |
| `33445566` y `33.445566` → dos contribuyentes; historial lista ambos ids | Confirmado en test (`resolve_contribuyente`) |
| Dos INSERT concurrentes del mismo literal → dos activos | Confirmado en test (barrera SELECT+INSERT) |
| Carrera Cargar ↔ Corregir | Posibilidad por código, no comprobada a dos hilos |
| Duplicados en producción | **No comprobado** (no se consultó producción) |

---

## 4. Consultas de solo lectura

Ejecutar primero en copia o `digitaliza_test`. **No correr en producción sin autorización.** No fusionan ni borran.

```sql
-- Activos que comparten documento normalizado
SELECT
  REPLACE(REPLACE(REPLACE(c.documento, '.', ''), '-', ''), ' ', '') AS doc_norm,
  COUNT(*) AS filas,
  GROUP_CONCAT(c.id ORDER BY c.id) AS contribuyente_ids,
  GROUP_CONCAT(c.documento ORDER BY c.id) AS documentos_crudos
FROM contribuyente c
WHERE c.deleted_at IS NULL
GROUP BY doc_norm
HAVING COUNT(*) > 1
ORDER BY filas DESC, doc_norm;

-- Mismo normalizado, distinto formato (un solo id por formato)
SELECT
  REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm,
  documento,
  COUNT(*) AS n
FROM contribuyente
WHERE deleted_at IS NULL
GROUP BY doc_norm, documento
HAVING doc_norm IN (
  SELECT doc_norm FROM (
    SELECT REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm
    FROM contribuyente
    WHERE deleted_at IS NULL
    GROUP BY doc_norm
    HAVING COUNT(*) > 1
  ) d
)
ORDER BY doc_norm, documento;

-- Nombres / razones contradictorios en el mismo normalizado
SELECT
  REPLACE(REPLACE(REPLACE(c.documento, '.', ''), '-', ''), ' ', '') AS doc_norm,
  c.id,
  c.documento,
  c.apellido,
  c.nombre,
  c.razon_social
FROM contribuyente c
WHERE c.deleted_at IS NULL
  AND REPLACE(REPLACE(REPLACE(c.documento, '.', ''), '-', ''), ' ', '') IN (
    SELECT doc_norm FROM (
      SELECT REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '') AS doc_norm
      FROM contribuyente
      WHERE deleted_at IS NULL
      GROUP BY doc_norm
      HAVING COUNT(*) > 1
    ) d
  )
ORDER BY doc_norm, c.id;

-- Establecimientos y actuaciones por cada id de un normalizado (reemplazar :norm)
SELECT
  c.id AS contribuyente_id,
  c.documento,
  eo.id AS establecimiento_operativo_id,
  d.id AS domicilio_id,
  d.calle,
  d.numero,
  (SELECT COUNT(*) FROM actuaciones a WHERE a.domicilio_id = d.id) AS actuaciones
FROM contribuyente c
JOIN domicilio d ON d.contribuyente_id = c.id AND d.deleted_at IS NULL
LEFT JOIN establecimiento_operativo eo ON eo.domicilio_id = d.id
WHERE c.deleted_at IS NULL
  AND REPLACE(REPLACE(REPLACE(c.documento, '.', ''), '-', ''), ' ', '') = :norm
ORDER BY c.id, eo.id;
```

Interpretación: un resultado en la primera consulta **no** autoriza a fusionar. Puede ser tipeo, dos cargas concurrentes o datos viejos.

---

## 5. Propuesta técnica mínima

Objetivo: seguir reutilizando a la persona y resolviendo fichas como hoy, **sin** presentar el lock de CUIT.1 como candado de todo el sistema.

### Opciones

| Opción | Protección real | Cambio en canales | Migración / históricos | Reversión |
|--------|-----------------|-------------------|------------------------|-----------|
| **0. Nada** | Solo A2 | Ninguno | — | — |
| **1. Unique crudo en `documento`** | Impide dos literales iguales; **no** une `33.445566` y `33445566` | Cargar/Completar pasarían a IntegrityError | Falla si ya hay literales repetidos | Drop index |
| **2. Columna generada normalizada + UNIQUE** | Impide dos activos con el mismo normalizado (también soft-delete ocuparía el CUIT: MySQL no tiene unique parcial cómodo) | Los INSERT de `resolve_contribuyente` chocan el unique | **Exige** revisar duplicados antes; si hay, la migración falla | Drop columna/índice |
| **3. Lookup normalizado + lock/reserva en `resolve_contribuyente`** (recomendada como mínimo) | Reutiliza la fila existente aunque el formato cambie; al crear, `GET_LOCK` + `contribuyente_documento_unico` (el mismo que A2) | **Sí hay que tocar el helper** que ya usan Cargar/Completar/PATCH/PUT. Las pantallas no cambian. Si hay **varios** ids para el normalizado: no crear otro; error de revisión (como `DOCUMENTO_AMBIGUO`) | Backfill opcional de la reserva; no fusionar | Volver el helper al `==` literal; la tabla de reserva puede quedar |
| **4. Solo ampliar la reserva sin cambiar el lookup** | Carreras del **mismo** string; **sigue** el duplicado por formato | Hay que llamar la reserva desde el helper igual | Idem | Idem |

**Recomendación: opción 3**, en un ticket posterior. Es el menor cambio que cubre los canales que **sí escriben**. No alcanza con dejar el lock solo en Establecimientos.

Hace falta tocar Cargar/Completar **por dentro** (`resolve_contribuyente`) precisamente para **no** cambiar su experiencia: el QA (reutilizar, misma/otra ficha, historial por CUIT) se mantiene y se extiende a formatos equivalentes que hoy generan otra persona.

### Nombre / razón al encontrar documento

Hoy, si el payload trae las claves, **pisa** nombre/apellido/razón (incluso con `None`). Completar manda las cuatro claves. Un cierre con el CUIT bien y el nombre mal **cambia el titular compartido** de todos los locales. La unicidad no debe agravar eso: al unificar lookup, conviene **no ampliar** el overwrite (opción: actualizar solo campos no vacíos, o no actualizar en Cargar). Eso es decisión funcional aparte.

### Despliegue seguro (futuro)

1. Consultas de §4 en copia.  
2. Si hay duplicados: listar, no fusionar en automático.  
3. Helper con lookup normalizado + lock; si `COUNT>1`, 409 de revisión.  
4. Tests de §6.  
5. Unique generado **solo** si la copia quedó sin pares activos, o no ponerlo y vivir de lock+reserva.  
6. Rollback: revertir el helper; no hace falta borrar la tabla de reserva.

---

## 6. Pruebas propuestas (ticket siguiente)

1. Documento existente + mismo domicilio → misma ficha canónica (`MIN(eo.id)`).  
2. Documento existente + otra calle/número → otro EO, mismo `contribuyente_id`.  
3. Historial por CUIT con visitas de ambos locales.  
4. Formatos que **sí entran** (`33445566` / `33.445566`; dígitos vs puntos ≤11): un solo contribuyente si se implementa 3; hoy son dos (regresión consciente). Los tres strings del ticket: UI Completar/CRUD rechazan 2 y 3; BD rechaza 2 y 3 por longitud.  
5. Dos hilos: Cargar↔Cargar, Completar↔Completar, Cargar↔Corregir A2, Completar↔A2.  
6. Reuso: payload sin claves de nombre no borra apellido; payload Completar con claves vacías sí puede limpiar (comportamiento actual a fijar).  
7. Detección SQL de duplicados históricos **sin** merge.  
8. Cancelar / error de commit: sin fila huérfana ni reserva a medias.  
9. Relevador 403 en corrección; rutas/actas/coordenadas intactas; vinculación sigue siendo una ficha.

---

## 7. Qué no se hizo

- No se cambió Cargar actuación ni Completar trabajo.  
- No se crearon unique ni se migró nada en este ticket.  
- No se desactivó CUIT.1.  
- No se fusionó nadie.  
- No se consultó producción.

**Conclusión:** el flujo habitual del QA es el camino literal feliz y funciona. El hueco es lookup literal + ausencia de unique + lock solo en corrección. Cerrarlo implica un helper compartido, no un rediseño de pantallas.
