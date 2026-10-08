/** @jsxImportSource react */
import { Alert, Box, Link as MuiLink } from "@mui/material";
import { Link } from "react-router-dom";
import { useInspectorFotosPendientesCount } from "../hooks/useInspectorFotosPendientesCount";

/**
 * Aviso persistente Inspector cuando hay trabajos con fotos pendientes (MEDIA.2D).
 */
export function InspectorFotosPendientesBanner() {
  const { count, enabled } = useInspectorFotosPendientesCount();
  if (!enabled || count <= 0) {
    return null;
  }
  const message =
    count === 1
      ? "Te faltan subir fotos por una falla de conexión."
      : `Te faltan subir fotos en ${count} trabajos.`;

  return (
    <Box sx={{ px: { xs: 1, md: 2 }, pt: 1, flexShrink: 0 }}>
      <Alert severity="warning" sx={{ borderRadius: 2 }}>
        {message}{" "}
        <MuiLink component={Link} to="/completarTrabajos" underline="always" fontWeight={600}>
          Ir a Completar trabajos
        </MuiLink>
      </Alert>
    </Box>
  );
}
