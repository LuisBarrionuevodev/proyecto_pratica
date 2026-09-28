import { Chip } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

/** Marca visual para bloques del dashboard sin datos reales conectados (D1b). */
export function DashboardDemoBadge() {
  return (
    <Chip
      label="Demo"
      size="small"
      variant="outlined"
      sx={{
        height: 24,
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 700,
        fontSize: "0.7rem",
        letterSpacing: "0.06em",
        color: "rgba(255, 193, 7, 0.95)",
        borderColor: "rgba(255, 193, 7, 0.45)",
        backgroundColor: "rgba(255, 193, 7, 0.08)",
      }}
    />
  );
}

/** Texto secundario bajo gráficos demo. */
export const dashboardDemoCaptionSx = {
  display: "block",
  mt: 1,
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.75rem",
  color: GLASS_COLORS.textSecondary,
} as const;
