import type { SxProps, Theme } from "@mui/material/styles";

import type { ICompletarTrabajoPendienteDiaResumen } from "../../../api/completarTrabajoApi";
import { calendarDaysInMonth } from "../../../components/calendar/InstitutionalMonthCalendarGrid";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { toIsoDateLocal } from "../../../utils/dateRange";

const TACTIC = '"Tactic Sans", sans-serif' as const;

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
 * Etiqueta de pendientes para celda del calendario (singular/plural).
 * Retorna `undefined` si no debe mostrarse contador (0 o ausente).
 */
export function formatPendientesDiaLabel(total: number): string | undefined {
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

/** Superficie institucional por tono (fondo/borde suaves, legibles en dark mode). */
export function completarCeldaSurfaceSx(tono: CompletarPendienteCeldaTono): {
  bgcolor: string;
  border: string;
} {
  switch (tono) {
    case "verde":
      return {
        bgcolor: "rgba(56, 142, 60, 0.14)",
        border: "1px solid rgba(129, 199, 132, 0.4)",
      };
    case "amarillo":
      return {
        bgcolor: "rgba(255, 152, 0, 0.13)",
        border: "1px solid rgba(255, 183, 77, 0.42)",
      };
    case "rojo":
      return {
        bgcolor: "rgba(211, 47, 47, 0.15)",
        border: "1px solid rgba(255, 138, 128, 0.48)",
      };
    default:
      return {
        bgcolor: "rgba(255,255,255,0.025)",
        border: `1px solid ${GLASS_COLORS.borderLight}`,
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

/** Footer gris secundario bajo el número del día. */
export const completarPendingFooterSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  fontSize: "0.62rem",
  fontWeight: 500,
  lineHeight: 1.2,
  color: "rgba(255,255,255,0.55)",
  textAlign: "center",
  px: 0.25,
};
