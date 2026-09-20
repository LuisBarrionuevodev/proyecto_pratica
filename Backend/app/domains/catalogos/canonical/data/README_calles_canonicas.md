# Calles canónicas (`calles_canonicas.csv`)

## Contenido

- **734 entradas canónicas** aprobadas para Digitaliza.
- Una columna: `calles` (nombre canónico operativo).

## Origen

Derivado del snapshot revisado en `catalogos_digitaliza_revision.xlsx`, con
deduplicación de 4 pares alias y **exclusión explícita de 6 fixtures de test**
generados por `test_guardar_nomenclatura.py`:

- `CalleCat Canon *`
- `Main Canon *`
- `Esquina Canon *`

## Variantes no incluidas (decisión de catálogo)

Estas filas existen en DB como alias/variantes pero **no** son entradas
canónicas separadas en el CSV:

| Excluida (DB) | Conservada en CSV |
|---------------|-------------------|
| Dr Juan Brigido Teran | Avenida Dr Juan Brigido Teran |
| Avenida Ejercito del Norte | Ejercito del Norte |
| Pasaje Ernesto Padilla | Ernesto Padilla |
| Pasaje Independencia | Avenida Independencia |

## Reglas de identidad para seed/validación

1. Match primario por `nombre_key` (slug).
2. Fallback por `nombre_canonico` normalizado (ai_ci).
3. Soporte de keys legacy (ej. `Batalla de Chacabuco`, `gral jose maria paz`).
4. **`canon_base` no define identidad**: Pasaje Independencia ≠ Avenida Independencia.

## Nota sobre conteos DB

`EXPECTED_COUNTS["calles"] = 734` es la cantidad de **entradas canónicas**
esperadas, no `COUNT(*)` de `calle_catalogo`. La tabla puede tener filas
legacy/QA adicionales hasta la limpieza FASE 2.
