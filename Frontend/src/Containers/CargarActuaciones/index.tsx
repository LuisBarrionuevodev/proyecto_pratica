import { Box, Paper, Tab, Tabs } from "@mui/material";
import { useState } from "react";
import TablaCargarActuacionesGlideStyled from "./Components/TablaCargarActuacionesGlideStyled";
import PendientesExpedienteView from "../Actuaciones/Components/PendientesExpedienteView";
import PendientesOficioView from "../Actuaciones/Components/PendientesOficioView";
import { glassTabsHeaderPanelSx } from "../../styles/GlassStyles";

type CargarActuacionesSubview = "actas_comprobacion" | "pendientes_expediente" | "esperando_oficio";

const CargarActuaciones = () => {
  const [subview, setSubview] = useState<CargarActuacionesSubview>("actas_comprobacion");

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
      <Paper elevation={0} sx={glassTabsHeaderPanelSx}>
        <Tabs
          value={subview}
          onChange={(_, value) => setSubview(value)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={{ marginBottom: 0 }}
        >
          <Tab label="Actas / Comprobación" value="actas_comprobacion" />
          <Tab label="Pendientes de expediente" value="pendientes_expediente" />
          <Tab label="Esperando oficio" value="esperando_oficio" />
        </Tabs>
      </Paper>

      {subview === "actas_comprobacion" && <TablaCargarActuacionesGlideStyled />}
      {subview === "pendientes_expediente" && <PendientesExpedienteView />}
      {subview === "esperando_oficio" && <PendientesOficioView />}
    </Box>
  );
};

export default CargarActuaciones;
