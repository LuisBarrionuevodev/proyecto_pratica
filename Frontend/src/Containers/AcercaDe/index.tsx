import type { JSX } from "react";
import { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import TopBar from "../../Componets/TopBar";
import { setBodyAuthenticatedRoute } from "../../theme/bodyRouteClass";
import { CSS_VAR_NAMES } from "../../theme/applyCssVariables";
import {
  acercaDeBackButtonSx,
  acercaDeBodySx,
  acercaDeContentSx,
  acercaDePageSx,
  acercaDeScrollSx,
  acercaDeSectionSx,
  acercaDeSectionTitleSx,
  acercaDeTitleSx,
} from "../../styles/AcercaDeStyles";

const SECTIONS: { title: string; body: string }[] = [
  {
    title: "Acerca de Digitaliza",
    body: "Digitaliza es una plataforma de apoyo a la gestión operativa, inspección, relevamiento y trazabilidad administrativa. Integra cargas de campo, actuaciones, mapas y seguimiento de gestiones en un entorno unificado para equipos de trabajo.",
  },
  {
    title: "Propósito",
    body: "Facilitar el relevamiento, las actuaciones, las inspecciones, el registro de evidencias y el seguimiento operativo diario, con trazabilidad entre tareas, domicilios y documentación asociada.",
  },
  {
    title: "Uso institucional",
    body: "La plataforma está pensada para apoyar procesos de gestión y control en contextos de inspección y administración pública. Los alcances concretos de titularidad, operación y responsabilidad se formalizan con el organismo correspondiente.",
  },
  {
    title: "Derechos de autor y licencia",
    body: "La información sobre derechos de autor, condiciones de uso y licencia se encuentra en proceso de formalización.",
  },
];

/**
 * Pantalla institucional `/acerca-de` (solo frontend, responsive).
 */
export default function AcercaDe(): JSX.Element {
  useEffect(() => {
    setBodyAuthenticatedRoute(true);
    return () => setBodyAuthenticatedRoute(false);
  }, []);

  return (
    <Box sx={acercaDePageSx}>
      <Box component="header" sx={{ height: 56, flexShrink: 0, bgcolor: "transparent" }}>
        <TopBar />
      </Box>

      <Box
        sx={{
          ...acercaDeScrollSx,
          "&::-webkit-scrollbar": { width: "6px" },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: `var(${CSS_VAR_NAMES.scrollbarThumb})`,
            borderRadius: "3px",
          },
        }}
      >
        <Box sx={acercaDeContentSx}>
          <Typography component="h1" sx={acercaDeTitleSx}>
            Acerca de Digitaliza
          </Typography>

          {SECTIONS.map((section) => (
            <Box key={section.title} component="section" sx={acercaDeSectionSx}>
              <Typography component="h2" sx={acercaDeSectionTitleSx}>
                {section.title}
              </Typography>
              <Typography sx={acercaDeBodySx}>{section.body}</Typography>
            </Box>
          ))}

          <Box
            component={Link}
            to="/inicio"
            sx={{
              ...acercaDeBackButtonSx,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            VOLVER AL INICIO
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
