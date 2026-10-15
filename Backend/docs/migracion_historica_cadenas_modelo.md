# Cadenas históricas — modelo operativo Digitaliza (V1.1-MIG-ACTAS.1C)

Documento de auditoría para importación histórica. No introduce tablas nuevas de vínculos genéricos: reutiliza el modelo operativo existente.

## Principio

No existe `parent_actuacion_id` en `actuaciones`. La trazabilidad se expresa con:

| Mecanismo | Uso en histórico |
|-----------|------------------|
| `actuaciones.notificacion_id` | Misma notificación en visita raíz y en `REINSPECCION` |
| `actuaciones.comprobacion_id` | Comprobación de la visita o comprobación previa resuelta |
| `notificacion` / `comprobacion` | Actas por `(numero_acta, anio)` — clave de `resolver_previas` |
| `inspeccion`, `clausura`, `decomiso` | 1:1 con la actuación de la visita |
| `expediente` | `comprobacion_id`; envío (`oficio_id` NULL) o respuesta de oficio |
| `oficio` | Siempre `comprobacion_id` |
| `actuaciones.ec5_uuid` | Identidad EpiCollect en migración |

**Importación histórica:** no crea `ruta_trabajo`, `ruta_item` ni `iniciador_ruta` operativos. Los iniciadores existen solo en el flujo de rutas en producción; aquí el vínculo es documental (`previas` + FKs).

## Fase 1 — Raíz (inspección / denuncia)

- `tipo` típico: `INSPECCION` (u otro tipo raíz EpiCollect, no reinspección).
- Misma visita puede tener: inspección + notificación + comprobación + clausura/decomiso en la **misma** `actuaciones`.
- Si hay notificación y comprobación juntas: se importan ambas; **no** se programa reinspección por notificación.

Servicios de referencia: `attach_inspeccion`, `attach_notificacion`, `attach_comprobacion`, `attach_clausura`, `attach_decomiso` (`app/domains/actuaciones/attach/`).

## Fase 2 — Reinspección por notificación

**Operativo (rutas):** `IniciadorRuta` con `tipo_iniciador=REINSPECCION_NOTIFICACION`, `notificacion_id`, `actuacion_id` = inspección base; hijo = `RutaItem.actuacion_id` con `tipo=REINSPECCION`.

**Histórico:** equivalente documental:

1. Actuación hija `tipo=REINSPECCION`.
2. `resolver_previas` con `acta_notificacion_previa_num` → `act.notificacion_id` apunta a la notificación ya importada en Fase 1.
3. Validación: acta de notificación previa única, fecha reinspección > fecha notificación, identidad (DNI o domicilio+titular).

Referencia: `previas_service.resolver_previas`, `notificacion_iniciador_service` (solo lectura conceptual).

## Fase 3 — Oficio y derivadas

Cadena administrativa obligatoria:

```text
Comprobación (Fase 1)
  → Expediente ENVIO_ACTA (sin oficio_id)
  → Oficio (misma comprobación)
  → Actuación VERIFICAR E INFORMAR / RATIFICACION DE CLAUSURA / RATIFICACION DE DECOMISO
```

**Histórico:**

1. Comprobación padre ya persistida (Fase 1 u otra raíz).
2. Expediente y oficio identificables (triplete EpiCollect `expediente|año|oficio` o número de acta de comprobación previa).
3. Hija: `resolver_previas` con `comprobacion_previa_num` + `tipo` según EpiCollect.
4. Ratificación clausura: la actuación que portó la comprobación padre debe tener `clausura`.
5. Ratificación decomiso: idem con `decomiso`.

Referencia: `oficio_completion_service`, `attach_oficio`, `attach_expediente`, `completar_trabajo_tipo_iniciador`.

## Conciliación EpiCollect (read-only previo)

`epicollect_cadenas_historicas.analizar_cadena_reinspeccion` indexa actas de notificación/comprobación en el CSV y valida vínculos antes de escribir. El importador 1C reutiliza esa lógica y añade comprobación contra **base destino** (`SELECT` de `notificacion` / `comprobacion` / `oficio` ya importados).

## Idempotencia

`migracion_historica_registro` por `(source_name, source_sha256, source_record_uuid)`. Segunda ejecución: `SKIPPED_IDEMPOTENT` sin duplicar OT ni actas.

## Registros piloto previos

Los lotes ya aplicados en `digitaliza_migracion` no se reescriben en 1C. El CLI puede emitir `reporte_registros_piloto_existentes.json` clasificando raíz vs derivado según `tipo` y FKs actuales.
