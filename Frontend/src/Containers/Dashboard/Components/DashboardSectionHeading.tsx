import { Box, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

type DashboardSectionHeadingProps = {
  title: string;
  subtitle?: string;
  /** Primera sección tras filtros: sin margen superior extra. */
  first?: boolean;
};

/**
 * Título de bloque del dashboard (D1d.2): jerarquía institucional glass.
 */
export function DashboardSectionHeading({ title, subtitle, first = false }: DashboardSectionHeadingProps) {
  return (
    <Box sx={{ mt: first ? 0.5 : 2, mb: 1 }}>
      <Typography
        component="h2"
        sx={{
          fontFamily: FONT_FAMILY_UI,
          fontWeight: 700,
          fontSize: "0.8125rem",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: GLASS_COLORS.textPrimary,
          lineHeight: 1.25,
        }}
      >
        {title}
      </Typography>
      {subtitle ? (
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 0.35,
            fontFamily: FONT_FAMILY_UI,
            color: GLASS_COLORS.textMuted,
            fontSize: "0.7rem",
            lineHeight: 1.35,
          }}
        >
          {subtitle}
        </Typography>
      ) : null}
    </Box>
  );
}
