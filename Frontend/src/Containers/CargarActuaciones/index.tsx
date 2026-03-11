import { ThemeProvider } from "@emotion/react";
import { Box, Tab, Tabs, Typography } from "@mui/material";
import { useState } from "react";
import TablaCargarActuacionesGlideStyled from "./Components/TablaCargarActuacionesGlideStyled";
import { darkTheme } from "../../configs/theme";
import PendientesExpedienteView from "../Actuaciones/Components/PendientesExpedienteView";
import PendientesOficioView from "../Actuaciones/Components/PendientesOficioView";

type CargarActuacionesSubview = "actas_comprobacion" | "pendientes_expediente" | "esperando_oficio";

const CargarActuaciones = () => {
    const [subview, setSubview] = useState<CargarActuacionesSubview>("actas_comprobacion");

    return (
        <ThemeProvider theme={darkTheme}>
            <Box sx={{ width: "100%" }}>
                <Typography sx={{ color: "#fff", fontWeight: 700, mb: 2, fontSize: "28px" }}>
                    Cargar Actuaciones
                </Typography>
                <Tabs
                    value={subview}
                    onChange={(_, value) => setSubview(value)}
                    sx={{ marginBottom: 2 }}
                    variant="scrollable"
                    allowScrollButtonsMobile
                >
                    <Tab label="Actas / Comprobación" value="actas_comprobacion" />
                    <Tab label="Pendientes de expediente" value="pendientes_expediente" />
                    <Tab label="Esperando oficio" value="esperando_oficio" />
                </Tabs>

                {subview === "actas_comprobacion" && <TablaCargarActuacionesGlideStyled />}
                {subview === "pendientes_expediente" && <PendientesExpedienteView />}
                {subview === "esperando_oficio" && <PendientesOficioView />}
            </Box>
        </ThemeProvider>
    );
};

export default CargarActuaciones;