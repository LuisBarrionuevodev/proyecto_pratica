import { Box, CircularProgress, Typography } from "@mui/material";

/**
 * Fallback estable al cargar chunks de ruta (PERF.4).
 */
export function RouteModuleFallback() {
  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 280,
        gap: 2,
        py: 4,
        px: 2,
      }}
    >
      <CircularProgress size={32} sx={{ color: "#0166FF" }} />
      <Typography variant="body2" color="text.secondary">
        Cargando módulo…
      </Typography>
    </Box>
  );
}
