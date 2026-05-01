import { Box } from "@mui/material";

import { CargarActuacionNuevaModal } from "./Components/CargarActuacionNuevaModal";

/**
 * Vista dedicada a la **carga inicial** de actas.
 * Flujo único: box + modal (motor grid: startBatch → validateRow → commitBatch).
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
