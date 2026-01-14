import {
    type CustomCell,
    type CustomRenderer,
    GridCellKind,
} from "@glideapps/glide-data-grid";

/**
 * Props para la celda Sparkline (mini gráfico de líneas)
 */
interface SparklineCellProps {
    readonly kind: "sparkline-cell";
    readonly values: number[];
    readonly color?: string;
    readonly graphKind?: "line" | "area";
    readonly showDots?: boolean;
}

export type SparklineCell = CustomCell<SparklineCellProps>;

/**
 * Custom Renderer para mini gráficos de líneas (sparklines)
 * Similar a los gráficos de "Performance" de la imagen
 */
export const sparklineRenderer: CustomRenderer<SparklineCell> = {
    kind: GridCellKind.Custom,
    isMatch: (c): c is SparklineCell => (c.data as any).kind === "sparkline-cell",
    draw: (args, cell) => {
        const { ctx, rect, theme } = args;
        const { values, color, graphKind = "line", showDots = false } = cell.data;

        if (!values || values.length === 0) return;

        ctx.save();

        // Configuración
        const padding = 12;
        const chartX = rect.x + padding;
        const chartY = rect.y + padding;
        const chartWidth = rect.width - padding * 2;
        const chartHeight = rect.height - padding * 2;

        if (chartWidth <= 0 || chartHeight <= 0) {
            ctx.restore();
            return;
        }

        // Normalizar valores
        const maxVal = Math.max(...values);
        const minVal = Math.min(...values);
        const range = maxVal - minVal || 1;

        // Función para obtener coordenadas
        const getX = (index: number) => {
            return chartX + (index / (values.length - 1)) * chartWidth;
        };

        const getY = (value: number) => {
            const normalizedVal = (value - minVal) / range;
            return chartY + chartHeight - normalizedVal * chartHeight;
        };

        // Color del gráfico
        const lineColor = color || theme.accentColor;

        // Dibujar área si es tipo "area"
        if (graphKind === "area") {
            ctx.beginPath();
            ctx.moveTo(getX(0), chartY + chartHeight);

            values.forEach((val, i) => {
                const x = getX(i);
                const y = getY(val);
                if (i === 0) {
                    ctx.lineTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.lineTo(getX(values.length - 1), chartY + chartHeight);
            ctx.closePath();

            // Gradiente para el área
            const gradient = ctx.createLinearGradient(0, chartY, 0, chartY + chartHeight);
            gradient.addColorStop(0, hexToRgba(lineColor, 0.3));
            gradient.addColorStop(1, hexToRgba(lineColor, 0.05));
            ctx.fillStyle = gradient;
            ctx.fill();
        }

        // Dibujar línea principal
        ctx.beginPath();
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        values.forEach((val, i) => {
            const x = getX(i);
            const y = getY(val);

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Dibujar puntos si está habilitado
        if (showDots) {
            values.forEach((val, i) => {
                const x = getX(i);
                const y = getY(val);

                ctx.beginPath();
                ctx.arc(x, y, 3, 0, 2 * Math.PI);
                ctx.fillStyle = lineColor;
                ctx.fill();
                ctx.strokeStyle = theme.bgCell;
                ctx.lineWidth = 2;
                ctx.stroke();
            });
        }

        ctx.restore();
    },
    provideEditor: () => undefined, // No editable
};

/**
 * Convierte un color hex a rgba con alpha
 */
function hexToRgba(hex: string, alpha: number): string {
    // Remover # si existe
    hex = hex.replace("#", "");

    // Convertir a RGB
    let r: number, g: number, b: number;

    if (hex.length === 3) {
        r = parseInt(hex[0] + hex[0], 16);
        g = parseInt(hex[1] + hex[1], 16);
        b = parseInt(hex[2] + hex[2], 16);
    } else {
        r = parseInt(hex.substring(0, 2), 16);
        g = parseInt(hex.substring(2, 4), 16);
        b = parseInt(hex.substring(4, 6), 16);
    }

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Helper para crear una SparklineCell fácilmente
 */
export function createSparklineCell(
    values: number[],
    color?: string,
    graphKind: "line" | "area" = "line",
    showDots: boolean = false
): SparklineCell {
    return {
        kind: GridCellKind.Custom,
        allowOverlay: false,
        copyData: values.join(", "),
        data: {
            kind: "sparkline-cell",
            values,
            color,
            graphKind,
            showDots,
        },
    };
}

/**
 * Genera valores aleatorios para demo
 */
export function generateRandomSparklineData(count: number = 12): number[] {
    const values: number[] = [];
    let current = Math.random() * 100;

    for (let i = 0; i < count; i++) {
        current += (Math.random() - 0.5) * 20;
        current = Math.max(0, Math.min(100, current));
        values.push(Math.round(current));
    }

    return values;
}
