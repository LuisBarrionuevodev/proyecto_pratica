# CargarActuaciones - Batch Grid

## Descripción

Componente de carga masiva de actuaciones con validación en vivo y commit por batch.

## Características

### 1. Sistema de Batch
- **Iniciar Batch**: Crea un nuevo batch en el backend y obtiene un `batch_id`
- **Validar Todo**: Envía todas las filas al endpoint `/grid/validate-batch` para validación masiva
- **Confirmar Carga**: Persiste todas las filas válidas (OK) usando `/grid/commit-batch` o iterando `/grid/commit-row`

### 2. Validación en Vivo
- Al editar cualquier celda, se activa un debounce de 500ms
- Después del debounce, se llama automáticamente a `/grid/validate-row`
- El estado de la fila se actualiza según la respuesta:
  - ✅ **OK**: Fila válida (fondo verde claro)
  - ❌ **ERROR**: Fila con errores (fondo rojo claro, errores visibles)
  - ⏳ **PENDIENTE**: Fila sin validar (fondo blanco)

### 3. Columnas

El grid incluye 33 columnas en total:

**Columnas de sistema:**
- Estado (chip con color)
- Errores (tooltip con detalles)
- ID (auto-asignado tras commit)

**Columnas de datos (con espacios, tal como las espera el backend):**
1. Fecha actuación
2. Tipo actuación
3. Contraproducencia
4. Orden de trabajo
5. Inspector 1, 2, 3
6. Calle
7. Número
8. Rubro
9. Apellido
10. Nombre
11. DNI
12. Acta inspección
13. Acta notificación
14. Motivo notif 1, 2, 3
15. Acta comprobación
16. Motivo comprobación
17. Acta clausura
18. Acta decomiso
19. Kilos decomiso
20. Acta notificación previa
21. Acta comprobación previa
22. Expediente año
23. Expediente número
24. Oficio año
25. Oficio número
26. Oficio causa

### 4. API Grid (`src/api/gridApi.ts`)

Endpoints disponibles:

```typescript
// Iniciar batch
startBatch(): Promise<{ batch_id: string }>

// Validar una fila
validateRow(request: {
  batch_id: string;
  row_id: string;
  row: GridRow;
}): Promise<ValidateRowResponse>

// Validar múltiples filas
validateBatch(request: {
  batch_id: string;
  rows: Array<{ row_id: string; row: GridRow }>;
}): Promise<ValidateBatchResponse>

// Confirmar una fila
commitRow(request: {
  batch_id: string;
  row_id: string;
  row: GridRow;
}): Promise<CommitRowResponse>

// Confirmar múltiples filas (con fallback automático)
commitBatch(request: {
  batch_id: string;
  rows: Array<{ row_id: string; row: GridRow }>;
}): Promise<CommitBatchResponse>
```

### 5. Tipos TypeScript

```typescript
interface GridRow {
  // Metadata interna
  _rowId?: string;
  _state?: "PENDIENTE" | "OK" | "ERROR";
  _errors?: string;
  _normalized?: GridRow;

  // Columnas de datos (con espacios)
  "ID"?: number | null;
  "Fecha actuación"?: string | null;
  "Tipo actuación"?: string | null;
  // ... (todas las columnas del modelo)
}
```

## Flujo de Trabajo

1. **Usuario hace clic en "Iniciar Batch"**
   - Se llama a `/grid/start`
   - Se guarda el `batch_id` en el estado
   - Los botones "Validar Todo" y "Confirmar Carga" se habilitan

2. **Usuario agrega filas y edita celdas**
   - Cada fila nueva tiene estado `PENDIENTE`
   - Al editar, se valida automáticamente después de 500ms
   - El estado cambia a `OK` o `ERROR`

3. **Usuario hace clic en "Validar Todo" (opcional)**
   - Se envían todas las filas al backend
   - Se actualizan todos los estados simultáneamente

4. **Usuario hace clic en "Confirmar Carga"**
   - Solo se envían las filas con estado `OK`
   - Si el commit es exitoso, se asigna el ID a la fila
   - Las filas con error permanecen en el grid para corrección

## Comportamiento de Errores

### Errores por celda
Los errores del backend vienen en formato:
```json
{
  "errors": {
    "Orden de trabajo": "No existe",
    "Rubro": "No encontrado"
  }
}
```

Se concatenan y muestran en la columna "Errores" con tooltip completo.

### Errores globales
Los errores de red o del servidor se muestran en un `Alert` en la parte superior del grid.

## Personalización

### Cambiar debounce de validación
```typescript
debounceRef.current[rowId] = window.setTimeout(() => {
  handleValidateRow(updatedRow);
}, 500); // ← Cambiar aquí (en milisegundos)
```

### Cambiar colores de estado
```typescript
const getRowStyle = (row: MRT_Row<GridRow>) => {
  const state = row.original._state;
  if (state === "ERROR") {
    return { backgroundColor: "#ffebee" }; // ← Cambiar aquí
  }
  // ...
};
```

## Dependencias

- `material-react-table` (ya instalado)
- `@mui/material` (ya instalado)
- `axios` (para API, ya instalado)

**No se agregaron dependencias nuevas.**
