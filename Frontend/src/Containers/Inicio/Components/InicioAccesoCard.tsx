import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import type { InicioAccesoItem } from "../inicioAccesosData";
import {
  InicioAccesoCardDescriptionSx,
  InicioAccesoCardTitleSx,
  InicioCardShellGrid,
  InicioCardShellGridDesktop,
} from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const iconStyles = {
  fontSize: "32px",
  color: GLASS_COLORS.primary,
  flexShrink: 0,
  mb: 0.25,
} as const;

type Props = { item: InicioAccesoItem; variant?: "compact" | "desktop" };

/**
 * Card de acceso rápido (misma cáscara que el resto de la grilla de 9 en Inicio).
 */
export default function InicioAccesoCard({ item, variant = "desktop" }: Props) {
  const { Icon } = item;
  const titleSx =
    variant === "desktop" ? InicioAccesoCardTitleSx : { ...InicioAccesoCardTitleSx, fontSize: "15px" };
  const descriptionSx =
    variant === "desktop"
      ? InicioAccesoCardDescriptionSx
      : { ...InicioAccesoCardDescriptionSx, fontSize: "12px" };
  return (
    <Link
      to={item.to}
      style={{ textDecoration: "none", display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <Box
        sx={{
          ...InicioCardShellGrid,
          ...(variant === "desktop" ? InicioCardShellGridDesktop : {}),
          width: "100%",
          flex: 1,
        }}
      >
        <Icon sx={iconStyles} />
        <Typography sx={titleSx}>{item.title}</Typography>
        <Typography sx={descriptionSx}>{item.description}</Typography>
      </Box>
    </Link>
  );
}
