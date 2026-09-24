import { Box, CircularProgress } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";

type Props = {
  visible: boolean;
};

/**
 * Overlay suave al refrescar filtros/período (mantiene secciones visibles debajo).
 */
export function DashboardIndicadoresRefreshingOverlay({ visible }: Props) {
  if (!visible) return null;

  return (
    <Box
      aria-hidden
      sx={{
        position: "absolute",
        inset: 0,
        zIndex: 2,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        pt: 6,
        bgcolor: "rgba(8, 12, 22, 0.35)",
        backdropFilter: "blur(2px)",
        borderRadius: 1,
        pointerEvents: "none",
      }}
    >
      <CircularProgress size={32} sx={{ color: GLASS_COLORS.primary }} />
    </Box>
  );
}
