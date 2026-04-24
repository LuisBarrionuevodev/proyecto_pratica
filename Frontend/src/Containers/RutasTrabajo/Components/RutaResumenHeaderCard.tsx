import type { ReactNode } from "react";
import type { SxProps, Theme } from "@mui/material";
import { Box, Chip, Paper, Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { planificacionPanelSubtitleSx, rutasInstitutionalResumenPaperSx, rutasResumenTitleSx } from "../styles/institutionalVisual";

const TACTIC = '"Tactic Sans", sans-serif' as const;

/** Botones de acción en columna (mismo ancho y alto mínimo en los tres slices). */
export const rutaResumenHeaderAccionesColumnaSx: SxProps<Theme> = {
  width: { xs: "100%", lg: 260 },
  alignSelf: { xs: "stretch", lg: "flex-start" },
};

export const rutaResumenHeaderAccionButtonSx: SxProps<Theme> = {
  width: "100%",
  minHeight: 40,
  fontFamily: TACTIC,
};
export type RutaResumenHeaderChip = {
  key: string;
  label: string;
  /** `estado`: chip con más énfasis; omitir o `default`: estilo outline estándar. */
  variant?: "estado" | "default";
};

export type RutaResumenHeaderCardProps = {
  title: string;
  /** Texto breve bajo el título; omitir en histórico si no aplica. */
  subtitle?: string | null;
  chips: RutaResumenHeaderChip[];
  /** Bloque de resumen (fechas, métricas, línea de identificación). */
  summary?: ReactNode;
  actions: ReactNode;
};

const chipOutlineSx = {
  fontSize: "0.7rem",
  borderColor: GLASS_COLORS.borderLight,
  color: GLASS_COLORS.textSecondary,
  backgroundColor: "rgba(255,255,255,0.03)",
} as const;

const chipEstadoSx = {
  ...chipOutlineSx,
  fontWeight: 600,
  color: GLASS_COLORS.textPrimary,
  borderColor: GLASS_COLORS.borderMedium,
} as const;

/**
 * Segunda caja unificada bajo el stepper: título, chips, resumen y acciones en un solo bloque glass.
 * Usada en Planificación, Asignación, Mapa final e histórico.
 */
export function RutaResumenHeaderCard({ title, subtitle, chips, summary, actions }: RutaResumenHeaderCardProps) {
  return (
    <Paper elevation={0} sx={rutasInstitutionalResumenPaperSx}>
      <Stack
        direction={{ xs: "column", lg: "row" }}
        spacing={2}
        alignItems={{ lg: "flex-start" }}
        justifyContent="space-between"
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            sx={{
              ...rutasResumenTitleSx,
              fontSize: "1.0625rem",
              letterSpacing: "0.04em",
            }}
          >
            {title}
          </Typography>
          {subtitle ? (
            <Typography
              sx={{
                ...planificacionPanelSubtitleSx,
                mt: 0.35,
                fontSize: "0.72rem",
                color: GLASS_COLORS.textMuted,
                maxWidth: 560,
              }}
            >
              {subtitle}
            </Typography>
          ) : null}
          {chips.length > 0 ? (
            <Stack direction="row" flexWrap="wrap" gap={0.75} sx={{ mt: subtitle ? 1 : 1.25 }} alignItems="center">
              {chips.map((c) => (
                <Chip
                  key={c.key}
                  size="small"
                  variant="outlined"
                  label={c.label}
                  sx={c.variant === "estado" ? chipEstadoSx : chipOutlineSx}
                />
              ))}
            </Stack>
          ) : null}
          {summary ? <Box sx={{ mt: chips.length > 0 || subtitle ? 1.5 : 1 }}>{summary}</Box> : null}
        </Box>
        <Stack direction="column" spacing={1.25} sx={{ ...rutaResumenHeaderAccionesColumnaSx, flexShrink: 0 }}>
          {actions}
        </Stack>
      </Stack>
    </Paper>
  );
}
