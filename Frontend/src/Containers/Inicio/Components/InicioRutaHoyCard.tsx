import { Box, Button, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import { InicioCardShellGrid, StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

/**
 * Acceso operativo a Rutas de trabajo (misma cáscara que las otras 8 cards de la grilla Inicio).
 */
export default function InicioRutaHoyCard() {
  return (
    <Link
      to="/rutasTrabajo"
      style={{ textDecoration: "none", display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <Box sx={{ ...InicioCardShellGrid, flex: 1 }}>
        <Typography sx={{ ...StyleTextCard, fontSize: "15px", mb: 0.5 }}>Ruta de trabajo</Typography>
        <Typography sx={{ ...StyleTextCardSecondary, fontSize: "12px", mb: 1, lineHeight: 1.45 }}>
          Planificá o continuá la ruta del día. Si tenés una ruta en sesión, se restaura al entrar.
        </Typography>
        <Button
          component="span"
          variant="contained"
          size="small"
          sx={{
            alignSelf: "flex-start",
            mt: "auto",
            textTransform: "none",
            fontFamily: '"Tactic Sans", sans-serif',
            backgroundColor: GLASS_COLORS.primary,
          }}
        >
          Ir a ruta de trabajo
        </Button>
      </Box>
    </Link>
  );
}
