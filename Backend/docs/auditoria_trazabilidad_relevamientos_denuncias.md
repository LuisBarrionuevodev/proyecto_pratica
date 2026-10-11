# Auditoría V1.1-TRAZABILIDAD-RELEVAMIENTOS.0

**Objetivo:** explicar por qué en **Gestión de Relevamientos** (y bandejas equivalentes de **Denuncias**) predominan los casos con inspección exitosa y no se ven cierres terminales (p. ej. **No existe local**).

**Alcance de este documento:** solo lectura de código y tests de caracterización. **No** se modificó lógica de producto, datos productivos, filtros ni estados en runtime.

---

## 1. Resumen ejecutivo

| Hallazgo | Detalle |
|----------|---------|
| Causa principal | La pestaña **Realizados** de Relevamientos filtra **únicamente** `iniciador_ruta.estado_iniciador = CUMPLIDO`. Los cierres con contraproducencia **No existe local** dejan `CERRADO_NO_EXISTE_LOCAL` → **no entran**. |
| Efecto colateral | Esos mismos casos **tampoco** aparecen en **Pendientes** (`gestion-operativa`), que exige `PENDIENTE`. Quedan **fuera de ambas bandejas** de Gestión. |
| Denuncias | No hay endpoint simétrico a `/relevamientos/realizados`. **Realizados** usa `GET /api/denuncias/gestion` con filtro sobre `denuncia.estado` (`CERRADA` / no cerrada), **sin** sincronizar automáticamente con el cierre vía ruta. |
| Mapa / indicadores | El mapa operativo de **cierres** (`list_mapa_operativo_cierres_geo_with_meta`) sí puede incluir `NO_REALIZADO` y motivos; **no** es la misma fuente que Gestión de Relevamientos. |
| Urgentes | Relevamientos **nunca** entran a urgentes (`tipo == RELEVAMIENTO` → excluido). Denuncias reencoladas `PENDIENTE` sí pueden planificarse/urgentes según prioridad. |

---

## 2. Qué ocurre al **Completar trabajo** (Relevamiento / Denuncia)

Flujo común: `POST /actuaciones/completar-trabajo/cerrar/:ruta_item_id` → `completar_trabajo_cierre_service.ejecutar_cierre_completar_trabajo`.

### 2.1 Registros tocados

| Entidad | Rol |
|---------|-----|
| `ruta_item` | Estado de ejecución del ítem en la ruta del día. |
| `iniciador_ruta` | Cola / ciclo de vida del disparador (relevamiento o denuncia). |
| `actuaciones` | Acta(s) del cierre (inspección, comprobación, contraproducencia persistida, etc.). |
| `relevamiento` / `denuncia` | Origen de negocio; **no** reciben un campo único “resultado de cierre” automático en todos los caminos. |

### 2.2 Estados por tipo de cierre (`completar_trabajo_cierre_service.py`)

| Resultado operativo | `ruta_item.estado_ejecucion` | `ruta_item.estado_ruta_item` | `ruta_item.motivo_no_realizado` | `iniciador_ruta.estado_iniciador` | Reencola mapa/planificación |
|---------------------|------------------------------|------------------------------|----------------------------------|-----------------------------------|------------------------------|
| Visita realizada (sin contra) | `REALIZADO` | `FINALIZADO` | `null` | `CUMPLIDO` | No |
| **No existe local** | `NO_REALIZADO` | `FINALIZADO` | `NO_EXISTE_LOCAL` | **`CERRADO_NO_EXISTE_LOCAL`** | No (cierre lógico del iniciador) |
| Contraproducencia reencolable (p. ej. local cerrado, clima, otro) | `NO_REALIZADO` | `FINALIZADO` | según bucket | **`PENDIENTE`** (+ prioridad alta vía `aplicar_reencolado_iniciador`) | Sí |
| No permite inspección (con comprobación válida) | `REALIZADO` | `FINALIZADO` | `null` | `CUMPLIDO` | No |

**Actuación:** se crea/actualiza en el mismo servicio; con visita realizada hay acta de inspección; con contraproducencia se persiste `actuaciones.contraproducencia` (p. ej. `NO_EXISTE_LOCAL`).

**Relevamiento / Denuncia origen:** el registro de origen **permanece**; no hay en este servicio un `UPDATE relevamiento SET estado = …` ni `denuncia.estado = CERRADA` sistemático al cerrar la ruta.

---

## 3. APIs que alimentan las tablas de Gestión

### 3.1 Relevamientos (frontend)

| Pestaña UI | Hook | Endpoint backend | Servicio |
|------------|------|------------------|----------|
| **Pendientes** | `useRelevamientosBandeja("pendientes")` | `GET /relevamientos/gestion-operativa` | `listar_relevamientos_operativos_con_filtros` |
| **Realizados** | `useRelevamientosBandeja("realizados")` | `GET /relevamientos/realizados` | `listar_relevamientos_realizados_actuacion_completada_con_filtros` |

Texto UI (`RelevamientosContainer.tsx`): Realizados = “Relevamientos con actuación completada en ruta (**CUMPLIDO**)”.

### 3.2 Denuncias (frontend)

| Pestaña UI | Hook | Endpoint | Servicio |
|------------|------|----------|----------|
| **Pendientes** | `useDenunciasBandeja("pendientes")` | `GET /api/denuncias/gestion-operativa` | `listar_denuncias_gestion_operativa` |
| **Realizados** | `useDenunciasBandeja("realizados")` | `GET /api/denuncias/gestion` | `listar_denuncias_gestion` |

Filtro **Realizados** denuncias: `estado=hechas|no_hechas|all` sobre **`denuncia.estado`** (`ABIERTA` / `CERRADA` / `DESCARTADA`), **no** sobre `iniciador_ruta.estado_iniciador`.

---

## 4. Condición exacta que excluye cierres terminales

### 4.1 Relevamientos — Pendientes

```sql
-- listar_relevamientos_operativos_con_filtros (list_service.py)
IniciadorRuta.tipo_iniciador = 'RELEVAMIENTO'
AND IniciadorRuta.estado_iniciador = 'PENDIENTE'
AND IniciadorRuta.deleted_at IS NULL
```

**Excluye:** `CUMPLIDO`, `CERRADO_NO_EXISTE_LOCAL`, `ANULADO`, etc.

### 4.2 Relevamientos — Realizados

```sql
-- EXISTS en listar_relevamientos_realizados_actuacion_completada_con_filtros
IniciadorRuta.relevamiento_id = relevamiento.id
AND tipo_iniciador = 'RELEVAMIENTO'
AND estado_iniciador = 'CUMPLIDO'
AND deleted_at IS NULL
```

**Excluye:** todo cierre que no deje el iniciador en **`CUMPLIDO`**, incluido **`CERRADO_NO_EXISTE_LOCAL`** (No existe local).

**Nota:** el docstring del endpoint habla de “actuación completada”; la implementación **no** exige `actuacion_id` en el iniciador, solo el estado **`CUMPLIDO`**.

### 4.3 Denuncias — Pendientes

Misma regla que relevamientos con `tipo_iniciador = 'DENUNCIA'` y `estado_iniciador = 'PENDIENTE'`.

### 4.4 Denuncias — Realizados (`/gestion`)

```python
# listar_denuncias_gestion — filtro opcional estado
if filters.estado == "hechas":
    Denuncia.estado == "CERRADA"
elif filters.estado == "no_hechas":
    Denuncia.estado != "CERRADA"
```

Completar trabajo **no** setea `denuncia.estado = CERRADA` en el servicio de cierre revisado. Un cierre exitoso (`CUMPLIDO`) puede seguir figurando como **`ABIERTA`** en gestión “hechas/no_hechas”.

---

## 5. Tabla: estado real → visibilidad actual → visibilidad esperada (negocio)

| Origen | Resultado de cierre | Estado iniciador (típico) | Gestión Pendientes | Gestión Realizados / historial | Urgentes / mapa pendientes | Visibilidad esperada (ticket) |
|--------|---------------------|---------------------------|--------------------|--------------------------------|----------------------------|-------------------------------|
| Relevamiento | Inspección realizada | `CUMPLIDO` | No | **Sí** (`/realizados`) | No (relev. fuera urgentes) | Sí | Sí |
| Relevamiento | No existe local | `CERRADO_NO_EXISTE_LOCAL` | No | **No** | No | **Sí** (resultado visible) | No |
| Relevamiento | Local cerrado / reencolable | `PENDIENTE` | **Sí** | No | Planificación M4 / mapa pendientes si agregable | Sí (estado claro) | Sí |
| Denuncia | Inspección realizada | `CUMPLIDO` | No | Parcial (`/gestion`, estado denuncia) | Urgentes si prioridad ≥3 y agregable | Sí | No |
| Denuncia | No existe local | `CERRADO_NO_EXISTE_LOCAL` | No | **No** (misma brecha que relev.) | No | **Sí** | No |
| Denuncia | Reencolable | `PENDIENTE` | **Sí** | No | Sí (denuncia en urgentes) | Sí | Sí |

---

## 6. ¿Solo visual o también export / indicadores / mapa?

| Superficie | ¿Ve cierres terminales NO EXISTE LOCAL? |
|------------|----------------------------------------|
| Gestión Relevamientos (2 pestañas) | **No** (brecha entre bandejas) |
| Gestión Denuncias | **No** / ambiguo (estado entidad vs iniciador) |
| Export CSV Relevamientos/Denuncias | **No** export en tablas (`relevamientosNoExport.test.ts`) |
| Indicadores no realizadas | **Sí** (consultas sobre `ruta_item` + motivo; p. ej. `indicadores_no_realizadas_queries.py`) |
| Mapa operativo cierres | **Sí** (universo `REALIZADO` / `NO_REALIZADO` con filtros de motivo) |
| Mapa / cola pendientes | Solo `iniciador PENDIENTE` → terminal no aparece (correcto para no reencolar) |

La exclusión en Gestión es **de contrato de listado (backend + pestaña UI)**, no un bug de render aislado en MRT.

---

## 7. ¿`NO EXISTE LOCAL` queda bien cerrado fuera de Urgentes/Mapa?

| Pregunta | Respuesta |
|----------|-----------|
| ¿Iniciador deja de ser `PENDIENTE`? | **Sí** → `CERRADO_NO_EXISTE_LOCAL`. |
| ¿Vuelve a planificación / urgentes? | **No** (`planificable_iniciadores_base_query` exige `PENDIENTE`). |
| ¿Relevamiento en urgentes? | **Nunca** (política `elegible_urgente_planificacion`). |
| ¿Aparece en mapa de **pendientes**? | **No** (cola PENDIENTE). |
| ¿Puede aparecer en mapa de **cierres**? | **Sí**, como cierre `NO_REALIZADO` con motivo (si hay geocode y rango de fechas). |
| ¿Trazable en Gestión Relevamientos? | **No hoy** → gap de trazabilidad operativa para el relevador. |

---

## 8. Archivos involucrados

### Backend

- Cierre: `app/domains/actuaciones/services/completar_trabajo_cierre_service.py`, `completar_trabajo_contraproducencia.py`, `actuacion_reencolado_service.py`
- Listados relevamiento: `app/domains/relevamientos/services/list_service.py`, routes `list_operativa.py`, `list_realizados.py`
- Denuncias: `app/domains/denuncias/services/denuncias_service.py`, `routes.py`
- Planificación / urgentes: `iniciadores_pendientes_service.py`, `planificacion_service.py`, `utils/planificacion_prioridad.py`
- Mapa: `geolocalizacion/geocode/services/map_operativo_service.py`
- Indicadores: `indicadores/services/indicadores_no_realizadas_queries.py`

### Frontend

- `Frontend/src/Containers/Relevamientos/hooks/useRelevamientosBandeja.ts`
- `Frontend/src/Containers/Relevamientos/RelevamientosContainer.tsx`
- `Frontend/src/Containers/Relevamientos/hooks/useDenunciasBandeja.ts`
- `Frontend/src/Containers/Relevamientos/Components/DenunciasCrudPlaceholder.tsx`
- APIs: `Frontend/src/api/relevamientosListApi.ts`, `Frontend/src/api/denunciasApi.ts`

### Test de caracterización (solo auditoría)

- `Backend/tests/test_auditoria_trazabilidad_relevamientos_char.py`

---

## 9. Alcance estimado del arreglo (propuesta mínima, **sin implementar**)

| Opción | Descripción | Esfuerzo relativo |
|--------|-------------|-------------------|
| **A. Solo filtro/presenter** | Nueva bandeja o ampliar **Realizados** a “Cierres” con unión `CUMPLIDO` **OR** estados terminales (`CERRADO_NO_EXISTE_LOCAL`, opcionalmente otros `CERRADO_*`), enriqueciendo fila con `iniciador_estado`, `motivo_no_realizado`, `contraproducencia` desde último `ruta_item` / actuación. | Medio (backend list + columnas UI) |
| **B. Contrato API** | Endpoint unificado `GET /relevamientos/gestion-cierres` (y espejo denuncias) con enum `resultado_operativo` calculado; deprecar lectura literal “solo CUMPLIDO = realizado”. | Medio–alto |
| **C. Circuito/estado entidad** | Al cerrar, actualizar `denuncia.estado` / campo futuro en relevamiento; sincronizar con iniciador. Requiere reglas de negocio y migración si se persisten nuevos campos. | Alto |

**Recomendación mínima:** **A + presenter** — tercera pestaña “**Cerrados / Todos los resultados**” o redefinir Realizados como “**Ya procesados en ruta**” (`CUMPLIDO` ∪ terminales), mostrando etiqueta de resultado. Denuncias: alinear con **`iniciador_ruta`** (y opcionalmente cerrar `denuncia.estado` en cierre).

---

## 10. Casos mínimos de reproducción (local/test)

Fixtures / tests:

- `Backend/tests/test_auditoria_trazabilidad_relevamientos_char.py` — demuestra que `CERRADO_NO_EXISTE_LOCAL` no está en operativos ni realizados; `CUMPLIDO` solo en realizados; `PENDIENTE` solo en operativos.

Para QA manual (misma lógica que producción):

1. Crear relevamiento → publicar ruta → Completar trabajo con **No existe local**.
2. Gestión → Pendientes: no listado; Realizados: no listado.
3. Repetir con inspección OK → Realizados: **sí**.
4. Repetir con Local cerrado → Pendientes: **sí** (reencolado).

---

## 11. Confirmación de alcance del ticket

- **No** se modificaron servicios de cierre, listados, filtros ni modelos de producto.
- **No** se ejecutaron migraciones ni cambios en datos productivos.
- **Sí** se agregó documentación (`Backend/docs/auditoria_trazabilidad_relevamientos_denuncias.md`) y tests de caracterización que **documentan el comportamiento actual** (pueden fallar si en el futuro se corrige la brecha — eso sería el ticket de fix).
