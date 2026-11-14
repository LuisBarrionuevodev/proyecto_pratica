# V1.1-INDICADORES-CLASIFICACION.0 — Actuaciones realizadas, Cargar actuación y “Otras”

**Fecha:** 2026-11-14  
**Alcance:** diagnóstico (sin cambios de queries, UI ni datos).  
**HEAD analizado:** `9e9f0e9a` (`main`).

---

## Resumen ejecutivo

1. El KPI **Actuaciones realizadas** **no cuenta filas de `actuaciones`**. Cuenta **ítems de ruta** (`RutaItem.id` distintos) con cierre operativo `REALIZADO` en una **ruta publicada** cuya **fecha de ruta** cae en el período.
2. **Cargar actuación** (grid/modal `POST /actuaciones` o `/grid/commit-*`) **crea `Actuaciones` y no crea `RutaItem`**. Según la lógica vigente, **no debería entrar** a ese KPI salvo que más tarde exista un cierre de ruta vinculado a esa actuación (p. ej. Completar trabajo, o una visita posterior de reinspección).
3. En la tabla **Actuaciones realizadas por inspector**, **Otras no es un tipo de actuación**. Es un **alias de presentación** del bucket **`denuncias`**: denuncias realizadas que no tienen columna propia. La card ejecutivo **no tiene** “Otras”. El PDF usa el mismo campo `otras` que la tabla.
4. Hay **otra** “Otras” en **No realizadas** (contraproducencia residual). No mezclarlas.
5. Los IDs/filas que compartió Luis **no están en este ticket**. La causa de “algunas cargas manuales no aparecen” queda **demostrada a nivel de modelo**; para confirmar fila a fila hace falta inspector, período e IDs.

---

## 1. Definición vigente de **Actuaciones realizadas**

### 1.1 Unidad de conteo

| Pregunta | Respuesta vigente |
|----------|-------------------|
| ¿Cuenta actuaciones? | **No** como unidad primaria. Usa `COUNT(DISTINCT RutaItem.id)`. |
| ¿Cuenta OT? | No. |
| ¿Cuenta visitas de ruta? | **Sí**: un `RutaItem` cerrado como realizado. |
| Nombre UI | “Actuaciones realizadas” (`DashboardEjecutivoSection`, PDF, export). |

Fuente: `count_cierres_realizados` en `Backend/app/domains/indicadores/services/indicadores_operativos_queries.py`.

Criterio canónico (docstring D1d.11fix-a / D1d.11fix-a4):

- `RutaTrabajo.estado_ruta == PUBLICADA`
- `RutaTrabajo.fecha` ∈ `[desde, hasta]` (**día operativo de la ruta**, no `Actuaciones.fecha` ni `RutaItem.ejecutado_at`)
- `RutaItem.estado_ruta_item == FINALIZADO`
- `RutaItem.estado_ejecucion == REALIZADO`
- `RutaItem.actuacion_id IS NOT NULL`
- `RutaItem.deleted_at IS NULL` y `IniciadorRuta.deleted_at IS NULL`
- Join obligatorio: `RutaItem` → `IniciadorRuta` → `RutaTrabajo` → `Actuaciones`

`ejecutado_at` es auditoría; **no** define el mes del Dashboard.

Test de contrato: `test_actuacion_cruda_sin_cierre_no_cuenta_realizada` vs `test_ruta_item_realizado_con_actuacion_cuenta` (`Backend/tests/test_indicadores_realizadas_base.py`).

### 1.2 Filtros

Query compartida (`GET /api/indicadores/ejecutivo`, `/productividad`, `/riesgo`, etc.): `desde`, `hasta` (obligatorios), `distrito_id?`, `inspector_id?`.

| Filtro | Cómo se aplica |
|--------|----------------|
| Período | `RutaTrabajo.fecha` inclusive. El front arma `desde`/`hasta` con `useIndicadoresFiltros` (mes actual, tabs Semanal/Mensual/… o month picker). |
| Distrito | Domicilio efectivo: `COALESCE(Actuaciones.domicilio_id, IniciadorRuta.domicilio_id)` → `Domicilio.distrito_id`. En productividad por inspector el join de distrito usa **solo** `Actuaciones.domicilio_id` (`_apply_distrito_filter` en `indicadores_productividad_queries.py`) — **posible desvío menor** vs ejecutivo. |
| Inspector | `_realizados_inspector_coincide`: grupo de ruta **o** `actuaciones_inspector`. Un inspector de sesión (`relevador`) se fuerza por JWT (`resolve_effective_inspector_id`). |
| Estado de ejecución | Solo `REALIZADO` + ítem `FINALIZADO`. No entra `NO_REALIZADO` ni pendientes. |

### 1.3 Cards ejecutivo (desglose, no “Otras”)

`GET /api/indicadores/ejecutivo` → `build_indicadores_ejecutivo`:

| KPI | Unidad / regla |
|-----|----------------|
| `actuaciones_realizadas` | Todos los `RutaItem` que cumplen el criterio (cualquier `tipo_iniciador`). |
| `inspecciones_realizadas` | Subconjunto productividad: `tipo_iniciador == RELEVAMIENTO` (misma subquery que la columna Inspección). |
| `reinspecciones_notificacion_realizadas` | Bucket híbrido `REINSPECCION_NOTIFICACION`. |
| `reinspecciones_oficio_realizadas` | Suma oficio: `REINSPECCION_OFICIO` + ratificaciones + verificar e informar. |
| Ratificaciones / Verificar | Desglose híbrido iniciador + `Actuaciones.tipo` (`bucket_operativo`). |
| `actas_labradas` | Actas sobre **actuaciones IDs** de esos cierres (otra unidad: actas, no visitas). |

La suma de las cards de tipo **no** tiene por qué igualar `actuaciones_realizadas`: el total incluye también **denuncias** y residual `OTRO` en iniciador; las cards de tipo no muestran denuncia.

### 1.4 ¿Deben participar las cargas de **Cargar actuación**?

**Según la lógica actual: no, por el solo hecho de existir en `actuaciones`.**

El canal Cargar actuación:

- Persiste `Actuaciones` (+ inspectores, OT, domicilio).
- **No crea `RutaItem`** (documentado en `Frontend/docs/v1_1_act_edit_0_relevamiento.md` §3.2; el dominio grid no toca `RutaItem`).
- Post-commit: `ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal` → `sync_iniciadores_reinspeccion_notificacion`. Eso puede crear un **iniciador pendiente** `REINSPECCION_NOTIFICACION` si hay notificación vencida. El iniciador **no es un cierre realizado**.

Completar trabajo, en cambio, cierra un `RutaItem` existente y setea `actuacion_id` + `REALIZADO`.

Criterio funcional vigente (código + tests): **indicador = visita de ruta cerrada**, no **registro documental cargado a mano**.

---

## 2. Qué es **Otras** (Actuaciones realizadas)

Hay **dos** “Otras” en el dashboard. El ticket apunta a **realizadas**.

### 2.1 Tabla / PDF: Actuaciones realizadas por inspector

Endpoint: `GET /api/indicadores/productividad` → `query_inspectores_realizadas`.

Universo más chico que el KPI ejecutivo: solo tipos

`RELEVAMIENTO`, `REINSPECCION_NOTIFICACION`, `DENUNCIA`, y los cuatro de oficio (`REINSPECCION_OFICIO`, `RATIFICACION_*`, `VERIFICAR_INFORMAR_OFICIO`).

Mapeo:

| `tipo_iniciador` | Bucket interno | Columna UI |
|------------------|----------------|------------|
| `RELEVAMIENTO` | `inspecciones` | Inspección |
| Oficio (4 valores) | `reinspecciones_oficio` | Reins. oficio |
| `REINSPECCION_NOTIFICACION` | `reinspecciones_notificacion` | Reins. notif. |
| `DENUNCIA` | `denuncias` | **no hay columna** |

Cálculo explícito (`indicadores_productividad_queries.py`):

```text
total_realizadas = inspecciones + reinspecciones_oficio + reinspecciones_notificacion + denuncias
visible_sin_denuncia = inspecciones + reinspecciones_oficio + reinspecciones_notificacion
otras = max(0, total - visible_sin_denuncia)  # = denuncias
```

Contrato de tests: `test_realizada_suma_por_tipo` exige `total == inspecciones + oficio + notif + otras` y, si el tipo es `DENUNCIA`, `otras >= denuncias`.

**Conclusión:** **Otras (realizadas) = denuncias realizadas** (visitas con iniciador `DENUNCIA`). No es residual de `Actuaciones.tipo` (INSPECCION, COMPROBACION, etc.). No incluye Cargar actuación “suelta”.

UI: header tooltip “Otros tipos operativos”; **no muestra** `denuncias` como columna. El PDF (`dashboardPdfMappers.ts`) copia `r.otras`. El front **no reclasifica**.

### 2.2 “Otras” de **No realizadas** (no confundir)

En no realizadas, `otras` es el bucket residual de **motivo/contraproducencia** (`BUCKET_OTRAS`): p. ej. `OTRO`, valores no mapeados a local cerrado / no existe / clima / no se ratificó. Misma etiqueta, **otra métrica**.

### 2.3 Card ejecutivo vs tabla vs PDF

| Superficie | ¿Hay “Otras” realizadas? | Fuente |
|------------|--------------------------|--------|
| Cards ejecutivo | No | `kpis.actuaciones_realizadas` y desgloses por tipo de visita |
| Tabla productividad | Sí = denuncias | `inspectores_realizadas[].otras` |
| PDF productividad | Sí = mismo campo | mapper |
| Export CSV/payload | Cards usan kpis ejecutivo; tablas usan productividad | `buildDashboardExportPayload.ts` |

El **total** de la tabla por inspector **no es el mismo universo** que la card “Actuaciones realizadas”: la card incluye **todos** los iniciadores; la tabla **omite** iniciadores fuera de `_TIPOS_PRODUCTIVIDAD` (p. ej. residual `OTRO` de `bucket_operativo`).

---

## 3. Diferencia observada (Cargar actuación vs indicador)

### 3.1 Camino que **no** cuenta (típico de carga manual)

```
Cargar actuación → Actuaciones (+ actuaciones_inspector)
                 → NO RutaItem
                 → count_cierres_realizados = 0 para esa fila
```

Punto exacto de exclusión: join `RutaItem.actuacion_id == Actuaciones.id` + estados de cierre. Sin ítem, la actuación **no existe** para el indicador.

Filtros adicionales si *hubiera* ítem:

- Período por **fecha de ruta**, no fecha de la actuación.
- Inspector: debe estar en grupo de ruta o en `actuaciones_inspector`.
- Distrito: domicilio efectivo.

### 3.2 Camino que **sí** puede contar (aunque el usuario recuerde “Cargar actuación”)

Hipótesis **compatibles con el código** (a verificar con IDs):

| Hipótesis | Qué buscar en BD |
|-----------|------------------|
| A. Completó trabajo el mismo día / misma OT | `ruta_item.actuacion_id = id` y `estado_ejecucion = REALIZADO` |
| B. Carga manual + más tarde visita de reinspección sobre esa actuación | `RutaItem` de otra ruta con esa `actuacion_id` o iniciador derivado cerrado |
| C. Confusión de pantallas: Gestión de actuaciones lista **todas** las filas; Indicadores solo cierres | Misma `actuaciones.id` aparece en Gestión y no en KPI |
| D. Período: `Actuaciones.fecha` en el mes filtrado, `RutaTrabajo.fecha` en otro mes | Comparar ambas fechas |
| E. “Otras” vs Inspección: denuncia sí suma al **total** de la tabla pero solo en columna Otras; relevamiento suma en Inspección | `tipo_iniciador` |

La observación “una carga manual sí aparece y otras no” **encaja** con A/B/D (la que aparece tiene cierre de ruta o cae en el período de ruta), no con un bug de `tipo_actuacion` en el KPI total.

### 3.3 Datos de Luis

**No hay en el ticket ni en el repo** inspector, rango ni IDs. No se consultó ni modificó producción/sandbox para este relevamiento.

Para **confirmar fila a fila** hace falta:

- `inspector_id` o nombre
- `desde` / `hasta` usados en Indicadores
- IDs de actuaciones “no aparecen” vs “sí aparece”
- Para cada ID: `actuaciones.fecha`, `tipo`, `orden_trabajo_id`, filas `actuaciones_inspector`, existencia de `ruta_item` (`id`, `ruta_trabajo_id`, `estado_ejecucion`, `estado_ruta_item`, `actuacion_id`), `ruta_trabajo.fecha` y `estado_ruta`, `iniciador_ruta.tipo_iniciador`

Query de inclusión (solo lectura):

```sql
SELECT a.id, a.fecha, a.tipo, ri.id AS ruta_item_id, ri.estado_ejecucion,
       rt.fecha AS fecha_ruta, rt.estado_ruta, ir.tipo_iniciador
FROM actuaciones a
LEFT JOIN ruta_item ri ON ri.actuacion_id = a.id AND ri.deleted_at IS NULL
LEFT JOIN ruta_trabajo rt ON rt.id = ri.ruta_trabajo_id
LEFT JOIN iniciador_ruta ir ON ir.id = ri.iniciador_ruta_id
WHERE a.id IN (...);
```

Si `ruta_item_id` es NULL o `estado_ejecucion <> 'REALIZADO'` o `estado_ruta <> 'PUBLICADA'` o `fecha_ruta` fuera de rango → **no entra**. Eso cierra el caso sin inferir “deberían incluirse”.

---

## 4. Contraste de fuentes

| Consumidor | Endpoint | Servicio | ¿Misma fórmula de “realizadas”? |
|------------|----------|----------|----------------------------------|
| Card “Actuaciones realizadas” | `GET /api/indicadores/ejecutivo` | `count_cierres_realizados` | Universo completo de cierres |
| Cards tipo (inspección, reins., etc.) | mismo | buckets productividad / iniciador | Subconjuntos |
| Tabla por inspector | `GET /api/indicadores/productividad` | `query_inspectores_realizadas` | Solo 4 familias; Otras = denuncia |
| PDF / export tablas | mismos JSON | mappers front | Sin recálculo |
| Gestión de actuaciones | `GET /actuaciones` | listado documental | **Otra fuente**: filas `actuaciones` por fecha de actuación |

Desfase típico **Gestión vs Indicadores** = inclusión (sin `RutaItem`), no presentación.

Desfase **card vs tabla inspector** = universo (todos los iniciadores vs `_TIPOS_PRODUCTIVIDAD`) + la card no desglosa denuncias.

---

## 5. Consumidores afectados (si hubiera ticket correctivo)

- Cards: `DashboardEjecutivoSection.tsx`
- Tabla: `DashboardProductividadSection.tsx` (`otras`)
- API: `indicadores_ejecutivo_service.py`, `indicadores_productividad_queries.py`, `indicadores_operativos_queries.py`
- PDF: `dashboardPdfMappers.ts`
- Export: `buildDashboardExportPayload.ts`
- Tests: `test_indicadores_realizadas_base.py`, `test_indicadores_productividad.py`

---

## 6. Propuesta mínima para ticket posterior

**No implementar aquí.** Opciones (elegir producto):

| Opción | Idea | Riesgo |
|--------|------|--------|
| **P0 clarificar UX** | Tooltip/copy: “Visitas de ruta cerradas (Completar trabajo). No incluye altas de Cargar actuación sin visita.” Renombrar columna Otras → “Denuncias”. | Bajo. No cambia números. |
| **P1 alinear card y tabla** | Card denuncia o incluir denuncias en desglose ejecutivo; misma lista de tipos. | Medio: cambian KPIs publicados. |
| **P2 incluir cargas manuales** | Contar `actuaciones` sin `RutaItem` (p. ej. por `Actuaciones.fecha` + inspector). | Alto: rompe D1d.11fix-a, doble conteo si luego se cierra ruta, periodo distinto. Requiere regla de unicidad. |

Pruebas sugeridas P0: snapshot de labels; P1/P2: fixtures `actuacion_cruda_sin_cierre` (hoy **no** cuenta) vs cierre; caso denuncia → columna; IDs de Luis en sandbox/prod **solo lectura**.

---

## 7. Fuera de alcance (cumplido)

- Sin cambios de queries, cards, tablas ni export.
- Sin UPDATE/DELETE de actuaciones.
- Sin mezclar con media ni edición de contribuyentes.
- Sin afirmar que las cargas manuales “deban” entrar al KPI: el criterio vigente es **cierre de ruta**.
