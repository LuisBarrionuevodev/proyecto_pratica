# V1.1-ESTABLECIMIENTOS-CONTRIBUYENTE.2 — Corrección global vs de ficha

**Fecha:** 2026-11-15  
**Alcance:** separar visualmente las dos acciones de la ficha; reutilizar el canal de vinculación existente; diagnosticar el alta de un contribuyente aún no registrado **sin implementarla**.

No cambia Cargar actuación, Completar trabajo, reinspecciones, titularidad ni protecciones de documento.

---

## 1. Dos acciones en la ficha

| Acción | Alcance | Canal |
|---|---|---|
| **Corregir datos del contribuyente** | La misma persona. Nombre, apellido, razón social o CUIT/DNI mal cargado. Preview lista **todos** los establecimientos asociados. | Corrección in-place existente (`CorreccionEstablecimientoDialog`). Sin cambios de lógica. |
| **Corregir contribuyente de este establecimiento** | Se registró a la persona equivocada **en esta ficha**. Solo esta ficha y sus vínculos comprobados. | Canal de vinculación existente (`VinculacionEstablecimientoDialog`). |

Texto de la segunda acción:

> Usá esta opción si se registró a la persona equivocada en este establecimiento.

Si en **Corregir datos** el CUIT propuesto ya pertenece a otra persona única, el flujo sigue ofreciendo asociar solo esta ficha (`DOCUMENTO_AJENO` + `ofrece_vinculacion`). No autoaplica.

---

## 2. Contribuyente correcto ya registrado

Se reutiliza el canal de asociación controlada:

1. Buscar por CUIT/DNI (lookup **normalizado**).
2. Mostrar el contribuyente encontrado.
3. Preview de establecimiento, actuaciones, notificaciones, comprobaciones, oficios, iniciadores y rutas.
4. Confirmación explícita (`Sí, asociar` + fingerprint).
5. Apply reasigna `domicilio.contribuyente_id` de **esta** identidad lógica. Auditoría `tipo=VINCULACION`.

No edita datos personales del destino. Los demás locales de origen y destino no se mueven.

Si ya existe ficha lógica (mismo contribuyente + mismo domicilio), se agrupa (`MIN(eo.id)`). No se borran ni fusionan filas físicas.

---

## 3. Contribuyente correcto aún no registrado — diagnóstico (sin implementar)

**Decisión de este ticket:** no implementar el alta. El canal responde `SIN_DESTINO` y no escribe.

### Cómo se informaría el alta

Habría que pedir CUIT/DNI **y** nombre/apellido o razón social, con confirmación explícita del tipo «vas a crear a esta persona y vincular **solo esta ficha**». Hoy el diálogo de vinculación solo pide documento.

### Cómo no crear si se cancela o falla

Preview es solo lectura. El apply actual ya corre en una transacción: rollback total si falla. Un alta seguro tendría que insertar el contribuyente **en la misma transacción** que la reasignación de domicilios, con `GET_LOCK('corr_doc:{norm}')` y `contribuyente_documento_unico` (UNICIDAD.1). Cancelar = no llamar apply.

### Cómo preservar los demás locales del anterior

Igual que la vinculación actual: solo `domicilio_ids_ficha`. Prohibido UPDATE in-place del contribuyente anterior (eso es Corregir datos).

### Cómo quedarían ficha, actuaciones, historial y trámites

- Ficha: `domicilio.contribuyente_id` al id nuevo.
- Actuaciones: siguen el domicilio; no se reescriben snapshots ni PDF.
- Historial por CUIT: pasa al documento nuevo; el anterior deja de listar esas visitas de la ficha.
- Notificaciones, comprobaciones, oficios, rutas: se conservan (cuelgan del domicilio).

### Coincidencia o ambigüedad

- Match único → no es alta: es vinculación (punto 2).
- Varios ids activos → `DOCUMENTO_AMBIGUO`, sin cambios.
- Documento del contribuyente actual → `MISMO_CONTRIBUYENTE`, sin cambios.

### Por qué no entra en este ticket

1. Crear desde la ficha se parece a un **cambio de dueño**, que el ticket prohíbe como función automática.
2. No se puede distinguir con seguridad un CUIT inexistente (typo) de «la persona correcta todavía no está». Un alta haría un contribuyente fantasma y movería la ficha.
3. Reusar `resolve_contribuyente` pisaría nombre/apellido/razón y no es atómico con la reasignación de ficha.
4. El workaround seguro ya existe: dar de alta a la persona por Cargar/Completar (con lock UNICIDAD.1) y después usar **Corregir contribuyente de este establecimiento**.

**Ticket posterior (propuesta):** `V1.1-ESTABLECIMIENTOS-CONTRIBUYENTE.3` — alta atómica + vincular ficha, con datos de identidad, `GET_LOCK`, reserva de documento, sin `resolve_contribuyente`, rollback si falla la vinculación, y confirmación que no es cambio de titularidad.

---

## 4. QA de inspección nueva (Cargar / Completar sin cambios)

Denuncia y relevamiento **pendientes no heredan** el titular del domicilio histórico (fork PR12). Al completar la visita con **otro** titular:

| Origen | Actuación anterior | Actuación nueva |
|---|---|---|
| Denuncia, mismo domicilio, titular B | Conserva contribuyente A y su ficha | Domicilio/EO propios de B |
| Relevamiento, mismo domicilio, titular B | Conserva contribuyente A y su ficha | Domicilio/EO propios de B |

Pruebas: `test_cambio_titular_denuncia_t0_t1_t2` (PR12), `test_denuncia_t0_t1_t2_otro_titular_conserva_ficha_anterior` y `test_relevamiento_t0_t1_t2_otro_titular` (este ticket).

**No se asume lo mismo para reinspección por notificación u oficio.** Esos iniciadores cuelgan del domicilio/titular de la actuación origen; no se tocan en este ticket.

Diferencia documentada: denuncia/relevamiento arrancan **sin** titular; la visita captura el de ese día. Una reinspección arranca **con** el domicilio de la actuación que la originó.

---

## 5. QA de las acciones

- Las dos acciones explican alcance distinto (todos los locales vs solo esta ficha).
- Corregir datos conserva preview, confirmación, auditoría, fingerprint y bloqueo de documento ajeno/ambiguo.
- Asociar un contribuyente existente cambia solo la ficha seleccionada.
- Otros locales de ambos contribuyentes intactos (tests VINCULACION.1).
- Mismo documento y domicilio: historial lógico sin actuaciones duplicadas.
- Otro domicilio: fichas separadas; historial por CUIT correcto.
- Notificaciones, comprobaciones, oficios, rutas y estados se conservan.
- Cancelación, ambigüedad o `SIN_DESTINO`: sin cambios parciales ni alta.
- Permisos admin/usuario, confirmación y validación de backend vigentes.

---

## Qué no se hizo

- No hay alta de contribuyente desde la ficha.
- No hay modelo de períodos de titularidad.
- No se fusionan ni borran contribuyentes o fichas.
- No se cambian Cargar actuación, Completar trabajo ni reinspecciones.
- No se alteran coordenadas, estados, actas ni documentos históricos.
- No se quitan UNICIDAD.1 ni `limpiar_contribuyente`.
