import { Box, Grid, Stack } from "@mui/material";
import type { JSX } from "react";

import { INICIO_ACCESOS } from "../inicioAccesosData";
import InicioAccesoCard from "./InicioAccesoCard";

const GAP = 2;

/**
 * Accesos rápidos (12 cards) alineados al menú lateral — sin duplicados compactos.
 */
export default function InicioOperacionesGrid(): JSX.Element {
  return (
    <Stack spacing={GAP}>
      <Grid container spacing={GAP}>
        {INICIO_ACCESOS.map((item) => (
          <Grid key={item.to} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
            <InicioAccesoCard item={item} />
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}
