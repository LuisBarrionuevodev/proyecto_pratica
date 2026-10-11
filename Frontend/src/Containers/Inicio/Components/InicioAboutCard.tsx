import type { JSX } from "react";
import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import {
  InicioAboutCardShell,
  InicioAboutCtaSx,
  StyleTextCard,
  StyleTextCardSecondary,
} from "../../../styles/InicioStyles";

/**
 * Acceso institucional a `/acerca-de` (misma familia visual que cards de Inicio).
 */
export default function InicioAboutCard(): JSX.Element {
  return (
    <Box
      component={Link}
      to="/acerca-de"
      sx={{
        ...InicioAboutCardShell,
        textDecoration: "none",
        color: "inherit",
        display: "flex",
      }}
    >
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography sx={{ ...StyleTextCard, fontSize: { xs: "15px", md: "17px", lg: "18px" } }}>
          Acerca de Digitaliza
        </Typography>
        <Typography
          sx={{
            ...StyleTextCardSecondary,
            fontSize: { xs: "12px", md: "14px" },
            mt: 0.75,
            maxWidth: { md: "52rem" },
          }}
        >
          Digitaliza es una plataforma de apoyo a la gestión operativa, inspección, relevamiento y
          trazabilidad administrativa.
        </Typography>
      </Box>
      <Box
        component="span"
        sx={{
          ...InicioAboutCtaSx,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        CONOCER MÁS
      </Box>
    </Box>
  );
}
