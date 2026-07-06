import { Box, Typography } from "@mui/material";
import { moduleFiltersSurfaceSx } from "../../../styles/GlassStyles";

/** Ayuda compacta cuando el mapa manual aún no tiene domicilio seleccionado. */
export function DomicilioMapPlaceholder() {
  return (
    <Box
      sx={{
        ...moduleFiltersSurfaceSx,
        mt: 2,
        px: 2,
        py: 1.5,
        borderRadius: 2,
      }}
    >
      <Typography variant="body2" color="text.secondary">
        Seleccioná un domicilio y usá «Geolocalizar» para abrir el mapa y colocar o ajustar el pin manual.
      </Typography>
    </Box>
  );
}
