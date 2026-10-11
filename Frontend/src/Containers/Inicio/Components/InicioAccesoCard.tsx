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
import { CSS_VAR_NAMES } from "../../../theme/applyCssVariables";
import mapaPreview from "../../../assets/mapa.jpg";
import { MAPA_PATH } from "../../../auth/roles";

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
  const isMapCard = item.to === MAPA_PATH;
  return (
    <Link
      to={item.to}
      style={{ textDecoration: "none", display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <Box
        sx={{
          ...InicioCardShellGrid,
          ...InicioCardShellGridDesktop,
          width: "100%",
          flex: 1,
          position: "relative",
          overflow: "hidden",
          ...(isMapCard
            ? {
                backgroundImage: `url(${mapaPreview})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
                "&::before": {
                  content: '""',
                  position: "absolute",
                  inset: 0,
                  borderRadius: "inherit",
                  backgroundColor: `var(${CSS_VAR_NAMES.surfaceOverlay})`,
                  opacity: 0.88,
                  pointerEvents: "none",
                },
                "& > *": {
                  position: "relative",
                  zIndex: 1,
                },
              }
            : {}),
        }}
      >
        <Icon sx={iconStyles} />
        <Typography sx={InicioAccesoCardTitleSx}>{item.title}</Typography>
        <Typography sx={InicioAccesoCardDescriptionSx}>{item.description}</Typography>
      </Box>
    </Link>
  );
}
