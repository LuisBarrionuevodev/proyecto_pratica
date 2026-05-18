import { useState } from "react";
import { Box, Paper, Tab, Tabs } from "@mui/material";
import TablaCargarRelevamientosGlideStyled from "./Components/TablaCargarRelevamientosGlideStyled";
import DenunciaForm from "./Components/DenunciaForm";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";

const CargarRelevamientos = () => {
  const [section, setSection] = useState<"relevamientos" | "denuncias">("relevamientos");

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
      <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
        <Tabs value={section} onChange={(_, value) => setSection(value)} sx={moduleSlicesTabsSx}>
          <Tab label="Relevamientos" value="relevamientos" />
          <Tab label="Denuncias" value="denuncias" />
        </Tabs>
      </Paper>

      {section === "relevamientos" ? (
        <TablaCargarRelevamientosGlideStyled showTitle={false} />
      ) : (
        <DenunciaForm showTitle={false} />
      )}
    </Box>
  );
};

export default CargarRelevamientos;
