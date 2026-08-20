# OPER-RUTA.7F.1 — Reducir refetch innecesario M4/M3 al mutar pool

> **Alcance:** solo frontend planificación. Sin cambios backend.  
> **Fecha:** 2026-08-20

---

## 1. Effects/refetch que disparaban M4/M3 (antes)

| Trigger | M4 | M3 |
|---------|----|----|
| `poolIniciadorKey` cambia (agregar/quitar pool) | **Sí** — effect `[distritoActivoId, rutaId, poolIniciadorKey]` | **Sí** — effect `[loadUrgentes, poolIniciadorKey]` |
| Cambio distrito | Sí | No |
| Montaje / cambio `rutaId` | Sí (si distrito) | Sí |

El refetch existía para ocultar candidatos ya en pool, pero **6I/6J + `sinPool` / `filtrarUrgentesVisibles`** ya lo resolvían en cliente. El backend M4 (7B) además excluye agregables server-side.

---

## 2. Mutaciones con actualización local (después)

| Mutación | Pool | M4 candidatos/pins | M3 urgentes |
|----------|------|-------------------|-------------|
| Agregar al pool | `refreshPool` silent | Oculto vía `sinPool` | Oculto vía `filtrarUrgentesVisibles` |
| Quitar del pool | `refreshPool` silent | Reaparece si estaba en `pendientesMapaRaw` | Reaparece si estaba en `urgentesRaw` |
| Agregar desde mapa | igual | pin desaparece (sinPool) | igual |
| Quitar ítem grupo | `syncPoolTrasQuitarItem` | sin refetch M4 | sin refetch M3 |
| Eliminar grupo | refresh borrador + pool silent | sin refetch M4 | sin refetch M3 |

---

## 3. Cuándo se refresca M4

- Selección de **distrito** (`loadPendientesMapa` en effect).
- Cambio de **ruta** (`rutaId` en `loadPendientesMapa`).
- **Manual:** `refreshPendientesMapa` (expuesto; sin botón UI hoy).

**No** al mutar pool.

---

## 4. Cuándo se refresca M3

- **Montaje** y cambio de **ruta** (`loadUrgentes(1, 25)`).
- **Filtros urgentes** (`aplicarFiltrosUrgentes` / `limpiarFiltrosUrgentes`).
- **Paginación** (`onPageChange` en `UrgentesPanel`).

**No** al mutar pool.

---

## 5. Archivos tocados

| Archivo | Cambio |
|---------|--------|
| `planificacion/hooks/usePlanificacionController.ts` | Quitado `poolIniciadorKey`; `loadPendientesMapa`; M3 solo `[rutaId]` |
| `hooks/useRutaPoolDiaBackend.ts` | `quitarDelPool` → `refreshPool` silent |
| `planificacion/selectors/planificacionSelectors.ts` | Comentario 7F.1 |
| `operRuta6i.test.ts`, `operRuta6j.test.ts` | Expectativas actualizadas |
| `operRuta7f1.test.ts` | **Nuevo** — 8 tests estáticos + selectors |

---

## 6. Tests ejecutados

```bash
npx tsc --noEmit
npx vitest run operRuta7f1
npx vitest run operRuta6i
npx vitest run operRuta6j
npx vitest run RutasTrabajo
```

Backend: no tocado.

---

## 7. QA manual (checklist)

1. Abrir Ruta Trabajo → seleccionar distrito → M4 rápido (~0.5s post-7B).
2. Agregar candidato al pool → desaparece pin/lista; aparece en pool; **sin spinner largo** en mapa/urgentes.
3. Quitar del pool → sale del pool; candidato/urgente reaparece si aún en dataset local; sin congelar UI.
4. Quitar ítem / eliminar grupo → pool/grupos sync; sin recarga M3.

---

## 8. Confirmación de alcance

No se tocó: backend M4 7B, M3 backend, publicar, Completar Trabajo, PR11/PR12, geocode, exports, indicadores, pines rojos, My Maps.
