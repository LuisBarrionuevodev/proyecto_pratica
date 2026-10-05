# V1.1-QA-RELEASE.1 — Cierre técnico y operativo V1.1

**Fecha:** 2026-10-04  
**Commit referencia (`main` local):** `4d9185df958c1655648ee0ad8a78241ec05460b3` — `V1.1-RELEVAMIENTO-ROLE.1`  
**Entorno de corrida:** Windows 10, Node/npm del proyecto, Python 3.13, MySQL local (dev `digitaliza_sandbox` migrado en `v2w3x4y5z6a7`).

**Veredicto de cierre automatizado:** **NO CERRAR** release solo con esta evidencia. Hay **regresiones V1.1** en tests de frontend (Panel, Completar trabajo, Media) respecto al baseline documentado. Abrir hotfix(s) separados; este ticket solo documenta.

---

## 1. Reproducibilidad local

### Frontend

Comandos (copia con `npm ci` previo):

```bash
cd Frontend
npm ci
npm run build
npm run lint
npm test
```

| Comando | Exit code | Resumen |
|---------|-----------|---------|
| `npm ci` | **0** | 692 paquetes instalados (warnings peer deps / audit npm) |
| `npm run build` | **0** | `tsc -b` + `vite build` OK (~14 s) |
| `npm run lint` | **1** | **265** problemas (**240** errors, **25** warnings) |
| `npm test` | **1** | **1779** passed, **70** failed · **259** archivos OK, **27** archivos con fallos (**1849** tests en **286** archivos, ~34 s) |

**Comparación con baseline** [`V1_1_BASELINE_1.md`](./V1_1_BASELINE_1.md) (2026-09-30):

| Métrica | Baseline | QA Release 1 | Δ |
|---------|----------|--------------|---|
| `npm run lint` exit | 1 | 1 | Sin cambio de política (deuda histórica) |
| Problemas lint | 260 | 265 | +5 (ruido, no bloqueante por alcance) |
| Tests failed | 23 | **70** | **+47** |
| Tests passed | 1664 | 1779 | +115 (más tests en suite) |
| Archivos test fallidos | 17 | **27** | +10 |

### Backend

```bash
cd Backend
pytest
```

| Escenario | Exit code | Resumen |
|-----------|-----------|---------|
| `pytest` sin `openpyxl` | **2** | Error de **colección**: `tests/test_export_catalogos_actuales.py` → `ModuleNotFoundError: openpyxl` (`openpyxl` **no** está en `requirements.txt`) |
| `pytest` tras `pip install openpyxl` contra DB dev sin aislamiento test | **1** | Cientos de **FAILED** + **ERROR** (fixtures DB / esquema / datos; no representa CI sana) |
| Subconjunto focal V1.1 (MySQL dev migrado, `scope_fixture`) | **0** | `test_relevamiento_role_v1_1.py` + `test_hotfix_relevador_role.py` + `test_media_storage_1a.py` → **19** passed |

**Procedimiento canónico** (ver `Backend/TESTING.md`): `TEST_DATABASE_URL` → `digitaliza_test`, `python scripts/migrate_test_db.py`, luego `pytest`. Esta corrida de release **no** ejecutó suite completa en `digitaliza_test` (fuera de alcance corregir entorno).

**Alembic local (dev):**

```bash
cd Backend
$env:FLASK_APP="run.py"
python -m flask db current
# → v2w3x4y5z6a7 (head)
```

### Tests focalizados V1.1 (verde en esta corrida)

```bash
cd Frontend
npm test -- --run \
  src/auth/relevamientoRole.test.ts \
  src/Containers/Actuaciones/actuacionesGestionPagination.test.ts \
  src/Containers/Actuaciones/actuacionesGestionResponsive.test.ts

cd Backend
python -m pytest tests/test_relevamiento_role_v1_1.py \
  tests/test_hotfix_relevador_role.py tests/test_media_storage_1a.py -q
```

Frontend: **11/11** passed. Backend focal: **19/19** passed.

---

## 2. Triage de deuda (estricto)

### A. Regresión V1.1 — corregir antes de cerrar release

| Archivo | Fallos | Causa probable | Área V1.1 |
|---------|--------|----------------|-----------|
| `src/Containers/Dashboard/Components/Panel.test.tsx` | 17/19 | `Panel.tsx` usa `useAppSession()`; tests renderizan sin `AppSessionProvider` → `useAppSession debe usarse dentro de AppSessionProvider` | Indicadores / IND-QA |
| `src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.test.tsx` | 16/16 | Mismo patrón de harness o cambios MEDIA.1B (galerías / copy) sin actualizar tests | Completar trabajo + Media |
| `src/features/media/ActuacionMediaGallery.test.tsx` | 3/3 | Tests de galería no alineados con componentes/pipeline Media V1.1 | Media |
| `src/Containers/Actuaciones/Components/ActuacionDetalleDialog.seguimiento1d.test.tsx` | 2/3 | Seguimiento acta / toggles carnet vs. comportamiento actual del diálogo | Acta seguimiento |
| `src/Containers/Actuaciones/Components/ActuacionDetalleDialog.test.tsx` | 1/25 | Edición domicilio: expectativa de copy/UI desactualizada | Actuaciones CRUD |
| `src/theme/frontProd5.test.ts` | 1/6 | Flujo “Mandar todo” / commit Glide vs. implementación actual | Carga grid |
| `src/utils/stab10b.test.ts` | 2/8 | Análisis estático mapa operativo desactualizado | Mapa |
| `src/utils/hotfixReencoladoContraproducencia.test.ts` | 1/3 | String/assert en mapper frontend desactualizado | Actuaciones |
| `src/Containers/GestionNotificacion/gestionNotificacionOperRuta6c.test.tsx` | 1/6 | Aserción de fuente desactualizada | Notificaciones |
| `src/Containers/GestionNotificacion/gestionNotificacionOperRuta6d.test.tsx` | 1/5 | Idem | Notificaciones |

**Acción:** hotfix dedicado (harness `AppSessionProvider` en tests de Panel/Modal; alinear tests Media y seguimiento). **No** mezclar con este ticket de documentación.

### B. Preexistente — ya en baseline o deuda textual/tema

| Archivo | Fallos | Notas |
|---------|--------|-------|
| `src/api/notificacionesExportApi.test.ts` | 1 | Baseline: `motivoId` vs `motivoQ` |
| `src/utils/uxFiltrosNav2.test.ts` | 3 | Baseline: panel filtros Actuaciones |
| `src/utils/hotfixUiLayout.test.ts` | 1 | Baseline: scrollbar sidebar |
| `src/utils/hotfixUrgentesGlobales.test.ts` | 1 | Baseline: shell lateral |
| `src/Containers/Actuaciones/actuacionesUiConsistencia.test.tsx` | 2 | Baseline: labels filtros |
| `src/Containers/Mapa/MapPage.pr6c11.test.tsx` | 1 | Baseline familia mapa |
| `src/Containers/Mapa/MapPage.pr6c13.test.tsx` | 3 | Baseline |
| `src/Containers/Mapa/MapPage.pr6c14.test.tsx` | 3 | Baseline |
| `src/Containers/Mapa/MapPage.pr6c14b.test.tsx` | 1 | Baseline |
| `src/Containers/RutasTrabajo/frontPilot2.test.ts` | 2 | Baseline / tema login |
| `src/Containers/RutasTrabajo/operRutaFuncional2a.test.ts` | 1 | Baseline |
| `src/Containers/RutasTrabajo/operRutaFuncional2b2.test.ts` | 1 | Baseline |
| `src/documentos/builders/buildRutaPublicadaDocumentModel.pr7_11.test.ts` | 1 | Baseline |
| `src/Containers/ActasComprobacion/components/ComprobacionExpedienteOperativoDialog.test.tsx` | 1 | Baseline: tokens CRUD glass |
| `src/Containers/ActasComprobacion/components/ComprobacionOficioOperativoDialog.test.tsx` | 1 | Baseline |
| `src/Containers/Actuaciones/utils/actuacionOficioSubmitPipeline.test.ts` | 1 | Baseline FIX.4.1 |
| `src/Containers/CargarRelevamientos/config/columnDefinitions.test.ts` | 1 | Baseline: `bgHeader` `#F6F8FB` vs `panelElevated` |

Ticket posterior sugerido: **V1.1-TEST-DEUDA.1** (tema + mapa + filtros), sin mezclar con release.

### C. Infra / entorno

| Ítem | Clasificación | Detalle |
|------|---------------|---------|
| `npm run lint` en rojo | Preexistente / política | 240+ errores históricos; fuera de alcance release |
| `pytest` sin `openpyxl` | Infra | Dependencia usada en test no declarada en `requirements.txt` |
| `pytest` completo sin `TEST_DATABASE_URL` | Infra | Ver `Backend/TESTING.md`; errores masivos en fixtures de integración |
| `npm audit` vulnerabilidades | Infra | 37 reportadas en `npm ci`; no evaluadas en este ticket |
| Smoke producción 4 roles | Infra / manual | Requiere cuentas y URLs de producción (sección 3) |
| Railway cron / commit deploy | Infra / manual | Sin acceso CLI Railway en esta corrida (sección 4) |

---

## 3. Smoke de producción (checklist manual)

Ejecutar en **producción** (o staging espejo) con cuentas dedicadas. Marcar OK/FAIL y capturas en herramienta interna.

### Auth responsive

- [ ] Login 375px / 768px / desktop — sin overflow horizontal
- [ ] Recuperar contraseña — branding `TextDigitaliza`, inputs 16px móvil
- [ ] Perfil — cambio de contraseña / datos sesión

### ADMIN / USUARIO

- [ ] Cargar relevamiento (grid + commit)
- [ ] Gestión relevamientos — pendientes / realizados, edición según flujo
- [ ] Actuaciones desktop + móvil (cards, paginación, CRUD modal)

### INSPECTOR (`relevador`)

- [ ] Completar mis trabajos
- [ ] Mis actuaciones (solo GET listado propio)
- [ ] Mis indicadores (allow-list)
- [ ] Mi mapa operativo
- [ ] URL/API cruzadas → **403** (`/actuaciones` POST, `/relevamientos`, `/api/admin/users`, etc.)

### RELEVAMIENTO (`relevamiento`)

- [ ] Inicio — solo cards permitidas
- [ ] Cargar relevamientos → login redirige aquí
- [ ] Gestión relevamientos — **sin** pestaña Denuncias
- [ ] Perfil
- [ ] API prohibidas → **403** con `No tiene permisos para esta acción`: Actuaciones, Rutas, Indicadores, Mapa, Denuncias, Usuarios

### Media (cuenta con permiso de carga en completar trabajo)

- [ ] Subida con progreso
- [ ] Miniaturas imagen sin barra de nombre; PDF con barra mínima
- [ ] Zoom / agregado / borrado
- [ ] URL firmada: sin JWT/cookie de otro usuario → no descarga; expiración si aplica

### Consola navegador

- [ ] Sin errores críticos (4xx/5xx repetidos, excepciones React) en flujos anteriores

---

## 4. Railway

Checklist operador (pendiente confirmación en entorno Railway):

| Verificación | Comando / acción | Resultado esperado | Estado corrida |
|--------------|------------------|--------------------|----------------|
| Migración HEAD | `FLASK_APP=run.py flask db current` en servicio web | `v2w3x4y5z6a7 (head)` | **OK local**; **pendiente prod** |
| Commit desplegado | Comparar SHA servicio con `main` | `4d9185d` o posterior en `main` | **Pendiente** |
| Cron `cleanup-pending-media` | Primer run servicio cron (`0 5 * * *`, ver `railway.toml` / `Backend/docs/ops_cleanup_pending_media.md`) | Termina OK; **no** levanta Gunicorn | **Pendiente** |
| Health | `GET /health` | 200 | **Pendiente** |

`startCommand` del servicio web incluye `flask db upgrade` antes de Gunicorn (`Backend/railway.toml`).

---

## 5. Entregables de este ticket

- [x] Documento `Frontend/docs/V1_1_QA_RELEASE_1.md`
- [ ] Cierre de release **bloqueado** hasta hotfix de regresiones sección 2.A
- [ ] Smoke producción y Railway — ejecución manual pendiente

**Evidencia cruda** (no commitear): `Frontend/docs/_qa_vitest_output.txt`, `_qa_pytest_summary.txt` generados localmente; pueden borrarse tras revisión.

---

## 6. Referencias

- Baseline frontend: [`V1_1_BASELINE_1.md`](./V1_1_BASELINE_1.md)
- Tests backend aislados: [`Backend/TESTING.md`](../../Backend/TESTING.md)
- Rol Relevamiento: commit `4d9185d`, migración `v2w3x4y5z6a7`
- Cron media: [`Backend/docs/ops_cleanup_pending_media.md`](../../Backend/docs/ops_cleanup_pending_media.md)
