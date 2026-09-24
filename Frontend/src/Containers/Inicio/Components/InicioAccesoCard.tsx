import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import type { InicioAccesoItem } from "../inicioAccesosData";
import { InicioCardShellGrid, StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const iconStyles = {
  fontSize: "32px",
  color: GLASS_COLORS.primary,
  flexShrink: 0,
  mb: 0.25,
} as const;

type Props = { item: InicioAccesoItem };

/**
 * Card de acceso rápido (misma cáscara que el resto de la grilla de 9 en Inicio).
 */
export default function InicioAccesoCard({ item }: Props) {
  const { Icon } = item;
  return (
    <Link
      to={item.to}
      style={{ textDecoration: "none", display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <Box sx={{ ...InicioCardShellGrid, width: "100%", flex: 1 }}>
        <Icon sx={iconStyles} />
        <Typography sx={{ ...StyleTextCard, fontSize: "15px" }}>{item.title}</Typography>
        <Typography sx={{ ...StyleTextCardSecondary, fontSize: "12px", lineHeight: 1.45 }}>{item.description}</Typography>
      </Box>
    </Link>
  );
}
