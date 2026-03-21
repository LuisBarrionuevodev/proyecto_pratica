import { Box, Button, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import { InicioCardShellGrid, StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

/** Placeholder hasta contador real desde API. */
const PENDIENTES_SIN_DATO = "—";

/**
 * Resumen de actas pendientes (conteo cuando exista endpoint).
 *
 * Parámetros: ninguno.
 * Retorno: JSX enlazado a `/pendientes`.
 */
export default function InicioActasPendientesCompactCard() {
  return (
    <Link
      to="/pendientes"
      style={{ textDecoration: "none", display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <Box sx={{ ...InicioCardShellGrid, flex: 1 }}>
        <Typography sx={{ ...StyleTextCard, fontSize: "15px", mb: 0.25 }}>Actas pendientes</Typography>
        <Typography
          sx={{
            fontFamily: '"Tactic Sans", sans-serif',
            fontWeight: 800,
            fontSize: { xs: "1.5rem", sm: "1.65rem" },
            color: GLASS_COLORS.primary,
            lineHeight: 1.1,
            mb: 0.5,
          }}
        >
          {PENDIENTES_SIN_DATO}
        </Typography>
        <Typography sx={{ ...StyleTextCardSecondary, fontSize: "12px", mb: 1, lineHeight: 1.35 }}>
          El total se mostrará cuando el servicio esté disponible.
        </Typography>
        <Button
          component="span"
          variant="outlined"
          size="small"
          sx={{
            alignSelf: "flex-start",
            mt: "auto",
            textTransform: "none",
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "12px",
            py: 0.25,
            px: 1.25,
            minHeight: 28,
            borderColor: GLASS_COLORS.borderMedium,
            color: GLASS_COLORS.textPrimary,
          }}
        >
          Ver pendientes
        </Button>
      </Box>
    </Link>
  );
}
