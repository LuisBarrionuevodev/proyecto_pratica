# Manifiesto — fuente EpiCollect (actas históricas)

**Ticket:** V1.1-MIG-ACTAS.0 (dry-run, sin escritura en DB)

## Fuente lógica

| Campo | Valor |
|--------|--------|
| Nombre lógico | `form-1__inspecciones-bromatologicas(1).csv` (export EpiCollect5 — inspecciones bromatológicas) |
| Ubicación local autorizada | `Backend/docs/private/migracion_historica/` (ignorada por Git) |
| Fecha de corte operativa | **2026-10-01** (filas con fecha de inspección **&lt;** corte son históricas; desde el 01/10/2026 Digitaliza es fuente oficial) |
| Herramienta de inventario | `Backend/scripts/inventariar_actas_historicas_epicollect.py` |

### Registro de corrida local (2026-10-12)

Fuente usada en dry-run de desarrollo: `docs/form-1__inspecciones-bromatologicas.csv` (mismo formulario; **no** versionada en Git).

| Métrica | Valor |
|---------|--------|
| SHA-256 | `144f1142544980d3c5ef04b55ae6c62b5e0f47d2bb99a73d4caccad9d230e00d` |
| Total filas leídas | 1491 |
| Total anterior al corte (`< 2026-10-01`) | 1443 |
| Formato de fecha detectado | `DD/MM/YYYY` (1491 filas) |
| Reinspecciones notificación vinculables | 147 |
| Reinspecciones no vinculables (→ `REVISAR`) | resto de casos con referencia ausente/ambigua |

Actualizar esta tabla si se reemplaza el archivo fuente entregado (`form-1__inspecciones-bromatologicas(1).csv`).

Ejemplo de comando (rutas fuera del repo):

```powershell
cd Backend
python scripts/inventariar_actas_historicas_epicollect.py `
  --input "C:\ruta-segura\form-1__inspecciones-bromatologicas(1).csv" `
  --cutoff-date 2026-10-01 `
  --output "C:\Users\pablo\Desktop\digitaliza-migracion\actas-dry-run"
```

## Columnas lógicas permitidas (lectura)

Solo se interpretan columnas de trazabilidad y clasificación. Se **ignoran** explícitamente columnas de fotos, videos, archivos y URLs (p. ej. prefijos `Foto`, `Video`, `https://`).

Listado canónico (ver también `ALLOWED_LOGICAL_COLUMNS` en código):

- `ec5_uuid`
- `1_Fecha_de_la_inspec`
- `2_Orden_de_Trabajo_N` (referencia histórica; **no** crea ODT)
- `3_Qu_inspectores_con`
- `4_Domicilio` (solo validación interna; no sale en artefactos)
- `5_Pudo_realizar_la_i`
- `6_Tipo_de_inspeccin`
- `8_Numero_de_la_Notif`
- `10_Se_dio_cumplimien`
- `14_Nombre_de_Fantasa`, `15_Razn_Socialnombre`, `16_DNI_del_Contribuy`, `17_Rubro` (no se exportan)
- Bloque actas: `80_`…`119_`, `251_Porque_no_realiz`, `255_Describe_porque_`
- Bloques repetidos en el mismo entry (reinspección): columnas `215_` en adelante para actas cuando el bloque primario está vacío

## Modelo objetivo (importación futura — V1.1-MIG-ACTAS.1)

```
Actuación histórica sin ODT
├── puede tener Notificación
├── puede tener Comprobación
│   ├── puede tener Clausura
│   └── puede tener Decomiso
└── puede ser origen de una reinspección posterior
```

Reglas fijadas para el ticket siguiente:

1. Una inspección o denuncia histórica puede generar **notificación y comprobación en la misma visita**.
2. Las notificaciones históricas **no** se importan huérfanas: siempre vinculadas a una actuación histórica sin ODT.
3. **Reinspección por notificación** solo si existe una notificación anterior importable/resoluble de forma **única** (`8_Numero_de_la_Notif` → acta de notificación previa).
4. **Reinspección por oficio** solo si existe una comprobación anterior identificable (número de acta o clave expediente+año+oficio única).
5. Las actuaciones históricas importadas **no** generan rutas, `iniciador_ruta`, alertas, pendientes ni trabajo operativo.
6. La carga histórica actual “solo comprobación” **no** se modifica en este ticket.

## Export enriquecido MySQL (V1.1-MIG-ACTAS.0C)

```powershell
cd Backend
python scripts/export_actas_historicas_enriquecidas.py `
  --output "$env:USERPROFILE\Desktop\digitaliza-migracion\fuente-mysql-enriquecida"
```

Genera `inventario_actas_historicas_enriquecido.csv` (PII solo local) y `resumen_export_actas_historicas_enriquecido.json` (sin PII). Solo `digitaliza_sandbox` en `localhost` / `127.0.0.1`.

## Conciliación MySQL (V1.1-MIG-ACTAS.0B)

Parámetro opcional `--legacy-inventory` apunta al CSV `inventario_actuaciones_digitaliza.csv` (fuera de Git). Genera `compatibilidad_inventario_mysql.json`, `resumen_conciliacion_legacy.json`, `vinculos_resueltos_legacy.csv` y `vinculos_conflictivos_legacy.csv`. El resumen de actas incluye `legacy_inventory_sha256` cuando aplica.

## Cadenas históricas (V1.1-MIG-ACTAS.0A)

El CLI genera además:

- `resumen_cadenas_historicas.json`
- `vinculos_confiables.csv`
- `vinculos_a_revisar.csv`

Cada reinspección recibe `estado_vinculo`, `tipo_origen_esperado`, `resultado_cadena_esperado` y `fuente_previa_uuid`. Solo `VINCULO_CONFIABLE` (referencia única + cronología + identidad por DNI/CUIT o domicilio+titular) habilita importación automática de cadena en el ticket siguiente.

## Decisiones del dry-run

| Decisión | Uso |
|----------|-----|
| `CANDIDATA_*` | Filas listas para revisión humana antes de importar |
| `REVISAR` | Referencia previa ausente/ambigua, fecha inválida, datos mínimos insuficientes |
| `EXCLUIR_POST_CORTE` | Fecha ≥ 2026-10-01 |
| `EXCLUIR_NO_OPERATIVA` | Sin tipo y sin visita realizable (p. ej. `5_Pudo_realizar_la_i` = NO) |

## Artefactos generados (fuera del repositorio)

- `resumen_actas_historicas.json`
- `candidatas_actuaciones_historicas.csv`
- `revisar_actas_historicas.csv`
- `excluidas_post_corte.csv`

Sin URLs ni datos personales en Git ni en stdout del CLI.
