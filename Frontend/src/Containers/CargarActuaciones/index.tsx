import { Box } from "@mui/material";

import TablaCargarActuacionesGlideStyled from "./Components/TablaCargarActuacionesGlideStyled";
import { CargarActuacionesHowTo } from "./Components/CargarActuacionesHowTo";

/**
 * Vista dedicada a la **carga inicial** de actas (batch Glide).
 * La grilla incluye columnas de notificación y comprobación a la vez.
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
            <TablaCargarActuacionesGlideStyled showHowTo={false} />

            <CargarActuacionesHowTo />
        </Box>
    );
};

export default CargarActuaciones;
