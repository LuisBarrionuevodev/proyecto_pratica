import { Box, Typography } from "@mui/material";
import type { ReactNode } from "react";

import {
  dashboardSectionBodySx,
  dashboardSectionHeaderSx,
  dashboardSectionSurfaceSx,
} from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

type DashboardSectionBlockProps = {
  title: string;
  subtitle?: string;
  first?: boolean;
  children: ReactNode;
};

/**
 * Bloque de sección integrado (cabecera + cuerpo en una sola superficie glass).
 */
export function DashboardSectionBlock({ title, subtitle, first = false, children }: DashboardSectionBlockProps) {
  return (
    <Box sx={{ ...dashboardSectionSurfaceSx, mt: first ? 0.5 : 2, minWidth: 0, maxWidth: "100%" }}>
      <Box sx={dashboardSectionHeaderSx}>
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
      <Box sx={dashboardSectionBodySx}>{children}</Box>
    </Box>
  );
}
