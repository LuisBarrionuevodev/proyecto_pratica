import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import type { JSX } from "react";
import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import {
  InicioAboutCardShell,
  StyleTextCard,
  StyleTextCardSecondary,
} from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const infoIconSx = {
  fontSize: { xs: "28px", md: "32px" },
  color: GLASS_COLORS.primary,
  flexShrink: 0,
} as const;

/**
 * Acceso institucional a `/acerca-de` (misma familia visual que cards de Inicio).
 */
export default function InicioAboutCard(): JSX.Element {
  return (
    <Box
      component={Link}
      to="/acerca-de"
      aria-label="Acerca de Digitaliza"
      sx={{
        ...InicioAboutCardShell,
        textDecoration: "none",
        color: "inherit",
        display: "flex",
        flexDirection: { xs: "column", md: "row" },
        alignItems: { xs: "flex-start", md: "center" },
        gap: { xs: 1, md: 1.5 },
        "&:focus-visible": {
          outline: `2px solid ${GLASS_COLORS.primary}`,
          outlineOffset: 2,
        },
      }}
    >
      <InfoOutlinedIcon sx={infoIconSx} aria-hidden />
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
    </Box>
  );
}
