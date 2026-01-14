# Endpoint Faltante: POST /grid/commit-batch

## Estado Actual

El frontend ya está preparado para usar este endpoint, pero actualmente no existe en el backend.
**Fallback automático**: El frontend detecta el 404 y automáticamente hace commit individual con `/commit-row`.

## Implementación Requerida

### Endpoint
```
POST /api/v1/grid/commit-batch
```

### Request Schema

```python
class CommitBatchRequest(BaseModel):
    batch_id: UUID
    rows: List[CommitRowItem]

class CommitRowItem(BaseModel):
    row_id: str = Field(..., min_length=1)
    normalized: Dict[str, Any]  # Payload canon ya validado
```

### Response Schema

```python
class CommitBatchResponse(BaseModel):
    batch_id: UUID
    results: List[CommitRowResponse]
```

### Implementación Sugerida

Agregar al archivo `Backend/app/domains/grid/routes/batch.py`:

```python
@grid.post("/commit-batch")
def commit_batch():
    """
    Persiste múltiples filas en una sola petición.
    
    Ventajas:
    - Reduce latencia (1 request vs N requests)
    - Permite transacción atómica (opcional)
    - Mejor rendimiento para batches grandes
    
    Comportamiento:
    - Itera sobre cada fila y llama a crear_actuacion_desde_payload o actualizar_actuacion
    - Si una fila falla, marca ok=false con errors, pero continúa con las demás
    - Retorna lista de resultados (CommitRowResponse por cada fila)
    """
    try:
        data = request.get_json(force=True)
        req = CommitBatchRequest.model_validate(data)
    except ValidationError as e:
        return jsonify({"detail": "Validation error", "errors": pydantic_errors_to_cell_map(e)}), 422
    except Exception as e:
        return jsonify({"detail": "Invalid JSON", "error": str(e)}), 400

    results = []
    for item in req.rows:
        normalized = item.normalized or {}
        act_id = normalized.get("id")

        try:
            if act_id is None:
                act = crear_actuacion_desde_payload(normalized)
            else:
                act = actualizar_actuacion(int(act_id), normalized)

            results.append(CommitRowResponse(
                batch_id=req.batch_id,
                row_id=item.row_id,
                ok=True,
                errors={},
                persisted=actuacion_to_grid_row(act),
            ))
        except ValueError as e:
            results.append(CommitRowResponse(
                batch_id=req.batch_id,
                row_id=item.row_id,
                ok=False,
                errors={"detail": str(e)},
                persisted=None,
            ))

    resp = CommitBatchResponse(batch_id=req.batch_id, results=results)
    return jsonify(resp.model_dump()), 200
```

### Schema Adicional Requerido

Agregar a `Backend/app/domains/grid/schemas/batch.py`:

```python
class CommitRowItem(BaseModel):
    """Item para commit batch: row_id y normalized payload."""
    row_id: str = Field(..., min_length=1)
    normalized: Dict[str, Any]

class CommitBatchRequest(BaseModel):
    batch_id: UUID
    rows: List[CommitRowItem]

class CommitBatchResponse(BaseModel):
    batch_id: UUID
    results: List[CommitRowResponse]
```

## Testing

Una vez implementado, probar desde el frontend:

1. Iniciar batch
2. Agregar varias filas
3. Validar todo
4. Click en "Confirmar Carga"
5. Verificar que usa `/commit-batch` (no fallback a commit-row)
6. Revisar que los IDs se asignan correctamente

## Beneficios de Implementar

✅ **Rendimiento**: 1 request HTTP en lugar de N
✅ **Latencia**: Menor tiempo total de commit
✅ **UX**: Usuario ve resultado más rápido
✅ **Opcional transacciones**: Si una falla, rollback de todas (requiere db.session manejo)

## Alternativa: Mantener Fallback

Si no se implementa, el frontend seguirá usando el fallback automático (commit-row iterativo).
**Funciona perfectamente**, solo es más lento para batches grandes (10+ filas).
