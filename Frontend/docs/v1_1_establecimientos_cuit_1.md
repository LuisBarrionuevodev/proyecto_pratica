# V1.1-ESTABLECIMIENTOS-CUIT.1 — Corrección segura de CUIT/DNI

**Fecha:** 2026-11-15  
**Alcance:** permite corregir el documento de la **misma persona** cuando el CUIT/DNI correcto no pertenece a otro contribuyente activo. El hotfix `CAMBIO_DOCUMENTO` queda reemplazado **solo** por este contrato.

No implementa cambio real de titularidad ni períodos.

---

## Contrato

### A2 — documento inexistente

1. Preview normaliza el documento y comprueba que no hay otro id activo.
2. Respuesta con fingerprint, datos anteriores/propuestos y **todos** los establecimientos asociados (domicilio visible + actuaciones por FK de domicilio).
3. Apply exige `confirmado` + fingerprint. Recalcula alcance; si cambió, `PREVIEW_STALE`.
4. UPDATE de la **misma** fila `contribuyente`. No crea ni reasigna domicilios.
5. Auditoría atómica (`tipo=CONTRIBUYENTE`) con valores anteriores/nuevos y locales alcanzados.

### A3 — documento de otro contribuyente único

Sigue el canal de vinculación: asocia **solo esta ficha**. No edita datos personales del destino. Los demás locales del origen no se mueven.

### Ambiguo

Varios ids activos con el mismo normalizado → `DOCUMENTO_AMBIGUO`, sin cambios.

---

## Concurrencia

`contribuyente.documento` **no** tiene unique (ni sobre el valor crudo ni sobre el normalizado). Pueden existir duplicados históricos; no se backfillea ni se agrega unique sobre `contribuyente` para no fallar la migración.

Garantía de este canal:

- `GET_LOCK('corr_doc:{norm}')` serializa applies A2 del mismo documento.
- Tabla `contribuyente_documento_unico` (PK = documento normalizado). El segundo apply concurrente recibe 409.

**Limitación:** Cargar actuación / Completar trabajo no usan esta reserva. Un alta paralela por esos flujos todavía podría crear otro contribuyente con el mismo normalizado. Queda deuda; no se tocan esos canales en este ticket.

---

## QA manual

1. Corregir CUIT mal cargado a uno libre, con dos locales: confirmar lista y que ambos quedan con el nuevo documento.
2. Cambiar nombre + CUIT a la vez: preview y ficha muestran ambos cambios.
3. Mismo número con puntos: se guarda el formato nuevo.
4. Cancelar / sin cambios: nada persiste.
5. CUIT de otra persona: modal “ya está registrado”; asociar solo este local; destino no cambia de nombre.
6. Dos personas con el mismo documento: bloqueo, un mensaje.
7. Volver desde la confirmación conserva lo tipeado.
8. Relevador no puede guardar.
9. Escritorio y celular: las dos consecuencias (corregir todos / asociar este) se distinguen. No hay acción de “cambiar titularidad”.
