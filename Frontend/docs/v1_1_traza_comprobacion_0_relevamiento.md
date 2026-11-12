# V1.1-TRAZA-COMPROBACION.0 — Relevamiento de decomisos, clausuras y ratificaciones

**Fecha:** 2026-11-11  
**Alcance:** diagnóstico de lectura. Sin cambios de código, datos, migraciones ni flujo operativo.  
**Fuera de foco (explícito):** Completar trabajo; Cargar/Editar actuaciones; estados, rutas, oficios, expedientes, contraproducencias y reapertura; creación/edición de actas, kilos, clausuras o decomisos; clasificación errónea de actuaciones manuales en «Otras»; edición maestra de contribuyentes/establecimientos.

Este documento responde **qué vínculos ya existen** entre comprobación, decomiso, clausura y las visitas de oficio (ratificación / verificar e informar), **qué consumidores de lectura los muestran hoy**, y **qué puede proyectarse en Recorrido, detalles, exportaciones e indicadores** sin tocar el circuito operativo.

Tickets posteriores (no implementar aquí):

| Ticket | Objetivo |
|---|---|
| V1.1-TRAZA-COMPROBACION.1 | Proyección read-only de la trazabilidad existente |
| V1.1-TRAZA-COMPROBACION.2 | Lectura en grillas, detalles y exportaciones |
| V1.1-INDICADORES-RATIFICACION.1 | Card y cálculo de kilos ratificados con fecha de ratificación |

---

## 1. Respuestas cortas (contrato del ticket)

### 1.1 Desde una comprobación, ¿cómo se obtiene su acta de decomiso, kilos y acta de clausura?

No hay FK `decomiso.comprobacion_id` ni `clausura.comprobacion_id`. Las actas cuelgan **1:1 de la actuación**, no de la comprobación.

Camino canónico:

```
comprobacion.id
  → actuaciones.comprobacion_id  (actuación ancla / Recorrido)
  → decomiso.actuacion_id = actuaciones.id     → numero_acta, cantidad (kg)
  → clausura.actuacion_id = actuaciones.id     → numero_acta
```

Campos concretos:

| Dato | Tabla.columna | Presenter actual |
|---|---|---|
| Acta de decomiso | `decomiso.numero_acta` (+ `anio`) | `actuacion_to_grid_row` → `acta_decomiso_num` |
| Kilos | `decomiso.cantidad` (`Numeric(12,3)`) | `decomiso_kilos_total` |
| Acta de clausura | `clausura.numero_acta` (+ `anio`) | `acta_clausura_num` |

`decomiso.actuacion_id` y `clausura.actuacion_id` son **unique**: una actuación tiene como máximo un decomiso y una clausura. La comprobación y esas actas conviven en la **misma visita ancla** cuando se labraron juntas.

### 1.2 Desde una reinspección por oficio, ¿cómo se llega a la comprobación de origen?

```
RutaItem.iniciador_ruta_id
  → iniciador_ruta
       .oficio_id        → oficio.comprobacion_id → comprobacion
       .comprobacion_id  (copiado al materializar desde la ancla)
       .actuacion_id     = actuación ANCLA (la del acta de comprobación)
  → RutaItem.actuacion_id (si FINALIZADO + REALIZADO) = actuación de VISITA
       distinta de la ancla
```

Materialización (`get_or_create_iniciador_from_oficio`): el iniciador nace como `REINSPECCION_OFICIO` con `oficio_id`, `comprobacion_id = actuacion.comprobacion_id` y `actuacion_id` = ancla. `fecha_origen` es `oficio.fecha_oficio` o fecha del expediente de respuesta: **no es la fecha de ratificación**.

La visita de cierre **no sustituye** a la ancla. Recorrido la resuelve con `_actuacion_visita_reinspeccion_desde_ruta_item` / `_actuacion_visita_desde_iniciador`: último `RutaItem` FINALIZADO + REALIZADO cuyo `actuacion_id` ≠ ancla.

### 1.3 ¿Cómo se identifica el tipo final?

Tres capas (no confundir):

| Capa | Dónde | Valores |
|---|---|---|
| Circuito | `iniciador_ruta.tipo_iniciador` al planificar | Siempre `REINSPECCION_OFICIO` al crear |
| Subtipo promovido | mismo campo, tras Completar trabajo | `RATIFICACION_DECOMISO_OFICIO`, `RATIFICACION_CLAUSURA_OFICIO`, `VERIFICAR_INFORMAR_OFICIO` |
| Acta labrada | `actuaciones.tipo` de la **visita** | `RATIFICACION DE DECOMISO`, `RATIFICACION DE CLAUSURA`, `VERIFICAR E INFORMAR` |

Regla de lectura ya usada en Recorrido (`_tipo_visita_resultado_final`):

1. Preferir `actuaciones.tipo` de la visita si está en el catálogo `{RATIFICACION DE CLAUSURA, RATIFICACION DE DECOMISO, VERIFICAR E INFORMAR}`.
2. Si no, mapear el `tipo_iniciador` promovido con `tipo_actuacion_para_iniciador`.
3. `REINSPECCION` genérico **no** es tipo final: la UI muestra «Pendiente» / `None`.

`REINSPECCION_OFICIO` describe el circuito, no el resultado. Tras cierre realizado, `promover_iniciador_reinspeccion_oficio_segun_tipo` alinea el iniciador al subtipo. Contraproducencia reencolable **restaura** el genérico (`reset_iniciador_reinspeccion_oficio_generico`): el tipo concreto queda en la actuación de visita histórica.

### 1.4 Verificar e informar: con inspección, sin inspección, origen sin decomiso/clausura

Campo de la **visita**: `actuaciones.realizo_nueva_inspeccion` (`Boolean`, nullable). Solo aplica a Verificar e informar. Ratificaciones lo dejan `NULL`.

| Caso | Qué permite Completar trabajo (hoy, no tocar) | Qué traer en trazabilidad de origen |
|---|---|---|
| `realizo_nueva_inspeccion = True` | Puede labrar actas nuevas en la **visita** (inspección y, si se cargan, comprobación/decomiso/clausura de esa segunda visita) | Decomiso/kilos y clausura de la **ancla**, si existen. Las actas de la visita son otro hecho. |
| `realizo_nueva_inspeccion = False` | Prohibido enviar actas/kilos (`_validar_payload_verificar_informar`) | Igual: origen en la ancla. La visita no tiene decomiso/clausura propios. |
| Origen sin decomiso ni clausura | Circuito válido | Campos vacíos. No inventar ni buscar en la visita. |
| `realizo_nueva_inspeccion` NULL (legado) | Ambiguo | Mostrar origen si hay; no inferir tipo de actas de visita. |

`resultado_cumplimiento_oficio` **no** aplica a Verificar e informar.

### 1.5 ¿Qué fecha existente representa la fecha de ratificación?

No hay columna `fecha_ratificacion`. Candidatas existentes:

| Campo | Qué es realmente | ¿Usar para indicadores de kilos ratificados? |
|---|---|---|
| `actuaciones.fecha` de la **visita** (`RutaItem.actuacion_id`) | Fecha labrada de la ratificación | **Sí para Recorrido / detalle** (`ejecucion_reinspeccion.fecha_actuacion`, `fecha_conclusion`) |
| `ruta_trabajo.fecha` de la ruta PUBLICADA del ítem REALIZADO | Día operativo del dashboard | **Sí para el KPI** (misma base que `ratificaciones_decomiso_realizadas`) |
| `ruta_item.ejecutado_at` | Auditoría de cierre en sistema | No. Los indicadores actuales lo excluyen a propósito. |
| `iniciador_ruta.fecha_origen` | Fecha del oficio / expediente de respuesta | No. Es disparador, no ratificación. |
| `decomiso.created_at` / fecha de la ancla | Alta del decomiso original | No. Es la decomisación, no la ratificación. |
| `comprobacion` mes/año o `actuaciones.fecha` ancla | Visita de origen | No. |

Recomendación: **mostrar** `Actuaciones.fecha` de la visita; **imputar el KPI** con `RutaTrabajo.fecha` para alinearlo al conteo ejecutivo ya existente. Documentar la posible diferencia de 1 día si OT y cierre no coinciden.

---

## 2. Inventario

### 2.1 Modelos y campos

| Entidad | Archivo | Campos relevantes |
|---|---|---|
| `Comprobacion` | `Backend/app/models/comprobacion.py` | `id`, `numero_acta`, `anio`, `mes`. Sin decomiso/clausura. |
| `Actuaciones` | `Backend/app/models/actuaciones.py` | `fecha`, `tipo`, `comprobacion_id`, `resultado_cumplimiento_oficio`, `realizo_nueva_inspeccion`. Relaciones `decomiso` / `clausura` / `inspeccion` (`uselist=False`). Unique `uq_act_anio_tipo_comprobacion` (`anio`, `tipo`, `comprobacion_id`): **permite** varias actuaciones con la misma comprobación si cambia `tipo` o `anio` (ancla vs visita). |
| `Decomiso` | `Backend/app/models/decomiso.py` | `numero_acta`, `anio`, `mes`, `actuacion_id` unique, `cantidad`. Unique `uq_ad_numero_anio`. |
| `Clausura` | `Backend/app/models/clausura.py` | `numero_acta`, `anio`, `mes`, `actuacion_id` unique. Unique `uq_ac_numero_anio`. |
| `Inspeccion` | `Backend/app/models/inspeccion.py` | `actuacion_id` unique. Solo relevante en VI con nueva inspección (visita). |
| `Oficio` | `Backend/app/models/oficio.py` | `comprobacion_id`, `numero_oficio`, `anio`, `fecha_oficio`, `causa`, `juzgado_id`. |
| `IniciadorRuta` | `Backend/app/models/iniciador_ruta.py` | `tipo_iniciador`, `estado_iniciador`, `fecha_origen`, `oficio_id`, `comprobacion_id`, `actuacion_id` (ancla). |
| `RutaItem` | `Backend/app/models/ruta_item.py` | `iniciador_ruta_id`, `actuacion_id` (visita al publicar/cerrar), `estado_ruta_item`, `estado_ejecucion`. |
| `RutaTrabajo` | `Backend/app/models/ruta_trabajo.py` | `fecha`, `estado_ruta`. Período de indicadores «realizadas». |

`IniciadorRuta.actuacion_id` **nunca** es la visita de cierre. La visita vive en `RutaItem.actuacion_id`.

### 2.2 Servicios y presenters de lectura

| Pieza | Archivo | Rol |
|---|---|---|
| Grilla canónica | `actuacion_presenters.py` → `actuacion_to_grid_row` | Expone `acta_decomiso_num`, `decomiso_kilos_total`, `acta_clausura_num` de **esa** actuación. |
| Recorrido fila | `comprobacion_actas_presenters.py` → `comprobacion_recorrido_resumen_row` | Parte de `actuacion_to_grid_row` (ancla) + `oficios_resumen`. Los kilos/actas de origen **viajan en el JSON** pero Recorrido UI no los usa. |
| Recorrido detalle | `comprobacion_recorrido_detalle` | `acta_comprobacion` sin decomiso/clausura. `referencia_actuacion` tampoco. `ejecucion_reinspeccion` = visita. |
| Snapshot visita | `_payload_ejecucion_reinspeccion` (presenter y `comprobacion_oficio_recorrido_service.py`) | Inspectores, fecha, OT, tipo, cumplimiento. **No incluye** `acta_decomiso_num` / kilos / `acta_clausura_num`. |
| Oficio por comprobación | `oficio_recorrido_campos_operativos` | Une iniciador + visita + `fecha_conclusion` = `act_visita.fecha`. |
| Tipo final | `_tipo_visita_resultado_final` + `tipo_actuacion_para_iniciador` | Ver §1.3. |
| Materialización | `oficio_iniciador_service.py` | Crea iniciador con FKs de origen. |
| Promoción de tipo | `completar_trabajo_tipo_iniciador.py` | Solo escritura; lectura debe tolerar genérico vs promovido. |
| Indicadores realizadas | `indicadores_operativos_queries.py` → `visitas_realizadas_por_tipo_iniciador` | Cuenta por `tipo_iniciador` + `RutaTrabajo.fecha`. |
| Kg actuales | `indicadores_ejecutivo_service.py` / `indicadores_resumen_service.py` | `SUM(decomiso.cantidad)` join `Decomiso.actuacion_id` ∈ actuaciones **realizadas en el período**. Son kilos **labrados en esa visita**, no ratificados. |

### 2.3 Endpoints

| Método | Ruta | Consumo |
|---|---|---|
| GET | `/api/actuaciones/comprobacion/recorrido` | Tabla Recorrido. Fila = ancla. |
| GET | `/api/actuaciones/comprobacion/recorrido/<id>` | Modal detalle Recorrido. |
| GET | `/api/actuaciones/` | Ver actuación / Gestión. `actuacion_to_grid_row` de **la fila abierta** (ancla o visita). |
| GET | `/api/actuaciones/<id>/gestion` | Modal Gestión. |
| GET | `/api/actuaciones/comprobacion/pendientes-reinspeccion-oficio` | Bandeja (ancla + iniciador). |
| GET | `/api/indicadores/ejecutivo` | KPIs: `ratificaciones_decomiso_realizadas`, `mercaderia_decomisada_kg`. |
| GET | `/api/indicadores/resumen` | `decomiso_kg` total + por mes (`Actuaciones.fecha` del dueño del decomiso). |
| GET | `/api/indicadores/riesgo` | `query_decomiso_kg_por_rubro` (misma semántica de kilos labrados). |

No existe endpoint de «kilos ratificados».

### 2.4 Frontend (solo lectura)

| Superficie | Archivo | Qué muestra hoy de decomiso/clausura |
|---|---|---|
| Recorrido tabla | `ActasComprobacionPage.tsx` | Chips de oficio / tipo visita / estado. **No** kilos ni actas de decomiso/clausura de origen. |
| Recorrido cabecera acta | `filasActaComprobacionRecorrido` | N.º comprobación, fecha, OT, domicilio, inspectores, motivos. **Sin** decomiso/clausura. |
| Recorrido oficio | `filasOficioRecorridoDocumental` | Intenta `ejec.acta_clausura_num` / `acta_decomiso_num` de la **visita**. El payload **no los envía**. Tampoco kilos. |
| Export Recorrido PDF/XLSX | `comprobacionExportTypes.ts` y builders | Oficio, expediente, tipo, conclusión, OT/fecha reinspección. **Sin** decomiso/clausura/kilos. |
| Tipo TS Recorrido | `IComprobacionRecorridoRow` | No declara `acta_decomiso_num` / `decomiso_kilos_total` / `acta_clausura_num` aunque el JSON de ancla los trae. |
| Ver actuación | `ActuacionDetalleDialog.tsx` | Acta decomiso, kilos, clausura de **la actuación abierta**. Si se abre la visita, no son los de origen. Si se abre la ancla, sí. |
| Indicadores UI | `DashboardEjecutivoSection.tsx`, `DashboardDecomiso.tsx` | `mercaderia_decomisada_kg` y serie mensual = kilos labrados. Conteo `ratificaciones_decomiso_realizadas` ya existe. |
| PDF indicadores | `dashboardPdfMappers.ts` | Misma card «Mercadería decomisada (kg)». No hay «kilos ratificados». |

---

## 3. Disponibilidad de datos por tipo final

Contrato pedido vs lo que los vínculos actuales permiten **sin escribir**:

| Tipo final | Dato pedido | ¿Existe en origen (ancla)? | ¿Lo proyecta Recorrido hoy? | Notas |
|---|---|---|---|---|
| Ratificación de decomiso | Acta de decomiso + kilos | Sí, si la ancla tiene fila `decomiso` | No (JSON ancla sí; UI/export/detalle no) | La visita **no** es la fuente. Un decomiso nuevo en la visita sería otra acta. |
| Ratificación de clausura | Acta de clausura | Sí, si la ancla tiene `clausura` | No (igual) | Idem. |
| Verificar e informar | Decomiso/kilos y clausura **si existen** | Opcional en ancla | No | Vacío es válido. Nueva inspección en visita no sustituye origen. |
| Reinspección genérica (aún no promovida) | — | Origen igual | Tipo final `None` | No imputar kilos ratificados. |

Identificación práctica del tipo final para joins:

```
tipo_iniciador IN (
  'RATIFICACION_DECOMISO_OFICIO',
  'RATIFICACION_CLAUSURA_OFICIO',
  'VERIFICAR_INFORMAR_OFICIO'
)
-- o actuaciones.tipo de la visita IN (
--   'RATIFICACION DE DECOMISO',
--   'RATIFICACION DE CLAUSURA',
--   'VERIFICAR E INFORMAR'
-- )
```

Si el iniciador sigue `REINSPECCION_OFICIO` pero la visita ya tiene `tipo` concreto, **prevalece la visita** (mismo criterio que Recorrido).

---

## 4. Trazados

### 4.1 Comprobación con decomiso (sin clausura)

```
[Visita origen / ancla]  actuaciones.id = A
  tipo                 ≈ INSPECCION / comprobación del día
  fecha                = F0
  comprobacion_id      = C
  decomiso             → numero_acta D, cantidad Kg
  clausura             = NULL

[Comprobacion C]  numero_acta …

[Oficio O]  comprobacion_id = C

[Iniciador I]  tipo_iniciador = REINSPECCION_OFICIO → (cierre) RATIFICACION_DECOMISO_OFICIO
  comprobacion_id = C
  oficio_id = O
  actuacion_id = A          ← ancla, no la visita

[RutaItem]  FINALIZADO + REALIZADO
  actuacion_id = V          ← visita V ≠ A
  iniciador_ruta_id = I

[Visita V]
  tipo = RATIFICACION DE DECOMISO
  fecha = Fr                ← fecha de ratificación (pantalla)
  decomiso/clausura propios = normalmente NULL
```

Lectura: Recorrido lista `A`. Detalle de oficio resuelve `V`. Origen kilos = `A.decomiso.cantidad`, no `V`.

### 4.2 Comprobación con clausura (sin decomiso)

Igual que 4.1, con `clausura` en `A` y `decomiso` NULL. Cierre típico: `RATIFICACION DE CLAUSURA` / `RATIFICACION_CLAUSURA_OFICIO`. Kilos ratificados = no aplica.

### 4.3 Comprobación con ambos

`A` tiene `decomiso` y `clausura`. Un **mismo** oficio/iniciador se promueve a **un** subtipo (decomiso **o** clausura **o** VI), no a los dos.

| Tipo final de esa visita | Qué mostrar de origen | KPI kilos ratificados |
|---|---|---|
| Ratificación de decomiso | Acta decomiso + kilos (y, si se desea en ficha, clausura como dato colateral de la ancla, no como «ratificada») | Sí, `A.decomiso.cantidad` |
| Ratificación de clausura | Acta clausura | No |
| Verificar e informar | Ambos si existen | No |

Varios oficios sobre la misma `C` pueden generar **varias** visitas (una ratifica decomiso, otra clausura, otra VI). Cada fila de oficio en Recorrido debe resolver su propio `tipo_iniciador` / visita.

---

## 5. Consumidores de lectura (estado actual)

### 5.1 Recorrido de comprobaciones

- Universo: actuaciones con comprobación (`list_comprobacion_recorrido`).
- Fila = ancla. `oficios_resumen[]` = un ítem por oficio, con `tipo_iniciador`, `visita_resumen_texto`, `ejecucion_reinspeccion`, `fecha_conclusion`.
- Origen decomiso/clausura: presentes en el objeto ancla vía `actuacion_to_grid_row`, **ocultos** en UI.
- Visita decomiso/clausura: UI los pide; API no los manda. Coherente con el contrato futuro: **no** deben usarse como origen.

### 5.2 Historial documental y detalles

- Detalle Recorrido: bloques origen / acta comprobación / expedientes / oficio / reinspección. Sin bloque «actas de origen decomiso/clausura».
- Ficha Gestión / seguimiento: no es fuente de kilos ratificados.
- Historial SQL de pendientes (`_apply_historial_documental_sql`) filtra documentales; no proyecta kilos.

### 5.3 Ver actuación

- `GET /actuaciones/` + `ActuacionDetalleDialog`.
- Muestra actas **de la actuación consultada**. Abrir la ancla = origen. Abrir la visita de ratificación = hueco (correcto: esas actas no se copian). TRAZA.2 puede añadir un recuadro «origen» en la visita **sin** editar.

### 5.4 Exportación PDF/XLSX de Recorrido

- `ComprobacionExportRow` / `RecorridoOficioExportDetalle`: oficio, expediente, tipo, conclusión, seguimiento, OT y fecha de reinspección.
- No hay columnas de acta decomiso, kilos ni clausura. TRAZA.2 las agrega como lectura.

### 5.5 Indicadores (endpoint + PDF)

| KPI actual | Semántica | Relación con este ticket |
|---|---|---|
| `ratificaciones_decomiso_realizadas` | Visitas REALIZADO con iniciador (híbrido) `RATIFICACION_DECOMISO_OFICIO`, período `RutaTrabajo.fecha` | Conteo ya existe. La card de kilos se apoya en el mismo universo. |
| `ratificaciones_clausura_realizadas` | Análogo clausura | Sin kilos. |
| `verificar_informar_realizadas` | Análogo VI | Sin kilos ratificados. |
| `mercaderia_decomisada_kg` / `decomiso_kg` | `SUM(decomiso.cantidad)` donde el **dueño** del decomiso es una actuación realizada **en el período** | Imputa kilos el **día de la decomisación** (visita que labró el acta), no el de ratificación. **No reutilizar** para «kilos ratificados». |
| PDF ejecutivo | Replica `mercaderia_decomisada_kg` | Card nueva aparte en INDICADORES-RATIFICACION.1. |

---

## 6. Limitaciones reales de los vínculos actuales

1. **Decomiso/clausura no cuelgan de `comprobacion`**. Hay que pasar por la actuación ancla. Si la ancla no tiene la fila, no hay origen recuperable.
2. **Varias actuaciones pueden compartir `comprobacion_id`** (unique solo `anio+tipo+comprobacion_id`). Recorrido elige la actuación con el acta de comprobación; otra actuación hermana con decomiso sería ambigua (ver SQL).
3. **La visita puede tener su propio decomiso** si Completar trabajo cargó acta/kilos en el cierre (permitido en ratificación y en VI con nueva inspección). Eso **no** es el decomiso original. Sumar kilos de la visita **doble-cuenta** o inventa un segundo decomiso.
4. **Un decomiso, varias ratificaciones.** Un oficio reencolado (contraproducencia) o varios oficios sobre la misma comprobación pueden producir más de un `RutaItem` REALIZADO `RATIFICACION_DECOMISO_OFICIO` apuntando al mismo `decomiso.id`. Contar kilos por visita duplica; hay que `DISTINCT decomiso.id` (o ancla `actuacion_id`).
5. **Iniciador genérico vs promovido.** Tras reset por contraproducencia, `tipo_iniciador` vuelve a `REINSPECCION_OFICIO`. El tipo final de visitas **cerradas** sigue en `actuaciones.tipo`. Un filtro solo por iniciador actual pierde histórico o mezcla pendiente.
6. **`_payload_ejecucion_reinspeccion` incompleto** respecto a la UI de Recorrido (actas de visita). Completarlo con actas de **visita** contradiría el contrato de origen; hay que proyectar un bloque `origen_ancla` aparte.
7. **Cargas históricas / `carga_solo_comprobacion`.** Ancla sin decomiso adjunto: no hay kilos. No se puede inferir desde texto de oficio.
8. **Tipo final «Ratificación de decomiso» sin fila `decomiso` en ancla.** Dato incompleto (oficio mal clasificado o acta nunca cargada). Mostrar vacío; no usar kilos de otra actuación.
9. **Dos fechas.** `Actuaciones.fecha` vs `RutaTrabajo.fecha`. El dashboard ya eligió la segunda para «realizadas».
10. **Verificar e informar con nueva inspección** puede labrar comprobación/decomiso **nuevos** en `V`. Esos kilos son decomisación del día de VI, no ratificación, y ya entran (si la visita cae en el período) en `mercaderia_decomisada_kg`.

Ninguna de estas limitaciones exige, para mostrar origen en Recorrido, un cambio de flujo. Sí condicionan el KPI.

---

## 7. Consultas SQL de solo lectura (casos incompletos, múltiples, ambiguos)

Ejecutar en réplica / entorno de análisis. No escriben.

### 7.1 Anclas de Recorrido con decomiso / clausura

```sql
-- Actuaciones con comprobación y sus actas de origen
SELECT
  a.id                    AS actuacion_ancla_id,
  a.fecha                 AS fecha_ancla,
  a.tipo                  AS tipo_ancla,
  a.comprobacion_id,
  c.numero_acta           AS acta_comprobacion,
  d.id                    AS decomiso_id,
  d.numero_acta           AS acta_decomiso,
  d.cantidad              AS kilos,
  cl.id                   AS clausura_id,
  cl.numero_acta          AS acta_clausura
FROM actuaciones a
JOIN comprobacion c ON c.id = a.comprobacion_id
LEFT JOIN decomiso d ON d.actuacion_id = a.id
LEFT JOIN clausura cl ON cl.actuacion_id = a.id
WHERE a.comprobacion_id IS NOT NULL;
```

### 7.2 Ambiguo: más de un decomiso alcanzable por la misma comprobación

```sql
SELECT a.comprobacion_id, COUNT(DISTINCT d.id) AS n_decomisos
FROM actuaciones a
JOIN decomiso d ON d.actuacion_id = a.id
WHERE a.comprobacion_id IS NOT NULL
GROUP BY a.comprobacion_id
HAVING COUNT(DISTINCT d.id) > 1;
```

Si hay filas: no basta `comprobacion_id → decomiso`; hay que fijar la ancla de Recorrido (`actuaciones.id` de la fila listada).

### 7.3 Ratificaciones de decomiso vs origen

```sql
SELECT
  i.id                    AS iniciador_id,
  i.tipo_iniciador,
  i.estado_iniciador,
  i.comprobacion_id,
  i.actuacion_id          AS ancla_id,
  i.oficio_id,
  ri.id                   AS ruta_item_id,
  ri.actuacion_id         AS visita_id,
  av.tipo                 AS tipo_visita,
  av.fecha                AS fecha_visita,
  rt.fecha                AS fecha_ruta,
  d.id                    AS decomiso_origen_id,
  d.cantidad              AS kilos_origen,
  dv.id                   AS decomiso_visita_id,
  dv.cantidad             AS kilos_visita
FROM iniciador_ruta i
JOIN ruta_item ri
  ON ri.iniciador_ruta_id = i.id
 AND ri.deleted_at IS NULL
 AND ri.estado_ruta_item = 'FINALIZADO'
 AND ri.estado_ejecucion = 'REALIZADO'
 AND ri.actuacion_id IS NOT NULL
JOIN ruta_trabajo rt ON rt.id = ri.ruta_trabajo_id
JOIN actuaciones av ON av.id = ri.actuacion_id
LEFT JOIN decomiso d  ON d.actuacion_id = i.actuacion_id
LEFT JOIN decomiso dv ON dv.actuacion_id = ri.actuacion_id
WHERE i.deleted_at IS NULL
  AND (
        i.tipo_iniciador = 'RATIFICACION_DECOMISO_OFICIO'
     OR av.tipo = 'RATIFICACION DE DECOMISO'
  )
  AND (i.actuacion_id IS NULL OR ri.actuacion_id <> i.actuacion_id);
```

Casos a etiquetar en el resultado:

- `decomiso_origen_id IS NULL` → incompleto (ratificación sin acta origen).
- `decomiso_visita_id IS NOT NULL` → riesgo de doble conteo si el KPI suma la visita.
- Varias filas con el mismo `decomiso_origen_id` → múltiple (DISTINCT en el KPI).

### 7.4 Mismo decomiso, más de una visita de ratificación

```sql
SELECT d.id AS decomiso_id, d.cantidad, COUNT(*) AS n_visitas_ratificacion
FROM decomiso d
JOIN iniciador_ruta i ON i.actuacion_id = d.actuacion_id AND i.deleted_at IS NULL
JOIN ruta_item ri
  ON ri.iniciador_ruta_id = i.id
 AND ri.deleted_at IS NULL
 AND ri.estado_ruta_item = 'FINALIZADO'
 AND ri.estado_ejecucion = 'REALIZADO'
 AND ri.actuacion_id IS NOT NULL
 AND ri.actuacion_id <> i.actuacion_id
JOIN actuaciones av ON av.id = ri.actuacion_id
WHERE i.tipo_iniciador = 'RATIFICACION_DECOMISO_OFICIO'
   OR av.tipo = 'RATIFICACION DE DECOMISO'
GROUP BY d.id, d.cantidad
HAVING COUNT(*) > 1;
```

### 7.5 Verificar e informar: inspección en visita vs origen

```sql
SELECT
  i.id,
  av.id                   AS visita_id,
  av.realizo_nueva_inspeccion,
  insp_v.id               AS inspeccion_visita_id,
  d.id                    AS decomiso_ancla_id,
  cl.id                   AS clausura_ancla_id
FROM iniciador_ruta i
JOIN ruta_item ri
  ON ri.iniciador_ruta_id = i.id
 AND ri.deleted_at IS NULL
 AND ri.estado_ruta_item = 'FINALIZADO'
 AND ri.estado_ejecucion = 'REALIZADO'
JOIN actuaciones av ON av.id = ri.actuacion_id
LEFT JOIN inspeccion insp_v ON insp_v.actuacion_id = av.id
LEFT JOIN decomiso d ON d.actuacion_id = i.actuacion_id
LEFT JOIN clausura cl ON cl.actuacion_id = i.actuacion_id
WHERE i.deleted_at IS NULL
  AND (
        i.tipo_iniciador = 'VERIFICAR_INFORMAR_OFICIO'
     OR av.tipo = 'VERIFICAR E INFORMAR'
  );
```

### 7.6 Estrategia de verificación (orden)

1. Correr 7.2 y 7.4 en un dump reciente: definen si el KPI puede ser `SUM(DISTINCT)` por `decomiso.id` o necesita regla extra.
2. Contar 7.3 con `decomiso_origen_id IS NULL` entre `CUMPLIDO`: huecos de presentación (guión), no bloquean TRAZA.1.
3. Contar `decomiso_visita_id IS NOT NULL`: si es > 0, el presenter de Recorrido **no** debe copiar actas de visita al bloque origen.
4. No «corregir» datos. Solo informar volúmenes a TRAZA.1 / INDICADORES-RATIFICACION.1.

---

## 8. Qué se resuelve solo con presenters / joins de lectura

Sí (TRAZA.1 / TRAZA.2), sin migraciones ni Completar trabajo:

- Bloque `origen_actas` en detalle Recorrido y, si hace falta, en cada ítem de `oficios_resumen`: `acta_decomiso_num`, `decomiso_kilos_total`, `acta_clausura_num` tomados de `actuacion_to_grid_row(ancla)` (o join `Decomiso`/`Clausura` por `i.actuacion_id`).
- Tipar esos campos en `IComprobacionRecorridoRow` / detalle.
- Mostrarlos en `filasActaComprobacionRecorrido` y/o en el relato de oficio **según tipo final** (tabla §3).
- Columnas equivalentes en PDF/XLSX de Recorrido.
- En Ver actuación de una **visita** de oficio: panel consultivo «Actas de la comprobación de origen» vía `iniciador.actuacion_id` (GET extra o embed en presenter de visita). No editar.
- KPI kilos ratificados: query nueva, mismo predicado «realizada» que ejecutivo, join ancla → `decomiso.cantidad`, `COUNT`/`SUM` con `DISTINCT decomiso.id`, filtro tipo final = solo ratificación de decomiso, período = `RutaTrabajo.fecha`.

No hace falta persistir `fecha_ratificacion` ni FK nueva comprobación→decomiso.

---

## 9. Qué quedaría fuera de foco si apareciera una limitación

Solo si el SQL de §7 mostrara un volumen material de:

| Hallazgo | Por qué no entra en TRAZA.* |
|---|---|
| Decomiso cargado en una actuación distinta de la ancla Recorrido, sin `comprobacion_id` compartido usable | Haría falta backfill / regla de attach. Eso es escritura de datos. |
| Ratificaciones históricas sin `iniciador.actuacion_id` ni `oficio.comprobacion_id` | Huérfanas: no hay join seguro. |
| Unificar kilos de visita y origen en una sola acta | Implicaría merge de `decomiso` (unique `actuacion_id` y `numero_acta+anio`). |
| Impedir labrar decomiso nuevo en Completar trabajo de ratificación | Cambio de flujo operativo. |
| Recalcular `mercaderia_decomisada_kg` para que «no cuente» kilos el día de origen | Cambio de KPI existente, fuera de este ticket. La card nueva es **adicional**. |
| Arreglar «Otras» en indicadores | Ticket separado, según alcance. |

Si 7.2/7.4 dan cero o pocos casos, TRAZA.1 sigue con ancla = `iniciador.actuacion_id` (fallback `oficio.comprobacion_id` → actuación Recorrido). Los incompletos se muestran vacíos.

---

## 10. Propuesta técnica y plan por etapas

### Principio

Una sola función de lectura, p. ej. `origen_actas_desde_ancla(act_ancla) -> { acta_decomiso_num, decomiso_kilos_total, acta_clausura_num }`, reutilizada por Recorrido list/detalle, export y (más adelante) Ver actuación. **Nunca** leer `Decomiso`/`Clausura` de la visita para ese bloque.

Selector de tipo final: reutilizar `_tipo_visita_resultado_final` sobre la visita; si no hay visita, el `tipo_iniciador` promovido del oficio.

### V1.1-TRAZA-COMPROBACION.1 — proyección read-only

- Extender `_payload` de oficio / detalle Recorrido con `origen_actas` (ancla) **sin** meter actas de visita en el mismo dict.
- Tests de presenter: ancla con decomiso; ancla con clausura; ancla con ambos; VI sin actas de origen; visita con decomiso propio **no** contamina origen.
- No UI todavía (o UI mínima detrás de flag si se adelanta). Sin migraciones.

### V1.1-TRAZA-COMPROBACION.2 — grillas, detalles, exportaciones

- Recorrido: cabecera y/o celdas de oficio según tipo final (tabla §3).
- Modal detalle: mismas filas.
- PDF/XLSX: columnas de origen.
- Ver actuación (visita de oficio): bloque origen de solo lectura.
- Vitest de labels/export; no tocar Completar trabajo.

### V1.1-INDICADORES-RATIFICACION.1 — card kilos ratificados

- Universo = visitas realizadas con tipo final **Ratificación de decomiso** (iniciador y/o `actuaciones.tipo` de visita), `RutaTrabajo.fecha` en rango (paridad con `ratificaciones_decomiso_realizadas`).
- Valor = `SUM(decomiso.cantidad)` del decomiso de **`iniciador.actuacion_id`**, `decomiso.id` distinto.
- Excluir VI y ratificación de clausura.
- No restar ni alterar `mercaderia_decomisada_kg`.
- Card + línea PDF ejecutivo. Serie mensual opcional por `RutaTrabajo.fecha` (no por `decomiso` / ancla).
- Test: dos visitas sobre el mismo decomiso en el período → se cuenta **una** vez los kilos; visita sin decomiso origen → 0; decomiso en visita y no en ancla → 0 en este KPI.

### Orden y riesgos

```
TRAZA.0 (este doc)
  → TRAZA.1 presenters
      → TRAZA.2 UI Recorrido / export / detalle
  → INDICADORES-RATIFICACION.1 (puede empezar en paralelo a TRAZA.2;
     depende de la misma join ancla, no de la UI)
```

Riesgo principal: doble conteo (§7.4). Se mitiga en la query del KPI, no cambiando datos.  
Riesgo secundario: confundir actas de visita con origen; se mitiga con nombres de campo (`origen_*`) y tests explícitos.

---

## 11. Conclusión

Con los vínculos actuales **sí** se puede mostrar el contrato del ticket:

| Tipo final | Origen a traer | Factible con joins |
|---|---|---|
| Ratificación de decomiso | Acta de decomiso + kilos de la ancla | Sí |
| Ratificación de clausura | Acta de clausura de la ancla | Sí |
| Verificar e informar | Decomiso/kilos y clausura si existen en la ancla | Sí |

El indicador **Kilos ratificados** también es factible: fuente = `decomiso.cantidad` de la ancla; fecha de imputación = fecha operativa de la visita de ratificación (`RutaTrabajo.fecha` para el card, `Actuaciones.fecha` de visita para Recorrido); solo tipo Ratificación de decomiso; `DISTINCT decomiso.id` para no doble-contar.

Nada de eso requiere modificar Completar trabajo, actas, estados ni migraciones. El trabajo siguiente es proyección de lectura.
