import { Box } from "@mui/material";

import { CargarActuacionNuevaModal } from "./Components/CargarActuacionNuevaModal";
import { functionalPageShellSx } from "../../styles/functionalPageShell";

/**
 * Vista dedicada a la **carga inicial** de actas.
 * Card principal con mismo vidrio que barras F3.8c (sin tabs en página).
 */
const CargarActuaciones = () => {
  return (
    <Box sx={functionalPageShellSx}>
      <CargarActuacionNuevaModal />
    </Box>
  );
};

export default CargarActuaciones;
