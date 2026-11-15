# HOTFIX-ESTABLECIMIENTOS-TITULAR.1 — causa, auditoría y recuperabilidad

**Fecha:** 2026-11-15  
**Alcance:** diagnóstico de solo lectura + protección preventiva. **No restaura datos de producción.**

---

## Causa confirmada (entorno de prueba / código)

El canal **Corregir contribuyente** actualiza **in-place** la misma fila de `contribuyente`:

```text
aplicar_correccion_establecimiento
  → contrib.documento / apellido / nombre / razon_social = propuesto
```

Varios `domicilio` (y por tanto varios establecimientos) apuntan al mismo `contribuyente_id`. Un UPDATE de esa fila se refleja en **todos** los locales vinculados. No se borra el registro anterior: se **sobrescribe**.

`validar_documento_propuesto` (antes de este hotfix) solo rechazaba si el documento normalizado ya pertenecía a **otro** id (`DOCUMENTO_AJENO`). Un CUIT nuevo, inexistente, se aceptaba y pisaba la identidad compartida.

La asociación (`/vinculaciones`) no entra en este fallo: reasigna `domicilio.contribuyente_id` de **esta** ficha y no edita datos personales del destino.

---

## Qué guarda la auditoría

Tabla `correccion_establecimiento_audit`:

| Campo | Uso para reconstruir |
|---|---|
| `tipo` | `CONTRIBUYENTE` / `AMBOS` / `VINCULACION` / … |
| `valores_anteriores` | JSON con `contribuyente.documento`, nombre, apellido, razón |
| `valores_nuevos` | JSON posterior |
| `alcance.establecimiento_ids_contribuyente` | EO que el preview consideró del mismo titular |
| `contribuyente_id` | Fila tocada |
| `establecimiento_operativo_id` | Ficha desde la que se operó |
| `created_by_user_id`, `created_at` | Quién y cuándo |

Limitación: un cambio de documento **en bruto** (p. ej. agregar un punto) también queda en auditoría. No todos los cambios de documento fueron errores de titularidad. Hace falta revisión humana caso por caso.

Otra limitación: si hubo correcciones posteriores sobre la misma fila, restaurar un snapshot viejo puede pisar un arreglo legítimo de nombre.

---

## Consultas de solo lectura (MySQL)

No ejecutar `UPDATE`/`DELETE`. Preferir réplica o sandbox.

### Correcciones donde el documento en JSON cambió

```sql
SELECT
  a.id AS audit_id,
  a.establecimiento_operativo_id,
  a.contribuyente_id,
  a.tipo,
  a.created_by_user_id,
  a.created_at,
  JSON_UNQUOTE(JSON_EXTRACT(a.valores_anteriores, '$.contribuyente.documento')) AS doc_antes,
  JSON_UNQUOTE(JSON_EXTRACT(a.valores_nuevos, '$.contribuyente.documento')) AS doc_despues,
  JSON_UNQUOTE(JSON_EXTRACT(a.valores_anteriores, '$.contribuyente.apellido')) AS apellido_antes,
  JSON_UNQUOTE(JSON_EXTRACT(a.valores_nuevos, '$.contribuyente.apellido')) AS apellido_despues,
  JSON_EXTRACT(a.alcance, '$.establecimiento_ids_contribuyente') AS eos_alcance
FROM correccion_establecimiento_audit a
WHERE a.tipo IN ('CONTRIBUYENTE', 'AMBOS')
  AND JSON_EXTRACT(a.valores_anteriores, '$.contribuyente.documento') IS NOT NULL
  AND JSON_UNQUOTE(JSON_EXTRACT(a.valores_anteriores, '$.contribuyente.documento'))
      <> JSON_UNQUOTE(JSON_EXTRACT(a.valores_nuevos, '$.contribuyente.documento'))
ORDER BY a.created_at DESC;
```

La comparación es **literal** (no normaliza puntos/guiones). Un cambio solo de formato aparece acá y **no** debe tratarse como error sin revisar.

### Establecimientos actuales de un contribuyente

```sql
SELECT
  eo.id AS establecimiento_operativo_id,
  d.id AS domicilio_id,
  d.calle,
  d.numero,
  c.id AS contribuyente_id,
  c.documento,
  c.apellido,
  c.nombre,
  c.razon_social
FROM establecimiento_operativo eo
JOIN domicilio d ON d.id = eo.domicilio_id
JOIN contribuyente c ON c.id = d.contribuyente_id
WHERE c.id = :contribuyente_id
  AND d.deleted_at IS NULL;
```

### Quién quedó con el documento “viejo” (si alguien más lo usa ahora)

```sql
SELECT id, documento, apellido, nombre, razon_social, deleted_at
FROM contribuyente
WHERE REPLACE(REPLACE(REPLACE(documento, '.', ''), '-', ''), ' ', '')
    = REPLACE(REPLACE(REPLACE(:documento_antes, '.', ''), '-', ''), ' ', '')
  AND deleted_at IS NULL;
```

---

## Plan de recuperación individual (no aplicar sin autorización)

Si un `audit_id` se confirma como error:

1. Congelar: no revertir en lote.
2. Comparar `valores_anteriores` con el estado actual de `contribuyente`.
3. Listar EO actuales de ese `contribuyente_id` (consulta de arriba).
4. Si el documento “nuevo” debería ser otra persona: **no** reescribir la fila compartida a ciegas. Evaluar con negocio si hay que:
   - restaurar documento/nombre de la fila original **solo si** todos los locales de esa fila deben volver al titular anterior; o
   - dejar la asociación posterior (`tipo = VINCULACION`) intacta y tratar cada ficha por separado.
5. Presentar el caso (ids, docs antes/después, EO afectados, usuario, fecha) y esperar autorización.
6. No borrar ni fusionar contribuyentes. No tocar PDF, snapshots, rutas ni actas.

En este ticket **no se encontró ni se revirtió ningún caso de producción**: las consultas no se ejecutaron contra prod.

---

## Protección aplicada

Preview y apply del canal de corrección:

- Mismo documento **normalizado** → se permite (formato y/o nombre/razón social).
- Documento de otro contribuyente único → `DOCUMENTO_AJENO` + `ofrece_vinculacion` (asociación explícita; no overwrite).
- Documento nuevo o no identificable con seguridad → `CAMBIO_DOCUMENTO` (409 en apply). Sin auditoría de éxito.
