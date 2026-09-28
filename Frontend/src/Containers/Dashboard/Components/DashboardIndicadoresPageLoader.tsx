import { Box, CircularProgress, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

/**
 * Loader único del dashboard de Indicadores (carga inicial de todos los bloques).
 */
export function DashboardIndicadoresPageLoader() {
  return (
    <Box
      role="status"
      aria-live="polite"
      aria-label="Cargando indicadores"
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 320,
        py: 6,
        gap: 2,
      }}
    >
      <CircularProgress size={36} sx={{ color: GLASS_COLORS.primary }} />
      <Typography
        variant="body2"
        sx={{
          fontFamily: FONT_FAMILY_UI,
          color: GLASS_COLORS.textSecondary,
          fontWeight: 500,
        }}
      >
        Cargando indicadores...
      </Typography>
    </Box>
  );
}
