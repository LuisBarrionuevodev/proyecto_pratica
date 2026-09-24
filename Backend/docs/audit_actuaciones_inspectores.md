# Inventario PR A — Inspectores en actuaciones (riesgo grilla vs DB)

## Fuente de verdad en base

- Tabla puente **`actuaciones_inspector`**: relación N:M entre `actuaciones` e `inspector`.
- Solo enlaces con **`deleted_at IS NULL`** cuentan como inspectores **activos** (misma regla que mapas/indicadores).

No hay límite de tres filas en el esquema: pueden existir 4+ inspectores por actuación.

## Dónde está el límite de 3 (canal grilla)

| Pieza | Comportamiento |
|-------|----------------|
| `ActuacionGridRowIn` | Campos `inspector1`, `inspector2`, `inspector3` |
| `map_actuacion_row` | Arma `"inspectores": [i1, i2, i3]` sin vacíos → **como mucho 3 nombres** |
| Presenter `actuacion_to_grid_row` | Rellena columnas 1–3 con los **tres primeros** inspectores (orden por `id`); el texto completo va en `inspectores_texto` |

**Riesgo:** si en DB hay **más de 3** inspectores y el usuario guarda desde la grilla, el PUT puede mandar solo los tres primeros nombres y **sobrescribir** la relación, **perdiendo** el 4º en adelante (salvo que el payload traiga una lista completa en un futuro contrato).

## Herramientas de diagnóstico

### 1. Comando Flask (recomendado)

Desde la carpeta `Backend`, con `FLASK_APP=run.py` y la misma `SQLALCHEMY_DATABASE_URI` que producción/staging:

```bash
python -m flask audit-inspectores-actuaciones
```

Opcional:

```bash
python -m flask audit-inspectores-actuaciones --max-ids 500
```

Salida JSON con:

- `con_mas_de_3_inspectores`: cuántas actuaciones tienen **>3** inspectores activos
- `actuacion_ids_mas_de_3` / `detalle_mas_de_3`: ids y cantidades
- `buckets_por_cantidad`: distribución 1 / 2 / 3 / 4+ por actuación (solo filas con ≥1 inspector)
- `max_inspectores_por_actuacion`

### 2. SQL directo (MySQL)

Ver `scripts/sql/audit_actuaciones_inspectores_mas_de_3.sql`.

## Salvaguarda temporal (este PR)

- **`log_truncation_risk_if_applicable`** en `aplicar_payload_actuacion`: si la actuación **ya tenía >3** inspectores activos y el payload trae **≤3** nombres, se emite un **WARNING** en el log del servidor (no bloquea el guardado).

Motivo: una reducción de 5→2 inspectores también dispara el warning; hay que interpretar el log en contexto. El objetivo es **visibilidad** hasta tener contrato/lista completa o reglas explícitas.

## Próximo PR estructural (fuera de este alcance)

- Exponer y persistir **`inspectores[]` completo** en el canal grilla (o endpoint dedicado) cuando `con_mas_de_3_inspectores > 0`, y/o bloquear guardado grilla con error claro hasta migrar datos.
