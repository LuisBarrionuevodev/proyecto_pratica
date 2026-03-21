import { Box, Grid, Stack } from "@mui/material";
import type { JSX } from "react";

import { INICIO_ACCESOS } from "../inicioAccesosData";
import InicioAccesoCard from "./InicioAccesoCard";
import InicioActasPendientesCompactCard from "./InicioActasPendientesCompactCard";
import InicioIndicadoresCompactCard from "./InicioIndicadoresCompactCard";
import InicioRutaHoyCard from "./InicioRutaHoyCard";

const GAP = 2;

/**
 * Bloque de 9 cards: en md+ grilla 3×3 (2 columnas accesos + 1 operativa), filas con misma altura;
 * las tres de la derecha quedan iguales entre sí y alineadas arriba/abajo con las seis de la izquierda.
 * En xs: seis accesos en 2 columnas y debajo las tres operativas.
 */
export default function InicioOperacionesGrid(): JSX.Element {
  return (
    <>
      {/* Mobile / tablet: 6 + 3 apilados */}
      <Box sx={{ display: { xs: "block", md: "none" } }}>
        <Grid container spacing={GAP} sx={{ mb: GAP }}>
          {INICIO_ACCESOS.map((item) => (
            <Grid key={item.to} size={{ xs: 12, sm: 6 }}>
              <InicioAccesoCard item={item} />
            </Grid>
          ))}
        </Grid>
        <Stack spacing={GAP}>
          <InicioRutaHoyCard />
          <InicioActasPendientesCompactCard />
          <InicioIndicadoresCompactCard />
        </Stack>
      </Box>

      {/* Desktop: 3 filas × 3 columnas — orden fila: izq, izq, der */}
      <Box
        sx={{
          display: { xs: "none", md: "grid" },
          gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1.1fr) minmax(0, 4fr)",
          gridTemplateRows: "repeat(3, minmax(0, 1fr))",
          gap: GAP,
          minHeight: "clamp(380px, 44vh, 720px)",
          alignItems: "stretch",
        }}
      >
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioAccesoCard item={INICIO_ACCESOS[0]} />
        </Box>
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioAccesoCard item={INICIO_ACCESOS[1]} />
        </Box>
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioRutaHoyCard />
        </Box>

        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioAccesoCard item={INICIO_ACCESOS[2]} />
        </Box>
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioAccesoCard item={INICIO_ACCESOS[3]} />
        </Box>
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioActasPendientesCompactCard />
        </Box>

        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioAccesoCard item={INICIO_ACCESOS[4]} />
        </Box>
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioAccesoCard item={INICIO_ACCESOS[5]} />
        </Box>
        <Box sx={{ minWidth: 0, minHeight: 0, display: "flex" }}>
          <InicioIndicadoresCompactCard />
        </Box>
      </Box>
    </>
  );
}
