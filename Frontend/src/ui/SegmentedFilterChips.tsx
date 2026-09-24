import RefreshIcon from "@mui/icons-material/Refresh";
import { Box, Chip, IconButton, Paper } from "@mui/material";
import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS, glassTabsSecondaryPanelBarSx } from "../styles/GlassStyles";

export type SegmentedFilterChipsOption<T extends string | number = string> = {
  value: T;
  /** Texto completo del chip, p. ej. `En plazo · 12` */
  label: string;
};

export type SegmentedFilterChipsProps<T extends string | number = string> = {
  options: SegmentedFilterChipsOption<T>[];
  /** Toque = aplicar: se dispara al elegir un segmento. */
  onSelect: (value: T) => void;
  isSelected: (value: T) => boolean;
  /** Icono opcional para refrescar datos (no sustituye al toque en el chip). */
  onRefresh?: () => void;
  refreshDisabled?: boolean;
  /** Contenedor: por defecto `Paper` + panel glass secundario. */
  wrapWithPanel?: boolean;
  sx?: SxProps<Theme>;
};

/**
 * Chips grandes como selector de sub-vista / filtro (mismo criterio visual en notificación, expediente, etc.).
 * Sin título ni texto explicativo: solo segmentos tocables.
 */
export function segmentedFilterChipSx(selected: boolean): SxProps<Theme> {
  /** Siempre `outlined` + misma caja: evita salto de altura entre filled/outlined de MUI. */
  return {
    cursor: "pointer",
    fontWeight: 600,
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "0.9375rem",
    height: 52,
    minHeight: 52,
    maxHeight: 52,
    boxSizing: "border-box",
    borderRadius: "16px",
    border: `1px solid ${selected ? "rgba(1, 102, 255, 0.55)" : GLASS_COLORS.borderMedium}`,
    backgroundColor: selected ? "rgba(1, 102, 255, 0.28)" : "rgba(255, 255, 255, 0.04)",
    color: GLASS_COLORS.textPrimary,
    "& .MuiChip-label": {
      px: 1.5,
      py: 0,
      lineHeight: 1.25,
    },
    "&:hover": {
      backgroundColor: selected ? "rgba(1, 102, 255, 0.38)" : GLASS_COLORS.hoverBg,
    },
  };
}

export function SegmentedFilterChips<T extends string | number = string>({
  options,
  onSelect,
  isSelected,
  onRefresh,
  refreshDisabled,
  wrapWithPanel = true,
  sx,
}: SegmentedFilterChipsProps<T>) {
  const inner = (
    <Box
      sx={[
        {
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 1.5,
          width: "100%",
          minHeight: 52,
        },
        ...(sx ? (Array.isArray(sx) ? sx : [sx]) : []),
      ]}
    >
      {options.map((opt) => {
        const selected = isSelected(opt.value);
        return (
          <Chip
            key={String(opt.value)}
            label={opt.label}
            color="default"
            onClick={() => onSelect(opt.value)}
            variant="outlined"
            sx={segmentedFilterChipSx(selected)}
          />
        );
      })}
      {onRefresh ? (
        <IconButton
          type="button"
          size="small"
          aria-label="Actualizar datos"
          disabled={refreshDisabled}
          onClick={() => onRefresh()}
          sx={{
            flexShrink: 0,
            alignSelf: "center",
            ml: { xs: 0, sm: "auto" },
            color: GLASS_COLORS.textSecondary,
            "&:hover": { color: GLASS_COLORS.textPrimary, backgroundColor: GLASS_COLORS.hoverBg },
          }}
        >
          <RefreshIcon fontSize="small" />
        </IconButton>
      ) : null}
    </Box>
  );

  if (!wrapWithPanel) {
    return inner;
  }

  return (
    <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
      {inner}
    </Paper>
  );
}
