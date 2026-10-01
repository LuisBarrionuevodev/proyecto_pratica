import type { SxProps, Theme } from "@mui/material/styles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

import type { ICompletarTrabajoPendienteDiaResumen } from "../../../api/completarTrabajoApi";
import { calendarDaysInMonth } from "../../../components/calendar/InstitutionalMonthCalendarGrid";
import { CSS_VAR_NAMES } from "../../../theme/applyCssVariables";
import { toIsoDateLocal } from "../../../utils/dateRange";

const V = CSS_VAR_NAMES;

/** Tono semántico de celda según cantidad de pendientes (0 / 1–5 / 6+). */
export type CompletarPendienteCeldaTono = "verde" | "amarillo" | "rojo" | "neutral";

/**
 * Límites inclusive del mes visible (`YYYY-MM-DD`).
 */
export function monthBoundsIso(mesAncla: Date): { desde: string; hasta: string } {
  const y = mesAncla.getFullYear();
  const m0 = mesAncla.getMonth();
  const dim = calendarDaysInMonth(y, m0);
  return {
    desde: toIsoDateLocal(new Date(y, m0, 1)),
    hasta: toIsoDateLocal(new Date(y, m0, dim)),
  };
}

/**
 * Etiqueta compacta visible en celda del calendario (`N!`).
 * Retorna `undefined` si no debe mostrarse contador (0 o ausente).
 */
export function formatPendientesDiaLabel(total: number): string | undefined {
  if (total <= 0) return undefined;
  return `${total}!`;
}

/** Texto descriptivo para tooltip / accesibilidad (no va en la celda). */
export function formatPendientesDiaDescripcion(total: number): string | undefined {
  if (total <= 0) return undefined;
  return total === 1 ? "1 pendiente" : `${total} pendientes`;
}

/**
 * Contador de pendientes para un día del resumen (misma fuente que el resumen API).
 */
export function pendientesFooterLabel(
  row: ICompletarTrabajoPendienteDiaResumen | undefined
): string | undefined {
  if (!row) return undefined;
  return formatPendientesDiaLabel(row.total);
}

/**
 * Tono de celda según `total` del resumen:
 * - 0 → verde
 * - 1–5 → amarillo
 * - 6+ → rojo
 * - sin fila en mes cargado → neutral
 */
export function resolvePendienteCeldaTono(
  row: ICompletarTrabajoPendienteDiaResumen | undefined
): CompletarPendienteCeldaTono {
  if (!row) return "neutral";
  if (row.total <= 0) return "verde";
  if (row.total <= 5) return "amarillo";
  return "rojo";
}

/** Superficie institucional por tono (tokens dark/light vía CSS variables). */
export function completarCeldaSurfaceSx(tono: CompletarPendienteCeldaTono): {
  bgcolor: string;
  border: string;
  color: string;
} {
  switch (tono) {
    case "verde":
      return {
        bgcolor: `var(${V.calendarCompletarVerdeBg})`,
        border: `1px solid var(${V.calendarCompletarVerdeBg})`,
        color: `var(${V.calendarCompletarVerdeText})`,
      };
    case "amarillo":
      return {
        bgcolor: `var(${V.calendarCompletarAmarilloBg})`,
        border: `1px solid var(${V.calendarCompletarAmarilloBg})`,
        color: `var(${V.calendarCompletarAmarilloText})`,
      };
    case "rojo":
      return {
        bgcolor: `var(${V.calendarCompletarRojoBg})`,
        border: `1px solid var(${V.calendarCompletarRojoBg})`,
        color: `var(${V.calendarCompletarRojoText})`,
      };
    default:
      return {
        bgcolor: `var(${V.calendarCompletarNeutralBg})`,
        border: `1px solid var(${V.calendarDayBorder})`,
        color: `var(${V.calendarCompletarNeutralText})`,
      };
  }
}

/** Tooltip accesible por tono y cantidad. */
export function completarCeldaTitle(
  tono: CompletarPendienteCeldaTono,
  pendientesLabel?: string
): string {
  const base =
    tono === "verde"
      ? "Sin pendientes de cierre"
      : tono === "amarillo"
        ? "Pendientes de cierre"
        : tono === "rojo"
          ? "Alto volumen de pendientes de cierre"
          : "Sin actividad en Completar trabajo para este día";
  return pendientesLabel ? `${base} — ${pendientesLabel}` : base;
}

/** Footer secundario bajo el número del día. */
export const completarPendingFooterSx: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.76rem",
  fontWeight: 600,
  lineHeight: 1.25,
  color: `var(${V.calendarCompletarFooterText})`,
  textAlign: "center",
  px: 0.25,
};
