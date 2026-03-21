import { useState } from "react";
import { Box, Paper, Tab, Tabs, Typography } from "@mui/material";
import TablaCargarRelevamientosGlideStyled from "./Components/TablaCargarRelevamientosGlideStyled";
import DenunciaForm from "./Components/DenunciaForm";
import { glassTabsHeaderPanelSx, GLASS_COLORS } from "../../styles/GlassStyles";

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
      <Paper elevation={0} sx={glassTabsHeaderPanelSx}>
        <Typography variant="body2" sx={{ mb: 2, color: GLASS_COLORS.textMuted, fontFamily: '"Tactic Sans", sans-serif' }}>
          Incluye relevamientos y denuncias
        </Typography>
        <Tabs value={section} onChange={(_, value) => setSection(value)} sx={{ marginBottom: 0 }}>
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
