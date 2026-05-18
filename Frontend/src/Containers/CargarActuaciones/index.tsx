import { Box } from "@mui/material";

import { CargarActuacionNuevaModal } from "./Components/CargarActuacionNuevaModal";

/**
 * Vista dedicada a la **carga inicial** de actas.
 * Card principal con mismo vidrio que barras F3.8c (sin tabs en página).
 */
const CargarActuaciones = () => {
  return (
    <Box
      sx={{
        width: "100%",
        p: { xs: 2, sm: 3 },
        display: "flex",
        flexDirection: "column",
        gap: 2,
        boxSizing: "border-box",
      }}
    >
      <CargarActuacionNuevaModal />
    </Box>
  );
};

export default CargarActuaciones;
