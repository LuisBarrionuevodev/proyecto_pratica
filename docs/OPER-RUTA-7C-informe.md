# OPER-RUTA.7C — Reacondicionamiento visual Planificación tipo My Maps

## Resumen

Reacondicionamiento **solo frontend** de la pantalla Planificación (paso 1 del flujo de 3). Sin cambios de backend, endpoints ni reglas de negocio.

## Layout anterior vs nuevo

| Antes | Después (7C) |
|-------|----------------|
| 3 columnas: candidatos \| mapa \| urgentes+pool | 2 columnas: **panel lateral (lg 4)** \| **mapa amplio (lg 8)** |
| KPI cards en franja horizontal arriba | KPIs como **chips de tipo** en barra de filtros |
| Filtros duplicados por panel | **Filtros unificados** visibles arriba del sidebar |
| Urgentes y pool apilados a la derecha | **Tabs**: Candidatos · Urgentes · Pool · Resumen |
| «Continuar» solo en pool | **Acción rápida** fija al pie del sidebar |

## Componentes nuevos

| Archivo | Rol |
|---------|-----|
| `planificacionMyMapsLayout.ts` | Tokens layout (altura compartida, shell sidebar, scroll) |
| `PlanificacionSidebarPanel.tsx` | Panel lateral unificado con tabs |
| `PlanificacionFiltrosBar.tsx` | Distrito + tipo + rubro + búsqueda + chips activos |
| `PlanificacionResumenPanel.tsx` | Tab resumen operativo (pool/grupo/candidatos/urgentes) |
| `PlanificacionTipoFilterChips.tsx` | KPIs compactos clicables |
| `PlanificacionActiveFiltersChips.tsx` | Chips de filtros activos |

## Paneles refactorizados

`PendientesContextoPanel`, `UrgentesPanel`, `PoolDelDiaPanel` soportan `variant="embedded"` para uso dentro del sidebar sin paper/títulos/filtros duplicados.

## Qué ve el usuario

1. **Distrito activo** como chip (se elige en el mapa).
2. **Tipo** (Total, Alta, Oficios, etc.) como chips con contadores.
3. **Rubro + buscar domicilio** siempre visibles.
4. **Chips de filtros activos** debajo.
5. **Tabs** para alternar candidatos, urgentes, pool y resumen.
6. **Mapa más ancho** a la derecha (pines sin cambios — pines rojos quedan para 7E).

## Sin tocar

- Asignación (paso 2) y mapa final (paso 3).
- Backend M4/M3, publicar, PR11/PR12, geocode, exports, indicadores.
- Pines rojos, línea de ruta, algoritmo de ordenamiento.

## Tests

```bash
npx tsc --noEmit
npx vitest run RutasTrabajo operRuta7c hotfixUiLayout hotfixUrgentesGlobales scrollHotfix
```

## QA manual sugerido

1. Abrir Ruta Trabajo → Planificación con borrador.
2. Confirmar layout: panel izquierdo + mapa amplio derecho.
3. Elegir distrito en mapa → chip distrito + candidatos en tab.
4. Filtrar por tipo/rubro/domicilio → chips activos + mapa/lista coherentes.
5. Tab Urgentes → filtros urgentes + lista paginada.
6. Agregar al pool → desaparece de candidatos; tab Pool muestra ítem.
7. Tab Resumen → totales pool libre / en grupo / urgentes.
8. «Continuar a asignación» al pie del sidebar (habilitado con pool > 0).
9. Responsive xs: panel arriba, mapa abajo.
