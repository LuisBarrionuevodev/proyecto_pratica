# Guía de Estilización Avanzada - Glide Data Grid

## ✅ Implementación Actual

Ya tienes implementado `TablaCargarActuacionesGlide.tsx` con:

- ✅ **Edición inline** de todas las columnas
- ✅ **Validación con debounce** al editar celdas
- ✅ **Estados visuales** (OK verde, ERROR rojo, PENDIENTE naranja)
- ✅ **Tema personalizado** con colores modernos
- ✅ **Columnas congeladas** (freeze primeras 3 columnas)
- ✅ **Altura de filas** personalizada
- ✅ **Integración completa** con tu lógica de batch del backend

## 🎨 Estilos Avanzados Disponibles (Como en la Imagen)

Glide Data Grid **SÍ permite** crear estilos como la imagen que mostraste. Aquí están las opciones:

### 1. **Badges/Pills** (Como los nombres de managers)

```typescript
// En getCellContent, para una columna de tipo badge:
if (columnId === "Inspector 1") {
    return {
        kind: GridCellKind.Text,
        data: value,
        displayData: value,
        allowOverlay: false,
        themeOverride: {
            bgCell: "#e3f2fd",
            textDark: "#1565c0",
            borderColor: "#90caf9",
        },
        style: "faded", // Estilo con fondo redondeado
    };
}
```

### 2. **Checkboxes/Boolean Cells**

```typescript
if (columnId === "Opt-In") {
    return {
        kind: GridCellKind.Boolean,
        data: value === true || value === "true",
        allowOverlay: false,
    };
}
```

### 3. **Imágenes/Fotos de Perfil**

```typescript
if (columnId === "Photo") {
    return {
        kind: GridCellKind.Image,
        data: [value], // URL de la imagen
        displayData: [value],
        allowOverlay: false,
        allowAdd: false,
    };
}
```

### 4. **Celdas URI/Links**

```typescript
if (columnId === "More Info") {
    return {
        kind: GridCellKind.Uri,
        data: value,
        displayData: "Ver más",
        allowOverlay: false,
        hoverEffect: true,
    };
}
```

### 5. **Custom Cells - Gráficos de Performance**

Para gráficos como los de la imagen, necesitas crear un **Custom Renderer**:

```typescript
// customRenderers/PerformanceChart.ts
import { CustomCell, CustomRenderer, GridCellKind } from "@glideapps/glide-data-grid";

interface PerformanceChartProps {
    readonly kind: "performance-chart";
    readonly values: number[]; // Array de valores para el gráfico
    readonly color?: string;
}

export type PerformanceChartCell = CustomCell<PerformanceChartProps>;

export const performanceChartRenderer: CustomRenderer<PerformanceChartCell> = {
    kind: GridCellKind.Custom,
    isMatch: (c): c is PerformanceChartCell => 
        (c.data as any).kind === "performance-chart",
    draw: (args, cell) => {
        const { ctx, rect, theme } = args;
        const { values, color } = cell.data;

        if (!values || values.length === 0) return;

        const padding = 8;
        const chartWidth = rect.width - padding * 2;
        const chartHeight = rect.height - padding * 2;
        const stepX = chartWidth / (values.length - 1);

        // Normalizar valores
        const maxVal = Math.max(...values);
        const minVal = Math.min(...values);
        const range = maxVal - minVal || 1;

        // Dibujar línea
        ctx.beginPath();
        ctx.strokeStyle = color || theme.accentColor;
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        values.forEach((val, i) => {
            const x = rect.x + padding + i * stepX;
            const normalizedVal = (val - minVal) / range;
            const y = rect.y + padding + chartHeight - normalizedVal * chartHeight;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();
    },
};

// Uso en getCellContent:
if (columnId === "Performance") {
    return {
        kind: GridCellKind.Custom,
        allowOverlay: false,
        copyData: "Performance data",
        data: {
            kind: "performance-chart",
            values: rowData.performanceValues || [], // Array de números
            color: "#ff6b6b",
        },
    } as PerformanceChartCell;
}
```

### 6. **Dropdowns/Select**

```typescript
if (columnId === "Tipo actuación") {
    return {
        kind: GridCellKind.Text,
        data: value,
        displayData: value,
        allowOverlay: true,
        readonly: false,
        // Puedes agregar un overlay personalizado con un select
    };
}
```

### 7. **Colores Condicionales por Fila**

Glide no soporta directamente `muiTableBodyRowProps`, pero puedes aplicar colores por celda:

```typescript
// En getCellContent, aplicar color según el estado:
const rowState = data[row]._state;
let bgColor = "#ffffff";

if (rowState === "OK") bgColor = "#e8f5e9";
else if (rowState === "ERROR") bgColor = "#ffebee";
else if (rowState === "PENDIENTE") bgColor = "#fff3e0";

return {
    kind: GridCellKind.Text,
    data: strValue,
    displayData: strValue,
    allowOverlay: true,
    themeOverride: {
        bgCell: bgColor,
    },
};
```

### 8. **Íconos en Celdas**

Puedes usar Unicode emojis o dibujar íconos con canvas:

```typescript
if (columnId === "Estado") {
    let icon = "";
    if (value === "OK") icon = "✅";
    else if (value === "ERROR") icon = "❌";
    else icon = "⏳";

    return {
        kind: GridCellKind.Text,
        data: `${icon} ${value}`,
        displayData: `${icon} ${value}`,
        allowOverlay: false,
    };
}
```

## 📋 Ejemplo de Implementación Completa con Estilos

Si quieres un diseño exactamente como la imagen, aquí está un ejemplo:

```typescript
const getCellContent = useCallback(([col, row]: Item): GridCell => {
    const rowData = data[row];
    const columnDef = COLUMN_DEFINITIONS[col];
    const value = rowData[columnDef.id as keyof GridRow];

    // Columna Estado con badge
    if (columnDef.id === "_state") {
        const state = value as string;
        let bgColor = "#fff3e0";
        let textColor = "#ef6c00";
        let icon = "⏳";

        if (state === "OK") {
            bgColor = "#e8f5e9";
            textColor = "#2e7d32";
            icon = "✅";
        } else if (state === "ERROR") {
            bgColor = "#ffebee";
            textColor = "#c62828";
            icon = "❌";
        }

        return {
            kind: GridCellKind.Text,
            data: `${icon} ${state}`,
            displayData: `${icon} ${state}`,
            allowOverlay: false,
            readonly: true,
            themeOverride: {
                bgCell: bgColor,
                textDark: textColor,
            },
        };
    }

    // Columna Inspector con badge estilo pill
    if (columnDef.id.startsWith("Inspector")) {
        return {
            kind: GridCellKind.Text,
            data: value?.toString() || "",
            displayData: value?.toString() || "",
            allowOverlay: true,
            themeOverride: {
                bgCell: "#e3f2fd",
                textDark: "#1565c0",
            },
            style: "faded",
        };
    }

    // Columna de fecha con formato especial
    if (columnDef.id === "Fecha actuación") {
        const formattedDate = value ? new Date(value).toLocaleDateString("es-AR") : "";
        return {
            kind: GridCellKind.Text,
            data: value?.toString() || "",
            displayData: formattedDate,
            allowOverlay: true,
            themeOverride: {
                textDark: "#424242",
            },
        };
    }

    // Resto de columnas
    return {
        kind: GridCellKind.Text,
        data: value?.toString() || "",
        displayData: value?.toString() || "",
        allowOverlay: columnDef.editable,
        readonly: !columnDef.editable,
    };
}, [data]);
```

## 🚀 Cómo Activar los Estilos Avanzados

1. **Para badges/pills**: Ya incluidos en el tema personalizado
2. **Para checkboxes**: Cambiar `GridCellKind.Text` a `GridCellKind.Boolean`
3. **Para imágenes**: Cambiar a `GridCellKind.Image` y pasar URLs
4. **Para gráficos**: Crear custom renderers (ejemplo arriba) y pasarlos a `customRenderers` prop
5. **Para colores por fila**: Aplicar `themeOverride` en cada celda según el estado

## 🔧 Configuración de Custom Renderers

Si creas custom renderers, agrégalos al DataEditor:

```typescript
import { performanceChartRenderer } from "./customRenderers/PerformanceChart";
import { badgeRenderer } from "./customRenderers/BadgeRenderer";

<DataEditor
    getCellContent={getCellContent}
    columns={columns}
    rows={data.length}
    customRenderers={[performanceChartRenderer, badgeRenderer]}
    // ... resto de props
/>
```

## 📚 Recursos

- **Storybook oficial**: https://glideapps.github.io/glide-data-grid/
- **Documentación**: https://docs.grid.glideapps.com/
- **Ejemplos de custom cells**: https://glideapps.github.io/glide-data-grid/?path=/story/glide-data-grid-dataeditor-demos--custom-cells

## 🎯 Siguiente Paso

Si quieres implementar alguno de estos estilos específicos (badges, gráficos, checkboxes), solo avísame y te creo el código exacto para tu componente.
