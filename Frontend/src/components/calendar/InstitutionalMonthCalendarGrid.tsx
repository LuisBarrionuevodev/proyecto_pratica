import ChevronLeft from "@mui/icons-material/ChevronLeft";
import { FONT_FAMILY_UI } from "../../theme/typography";
import ChevronRight from "@mui/icons-material/ChevronRight";
import { Box, ButtonBase, IconButton, Stack, Typography } from "@mui/material";
import type { SxProps, Theme } from "@mui/material/styles";
import type { ReactNode } from "react";

import { GLASS_COLORS } from "../../styles/GlassStyles";
import { CSS_VAR_NAMES } from "../../theme/applyCssVariables";

const CAL_DAY_BG = `var(${CSS_VAR_NAMES.calendarDayBg})`;
const CAL_DAY_HOVER = `var(${CSS_VAR_NAMES.calendarDayHover})`;
const CAL_DAY_SELECTED = `var(${CSS_VAR_NAMES.calendarDaySelected})`;
const CAL_DAY_SELECTED_TEXT = `var(${CSS_VAR_NAMES.calendarDaySelectedText})`;
const CAL_DAY_BORDER = `var(${CSS_VAR_NAMES.calendarDayBorder})`;
import { toIsoDateLocal } from "../../utils/dateRange";
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
  /** Altura mínima de celdas de día (px). */
  cellMinHeight?: number;
  /** Separación entre celdas (theme spacing). */
  cellGap?: number;
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
  cellMinHeight = 40,
  cellGap = 0.5,
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
        <IconButton size="small" onClick={prev} aria-label="Mes anterior" sx={{ color: GLASS_COLORS.textSecondary }}>
          <ChevronLeft />
        </IconButton>
        <Typography
          sx={{
            fontFamily: FONT_FAMILY_UI,
            fontWeight: 700,
            fontSize: "0.88rem",
            color: GLASS_COLORS.textPrimary,
            textTransform: "capitalize",
            flex: 1,
            textAlign: "center",
          }}
        >
          {tituloMes}
        </Typography>
        <IconButton size="small" onClick={next} aria-label="Mes siguiente" sx={{ color: GLASS_COLORS.textSecondary }}>
          <ChevronRight />
        </IconButton>
      </Stack>

      <Box
        role="grid"
        aria-label={ariaLabel}
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: cellGap,
          textAlign: "center",
        }}
      >
        {CALENDAR_WEEKDAY_LABELS.map((c) => (
          <Typography
            key={c}
            variant="caption"
            sx={{ fontFamily: FONT_FAMILY_UI, color: GLASS_COLORS.textPrimary, fontSize: "0.68rem", fontWeight: 600 }}
          >
            {c}
          </Typography>
        ))}
        {cells.map((cell) => {
          if (cell.iso == null || cell.dayNum == null) {
            return <Box key={cell.key} sx={{ minHeight: cellMinHeight }} />;
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
            footerEl !== undefined ? footerEl : <Box sx={{ height: 5 }} />;

          return (
            <ButtonBase
              key={cell.key}
              title={title}
              onClick={() => onSelectDay(cell.iso!)}
              sx={{
                position: "relative",
                minHeight: cellMinHeight,
                borderRadius: "10px",
                fontFamily: FONT_FAMILY_UI,
                fontWeight: ctx.esHoy ? 800 : 700,
                fontSize: cellMinHeight >= 68 ? "1.05rem" : cellMinHeight >= 52 ? "0.9rem" : "0.8rem",
                color: ctx.selected ? CAL_DAY_SELECTED_TEXT : GLASS_COLORS.textPrimary,
                bgcolor: ctx.selected ? CAL_DAY_SELECTED : CAL_DAY_BG,
                border: `1px solid ${ctx.selected ? GLASS_COLORS.primary : CAL_DAY_BORDER}`,
                boxShadow: ctx.selected ? `0 0 0 2px ${GLASS_COLORS.primary}` : "none",
                transition: "background-color 0.12s ease, border-color 0.12s ease",
                "&:hover": { bgcolor: ctx.selected ? CAL_DAY_SELECTED : CAL_DAY_HOVER },
                "&.Mui-focusVisible": {
                  outline: `2px solid ${GLASS_COLORS.primary}`,
                  outlineOffset: 2,
                },
                ...(ctx.esHoy
                  ? {
                      "&::after": {
                        content: '""',
                        position: "absolute",
                        top: 6,
                        right: 6,
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        bgcolor: GLASS_COLORS.primary,
                        opacity: 0.9,
                        pointerEvents: "none",
                      },
                    }
                  : {}),
                ...extraSx,
              }}
            >
              <Stack alignItems="center" spacing={0.35} sx={{ py: cellMinHeight >= 68 ? 0.5 : 0.25, px: 0.25 }}>
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
