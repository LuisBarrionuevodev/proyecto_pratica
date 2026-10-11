import type { JSX } from "react";
import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import type { InicioAccesoItem } from "../inicioAccesosData";
import { InicioMapaHeroShellSx, InicioMapaHeroTextSx } from "../../../styles/InicioStyles";
import { CSS_VAR_NAMES } from "../../../theme/applyCssVariables";
import mapaPreview from "../../../assets/mapa.jpg";

type Props = { item: InicioAccesoItem };

/**
 * Fila desktop dedicada al acceso Mapa (imagen principal + texto claro sobre la zona visual).
 */
export default function InicioMapaHeroCard({ item }: Props): JSX.Element {
  const { Icon } = item;
  const onImage = `var(${CSS_VAR_NAMES.primitiveWhite})`;

  return (
    <Link
      to={item.to}
      style={{ textDecoration: "none", display: "flex", width: "100%", minHeight: 0 }}
    >
      <Box
        sx={{
          ...InicioMapaHeroShellSx,
          backgroundImage: `url(${mapaPreview})`,
        }}
      >
        <Box sx={{ position: "relative", zIndex: 1, flex: 1, minWidth: 0, maxWidth: { md: "58%", lg: "52%" } }}>
          <Icon sx={{ fontSize: { md: 36, lg: 40 }, color: onImage, mb: 1 }} />
          <Typography
            sx={{
              ...InicioMapaHeroTextSx,
              fontSize: { md: "1.25rem", lg: "1.35rem" },
              color: onImage,
            }}
          >
            {item.title}
          </Typography>
          <Typography
            sx={{
              ...InicioMapaHeroTextSx,
              fontWeight: 400,
              fontSize: { md: "0.9375rem", lg: "1rem" },
              mt: 0.75,
              color: onImage,
              opacity: 0.95,
            }}
          >
            {item.description}
          </Typography>
        </Box>
      </Box>
    </Link>
  );
}
