# OPER-RUTA.7B-HOTFIX — Relevamientos geolocalizados en Planificación M4

## Causa raíz

**Regresión en el path M4 optimizado (OPER-RUTA.7B)**, no en frontend 7C.

El path legacy (`get_iniciadores_pendientes_para_ruta` sin SQL optimizado) filtraba distrito **después** de resolver domicilio efectivo con `apply_backfill=True`, que ejecuta `backfill_distrito_for_domicilio_if_needed` cuando `domicilio.distrito_id` es NULL pero hay geocode OK con lat/lng.

El path optimizado (`_get_iniciadores_pendientes_m4_optimizado` → `apply_joins_y_filtro_distrito_efectivo`) aplicaba solo:

```sql
dom_efectivo.distrito_id = :distrito_id
```

**Filtro donde caía el relevamiento:** paso **`distrito`** (SQL), con motivo **`distrito_id NULL en domicilio efectivo`** aunque el punto geocode cae dentro del polígono del distrito seleccionado.

Esto afecta sobre todo a relevamientos/domicilios **recién geolocalizados** cuyo `distrito_id` aún no está persistido (o nunca se backfillearon antes del listado).

## Qué no era

- No era filtro de tipo RELEVAMIENTO (enum correcto).
- No era rubro (`relevamiento.rubro_id` no participa en M4 SQL).
- No era elegibilidad pool/ruta (6I/6J intacto).
- No era cache frontend (bug reproducible en backend M4).

## Fix aplicado

Archivo: `Backend/app/domains/rutas_trabajo/utils/planificacion_m4_sql.py`

- Join a `domicilio_geocode` del domicilio efectivo (PR5).
- Filtro distrito alineado con path legacy + mapa geolocalización:
  - **FK:** `dom_efectivo.distrito_id == distrito_id`
  - **Fallback espacial:** si FK es NULL, geocode OK con lat/lng y punto dentro del polígono del distrito (`ST_Contains` / `ST_Intersects` + `ST_SwapXY`, misma convención que `resolve_distrito_id`).
- Domicilio efectivo de RELEVAMIENTO sigue viniendo de `relevamiento.domicilio_id` vía joins PR5 existentes.

Debug gated: `log_oper_ruta_m4_relev_debug` en `planificacion_debug.py` (`PLANIFICACION_DEBUG=1`).

## Regla final M4 para Relevamiento

> Si el iniciador está **PENDIENTE**, **libre** (sin pool/ruta bloqueante) y su **domicilio efectivo** (iniciador alineado o `relevamiento.domicilio_id`) tiene geocode **OK** con coordenadas, debe aparecer en M4 del distrito donde:
> - `domicilio.distrito_id` coincide, **o**
> - `distrito_id` es NULL pero el punto cae en el polígono del distrito (misma regla que backfill / mapa geo).

Tras la página devuelta, `_enriquecer_domicilio_efectivo_pagina` sigue persistiendo `distrito_id` vía backfill cuando corresponde.

## Archivos tocados

| Archivo | Cambio |
|---------|--------|
| `planificacion_m4_sql.py` | Filtro distrito FK + espacial; join geocode efectivo |
| `planificacion_debug.py` | Log `[OPER_RUTA_M4_RELEV_DEBUG]` |
| `tests/test_oper_ruta_7b_hotfix_relevamientos_m4.py` | Tests hotfix (7 casos) |

**No tocado:** geocode service, PR11/12, publicar, Completar Trabajo, exports, indicadores, reglas 6F/6G/6H/6I/6J, UI 7C.

## Tests

```bash
py -3.14 -m pytest tests/test_oper_ruta_7b_hotfix_relevamientos_m4.py -q
py -3.14 -m pytest tests -k "oper_ruta_7b_hotfix or m4 or pendientes_contexto" -q
```

Resultado: **21 passed** (hotfix + suite M4 existente).

## QA manual sugerido

1. Crear relevamiento nuevo, geolocalizar en Mapa de geolocalización.
2. Ruta Trabajo → Planificación → distrito del punto → chip Relev.
3. Confirmar candidato en lista y mapa.
4. Agregar al pool → desaparece de candidatos, aparece en pool strip.
5. Quitar del pool → vuelve como candidato.

## Alineación Mapa geolocalización ↔ Ruta Trabajo

Ambos usan domicilio efectivo con geocode OK y resolución de distrito por FK o por polígono sobre lat/lng. M4 optimizado ya no depende del backfill Python previo al filtro.
