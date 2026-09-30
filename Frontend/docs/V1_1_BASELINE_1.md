# V1.1-BASELINE.1 — Baseline verificable del frontend

**Fecha:** 2026-09-30  
**Alcance:** `Frontend/` únicamente.

## Comandos ejecutados

```bash
cd Frontend
npm ci
npm run build
npm run lint
npm test
```

## Resultados

| Comando | Exit code | Resumen |
|---------|-----------|---------|
| `npm ci` | 0 | 692 paquetes auditados |
| `npm run build` | 0 | `tsc -b` + `vite build` OK |
| `npm run lint` | 1 | **260** problemas (**238** errors, **22** warnings) |
| `npm test` | 1 | **1664** passed, **23** failed · **226** files OK, **17** files failed (total **1687** tests en **243** archivos) |

### Build

- Producción compila sin errores TypeScript.
- Advertencia de chunk > 500 kB (existente, no bloqueante).

### Lint

- ESLint no está en verde en el repo: deuda acumulada (`no-explicit-any`, `no-unused-vars`, `react-hooks/exhaustive-deps`, `react-refresh/only-export-components`, etc.).
- **No se corrigió** en este ticket (fuera de alcance: sin rediseño masivo de lint).

### Tests (post arreglo de harness)

Antes del fix de Vitest, decenas de archivos `.tsx` fallaban con `ReferenceError: React is not defined` al usar `renderToStaticMarkup` sin transform JSX de React.

**Cambio de infraestructura:** `vitest.config.ts` hace `mergeConfig` con `vite.config.ts` para heredar `@vitejs/plugin-react`.

- **0** ocurrencias de `React is not defined` tras el cambio.
- Ejemplo recuperado: `src/components/crudDialog/crudDialog.test.tsx` (12 tests) pasa completo.

## Fallos pendientes (23 tests · 17 archivos)

| Archivo | Test (resumen) | Clasificación | Causa probable |
|---------|----------------|---------------|----------------|
| `src/api/notificacionesExportApi.test.ts` | conserva filtros documentales y distrito | PREEXISTENTE | API de export usa `motivoId` en lugar de `motivoQ` esperado por el test |
| `src/utils/cierreQa2.test.ts` | columna derecha flex slots | PREEXISTENTE | Test de string en fuente: `planificacionUrgentesSlotSx` ya no existe / renombrado |
| `src/utils/hotfixUiLayout.test.ts` | sidebar scrollbar oscuro | PREEXISTENTE | Tokens/CSS del sidebar migraron a variables semánticas |
| `src/utils/hotfixUrgentesGlobales.test.ts` | altura mínima shell lateral | PREEXISTENTE | Misma línea: expectativas de clases/sx antiguas |
| `src/utils/uxFiltrosNav2.test.ts` | 3 tests filtros Actuaciones | PREEXISTENTE | Copy/estructura del panel de filtros cambió vs. aserciones de texto |
| `src/Containers/Actuaciones/actuacionesUiConsistencia.test.tsx` | labels y validación filtros | PREEXISTENTE | UI de filtros actualizada; tests de snapshot textual desactualizados |
| `src/Containers/Mapa/MapPage.pr6c13.test.tsx` | PanelResumenOperativo solo realizados | PREEXISTENTE | Copy o composición del panel operativo |
| `src/Containers/Mapa/MapPage.pr6c14.test.tsx` | 3 tests subtabs geolocalización | PREEXISTENTE | Mockup/tabs o labels distintos a los esperados |
| `src/Containers/Mapa/MapPage.pr6c14b.test.tsx` | subtabs estilo Relevamientos | PREEXISTENTE | Tokens glass/tabs secundarios |
| `src/Containers/RutasTrabajo/frontPilot2.test.ts` | 2 tests InputStyles login | INTRODUCIDO / tema | Login usa tokens/CSS vars; tests buscan colores oscuros hardcodeados en `InputStyles` |
| `src/Containers/RutasTrabajo/operRutaFuncional2a.test.ts` | candidatos por distrito | PREEXISTENTE | Aserción de string en implementación de mapa/planificación |
| `src/Containers/RutasTrabajo/operRutaFuncional2b2.test.ts` | GeoJSON distrito caso F | PREEXISTENTE | Idem |
| `src/documentos/builders/buildRutaPublicadaDocumentModel.pr7_11.test.ts` | EstablecimientoSecundarioLine | PREEXISTENTE | Builder de documento sin el componente esperado en string |
| `src/Containers/ActasComprobacion/components/ComprobacionExpedienteOperativoDialog.test.tsx` | chrome CRUD glass | INTRODUCIDO | THEME-FINAL: modales usan `--d-surface-*`; test exige `rgba(255,255,255,0.04)` |
| `src/Containers/ActasComprobacion/components/ComprobacionOficioOperativoDialog.test.tsx` | chrome CRUD glass | INTRODUCIDO | Idem |
| `src/Containers/Actuaciones/utils/actuacionOficioSubmitPipeline.test.ts` | FIX.4.1 acta inspección | PREEXISTENTE | Validación no devuelve `fieldErrors.acta_inspeccion_num` como espera el test |
| `src/Containers/CargarRelevamientos/config/columnDefinitions.test.ts` | Glide header light | INTRODUCIDO | `bgHeader` ahora es `tableHeader` `#F6F8FB`, no `panelElevated` (LIGHT-VISUAL-FINAL) |

Ningún fallo restante se clasifica como **INFRAESTRUCTURA_TEST** tras el fix de Vitest.

## Cambios realizados en este ticket

1. **`Frontend/vitest.config.ts`** — `mergeConfig(vite.config, …)` para transformación JSX/React en tests.

## Riesgos para V1.1-RESP.1 (Responsive)

1. **Lint en rojo (238 errors):** no bloquea build ni la mayoría de tests, pero CI futura con `eslint --max-warnings 0` fallaría sin plan de deuda.
2. **23 tests rojos:** mayoría son tests de regresión textual (mapa, rutas, filtros); conviene triage antes de refactors responsive amplios para no confundir roturas nuevas.
3. **Tests de tema desactualizados** (CRUD glass, Glide header, login InputStyles): alinear expectativas con tokens `--d-*` en un ticket de QA de tema, no en responsive.
4. **Build estable:** base sólida para trabajo responsive; no hay bloqueo de compilación.

## Reproducibilidad

En máquina de desarrollo (Windows, Node/npm del proyecto):

```bash
cd Frontend && npm ci && npm run build && npm run lint; npm test
```

Última corrida documentada: 2026-09-30 (~32.9 s suite de tests tras fix harness).
