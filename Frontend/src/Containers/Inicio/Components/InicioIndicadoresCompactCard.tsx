import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import { InicioCardShellGrid, StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

/** Mock hasta API de indicadores en Inicio. */
const MOCK_ACTUACIONES_MES = 86;
const MOCK_KILOS_DECOMISADOS = "1,2 t";

/**
 * Resumen compacto de indicadores (actuaciones del mes y decomisos).
 *
 * Parámetros: ninguno.
 * Retorno: JSX de card enlazada a `/dashboard` (Indicadores).
 */
export default function InicioIndicadoresCompactCard() {
  return (
    <Link
      to="/dashboard"
      style={{ textDecoration: "none", display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <Box sx={{ ...InicioCardShellGrid, flex: 1 }}>
        <Typography sx={{ ...StyleTextCard, fontSize: "15px", mb: 1 }}>Indicadores</Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "baseline", flex: 1, minHeight: 0 }}>
          <Box>
            <Typography
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 800,
                fontSize: "1.35rem",
                color: GLASS_COLORS.primary,
                lineHeight: 1,
              }}
            >
              {MOCK_ACTUACIONES_MES}
            </Typography>
            <Typography sx={{ ...StyleTextCardSecondary, fontSize: "11px", mt: 0.25 }}>Actuaciones del mes</Typography>
          </Box>
          <Box>
            <Typography
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 800,
                fontSize: "1.35rem",
                color: GLASS_COLORS.textPrimary,
                lineHeight: 1,
              }}
            >
              {MOCK_KILOS_DECOMISADOS}
            </Typography>
            <Typography sx={{ ...StyleTextCardSecondary, fontSize: "11px", mt: 0.25 }}>Kilos decomisados</Typography>
          </Box>
        </Box>
        <Typography sx={{ ...StyleTextCardSecondary, fontSize: "11px", mt: "auto", pt: 1, opacity: 0.85 }}>
          Valores ilustrativos · Ver panel completo
        </Typography>
      </Box>
    </Link>
  );
}
