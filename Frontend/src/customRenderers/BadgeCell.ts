import {
    type CustomCell,
    type CustomRenderer,
    GridCellKind,
    measureTextCached,
    getMiddleCenterBias,
} from "@glideapps/glide-data-grid";

/**
 * Props para la celda Badge personalizada
 */
interface BadgeCellProps {
    readonly kind: "badge-cell";
    readonly value: string;
    readonly color?: "success" | "error" | "warning" | "info" | "default";
    readonly icon?: string; // Emoji o unicode icon
}

export type BadgeCell = CustomCell<BadgeCellProps>;

/**
 * Mapa de colores para badges
 */
const BADGE_COLORS = {
    success: {
        bg: "#e8f5e9",
        text: "#2e7d32",
        border: "#81c784",
    },
    error: {
        bg: "#ffebee",
        text: "#c62828",
        border: "#e57373",
    },
    warning: {
        bg: "#fff3e0",
        text: "#ef6c00",
        border: "#ffb74d",
    },
    info: {
        bg: "#e3f2fd",
        text: "#1565c0",
        border: "#64b5f6",
    },
    default: {
        bg: "#f5f5f5",
        text: "#616161",
        border: "#bdbdbd",
    },
};

/**
 * Custom Renderer para celdas tipo Badge/Pill
 * 
 * Este renderer dibuja una celda con estilo de badge moderno:
 * - Fondo de color según el tipo
 * - Bordes redondeados
 * - Texto centrado
 * - Ícono opcional
 */
export const badgeRenderer: CustomRenderer<BadgeCell> = {
    kind: GridCellKind.Custom,
    isMatch: (c): c is BadgeCell => (c.data as any).kind === "badge-cell",
    draw: (args, cell) => {
        const { ctx, theme, rect } = args;
        const { value, color = "default", icon } = cell.data;

        if (!value) return;

        const colors = BADGE_COLORS[color];
        const displayText = icon ? `${icon} ${value}` : value;

        // Configurar fuente
        const fontSize = 12;
        const fontFamily = theme.fontFamily;
        const font = `${fontSize}px ${fontFamily}`;
        ctx.font = font;

        // Medir texto
        const textMetrics = measureTextCached(displayText, ctx, font);
        const textWidth = textMetrics.width;

        // Dimensiones del badge
        const padding = 8;
        const badgeHeight = 24;
        const badgeWidth = textWidth + padding * 2;

        // Centrar el badge en la celda
        const x = rect.x + (rect.width - badgeWidth) / 2;
        const y = rect.y + (rect.height - badgeHeight) / 2;

        ctx.save();

        // Dibujar fondo del badge con bordes redondeados
        ctx.beginPath();
        const radius = badgeHeight / 2;
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + badgeWidth - radius, y);
        ctx.quadraticCurveTo(x + badgeWidth, y, x + badgeWidth, y + radius);
        ctx.lineTo(x + badgeWidth, y + badgeHeight - radius);
        ctx.quadraticCurveTo(x + badgeWidth, y + badgeHeight, x + badgeWidth - radius, y + badgeHeight);
        ctx.lineTo(x + radius, y + badgeHeight);
        ctx.quadraticCurveTo(x, y + badgeHeight, x, y + badgeHeight - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();

        // Rellenar fondo
        ctx.fillStyle = colors.bg;
        ctx.fill();

        // Dibujar borde
        ctx.strokeStyle = colors.border;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Dibujar texto
        ctx.fillStyle = colors.text;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(
            displayText,
            x + badgeWidth / 2,
            y + badgeHeight / 2 + getMiddleCenterBias(ctx, font)
        );

        ctx.restore();
    },
    provideEditor: () => ({
        editor: (props) => {
            // Editor simple de texto
            return {
                disablePadding: false,
                disableStyling: false,
            };
        },
    }),
};

/**
 * Helper function para crear una BadgeCell fácilmente
 */
export function createBadgeCell(
    value: string,
    color?: "success" | "error" | "warning" | "info" | "default",
    icon?: string
): BadgeCell {
    return {
        kind: GridCellKind.Custom,
        allowOverlay: false,
        copyData: value,
        data: {
            kind: "badge-cell",
            value,
            color,
            icon,
        },
    };
}
