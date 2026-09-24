import { Box, CircularProgress, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";

type Props = {
  message?: string;
};

/**
 * Loader compacto dentro de una sección del dashboard (carga progresiva).
 */
export function DashboardSectionLoader({ message = "Cargando..." }: Props) {
  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 1.5,
        minHeight: 120,
        py: 3,
      }}
    >
      <CircularProgress size={24} sx={{ color: GLASS_COLORS.primary }} />
      <Typography
        variant="body2"
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          color: GLASS_COLORS.textSecondary,
          fontWeight: 500,
        }}
      >
        {message}
      </Typography>
    </Box>
  );
}
