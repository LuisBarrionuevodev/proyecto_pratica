import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";
import { Box, ButtonBase, IconButton, Stack, Typography } from "@mui/material";
import type { SxProps, Theme } from "@mui/material/styles";
import type { ReactNode } from "react";

import { GLASS_COLORS } from "../../styles/GlassStyles";
import { toIsoDateLocal } from "../../utils/dateRange";

const TACTIC = '"Tactic Sans", sans-serif' as const;

export const CALENDAR_WEEKDAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"] as const;

export function calendarDaysInMonth(year: number, monthIndex: number): number {
  return new Date(year, monthIndex + 1, 0).getDate();
}

/** Desplazamiento del 1º del mes para grid Lun–Dom (0 = lunes). */
export function calendarMondayOffsetFirstOfMonth(year: number, monthIndex: number): number {
  const js = new Date(year, monthIndex, 1).getDay();
  return (js + 6) % 7;
}

export type MonthCalendarDayContext = {
  iso: string;
  dayNum: number;
  esHoy: boolean;
  selected: boolean;
};

export type InstitutionalMonthCalendarGridProps = {
  monthAnchor: Date;
  onMonthChange: (next: Date) => void;
  hoyIso: string;
  selectedIso: string | null;
  onSelectDay: (iso: string) => void;
  /** Tooltip / accesibilidad por celda. */
  getDayTitle?: (ctx: MonthCalendarDayContext) => string;
  /** Estilos extra del botón-día (encima de estilos base). */
  getDayButtonSx?: (ctx: MonthCalendarDayContext) => SxProps<Theme>;
  /** Contenido bajo el número (punto, chip cantidad, etc.). */
  renderDayFooter?: (ctx: MonthCalendarDayContext) => ReactNode;
  /** aria-label del grid */
  "aria-label"?: string;
};

/**
 * Grilla mensual Lun–Dom con navegación, estética institucional (Rutas / Completar trabajo).
 * El llamador define color/leyenda por día vía `getDayButtonSx` / `renderDayFooter`.
 */
export function InstitutionalMonthCalendarGrid({
  monthAnchor,
  onMonthChange,
  hoyIso,
  selectedIso,
  onSelectDay,
  getDayTitle,
  getDayButtonSx,
  renderDayFooter,
  "aria-label": ariaLabel = "Calendario mensual",
}: InstitutionalMonthCalendarGridProps) {
  const y = monthAnchor.getFullYear();
  const m0 = monthAnchor.getMonth();
  const dim = calendarDaysInMonth(y, m0);
  const lead = calendarMondayOffsetFirstOfMonth(y, m0);
  const totalCells = lead + dim;
  const rows = Math.ceil(totalCells / 7);

  const tituloMes = new Intl.DateTimeFormat("es-AR", { month: "long", year: "numeric" }).format(monthAnchor);

  const prev = () => onMonthChange(new Date(y, m0 - 1, 1));
  const next = () => onMonthChange(new Date(y, m0 + 1, 1));

  const cells: { key: string; iso: string | null; dayNum: number | null }[] = [];
  for (let i = 0; i < rows * 7; i++) {
    if (i < lead || i >= lead + dim) {
      cells.push({ key: `pad-${y}-${m0}-${i}`, iso: null, dayNum: null });
    } else {
      const dayNum = i - lead + 1;
      const iso = toIsoDateLocal(new Date(y, m0, dayNum));
      cells.push({ key: iso, iso, dayNum });
    }
  }

  return (
    <Stack spacing={1.25}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
        <IconButton size="small" onClick={prev} aria-label="Mes anterior" sx={{ color: "rgba(255,255,255,0.85)" }}>
          <ChevronLeft />
        </IconButton>
        <Typography
          sx={{
            fontFamily: TACTIC,
            fontWeight: 700,
            fontSize: "0.88rem",
            color: "#FFFFFF",
            textTransform: "capitalize",
            flex: 1,
            textAlign: "center",
          }}
        >
          {tituloMes}
        </Typography>
        <IconButton size="small" onClick={next} aria-label="Mes siguiente" sx={{ color: "rgba(255,255,255,0.85)" }}>
          <ChevronRight />
        </IconButton>
      </Stack>

      <Box
        role="grid"
        aria-label={ariaLabel}
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: 0.5,
          textAlign: "center",
        }}
      >
        {CALENDAR_WEEKDAY_LABELS.map((c) => (
          <Typography
            key={c}
            variant="caption"
            sx={{ fontFamily: TACTIC, color: "#FFFFFF", fontSize: "0.64rem", fontWeight: 600 }}
          >
            {c}
          </Typography>
        ))}
        {cells.map((cell) => {
          if (cell.iso == null || cell.dayNum == null) {
            return <Box key={cell.key} sx={{ minHeight: 40 }} />;
          }
          const ctx: MonthCalendarDayContext = {
            iso: cell.iso,
            dayNum: cell.dayNum,
            esHoy: cell.iso === hoyIso,
            selected: cell.iso === selectedIso,
          };
          const extraSx = getDayButtonSx?.(ctx) ?? {};
          const title = getDayTitle?.(ctx) ?? "";
          const footerEl = renderDayFooter ? renderDayFooter(ctx) : undefined;
          const secondRow =
            footerEl !== undefined ? (
              footerEl
            ) : ctx.esHoy ? (
              <Box
                component="span"
                sx={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  bgcolor: GLASS_COLORS.primary,
                  opacity: 0.85,
                }}
              />
            ) : (
              <Box sx={{ height: 5 }} />
            );

          return (
            <ButtonBase
              key={cell.key}
              title={title}
              onClick={() => onSelectDay(cell.iso!)}
              sx={{
                minHeight: 40,
                borderRadius: "10px",
                fontFamily: TACTIC,
                fontWeight: ctx.esHoy ? 800 : 600,
                fontSize: "0.8rem",
                color: "#FFFFFF",
                bgcolor: "rgba(255,255,255,0.025)",
                border: `1px solid ${GLASS_COLORS.borderLight}`,
                boxShadow: ctx.selected ? `0 0 0 2px ${GLASS_COLORS.primary}` : "none",
                transition: "background-color 0.12s ease, border-color 0.12s ease",
                "&:hover": { bgcolor: "rgba(255,255,255,0.06)" },
                "&.Mui-focusVisible": {
                  outline: `2px solid ${GLASS_COLORS.primary}`,
                  outlineOffset: 2,
                },
                ...extraSx,
              }}
            >
              <Stack alignItems="center" spacing={0.15} sx={{ py: 0.25 }}>
                <span>{cell.dayNum}</span>
                {secondRow}
              </Stack>
            </ButtonBase>
          );
        })}
      </Box>
    </Stack>
  );
}
