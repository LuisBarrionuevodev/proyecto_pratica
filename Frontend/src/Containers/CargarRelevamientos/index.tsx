import { useState } from "react";
import { ThemeProvider } from "@emotion/react";
import { Box, Tab, Tabs, Typography } from "@mui/material";
import { darkTheme } from "../../configs/theme";
import TablaCargarRelevamientosGlideStyled from "./Components/TablaCargarRelevamientosGlideStyled";
import DenunciaForm from "./Components/DenunciaForm";

const CargarRelevamientos = () => {
  const [section, setSection] = useState<"relevamientos" | "denuncias">("relevamientos");

  return (
    <ThemeProvider theme={darkTheme}>
      <Box sx={{ width: "100%", p: { xs: 2, sm: 3 } }}>
        <Typography
          sx={{
            color: "#fff",
            fontWeight: 700,
            fontSize: { xs: "1.05rem", sm: "1.2rem" },
            mb: 2,
          }}
        >
          Cargar iniciadores principales
        </Typography>

        <Tabs
          value={section}
          onChange={(_, value) => setSection(value)}
          sx={{ marginBottom: 2 }}
        >
          <Tab label="Relevamientos" value="relevamientos" />
          <Tab label="Denuncias" value="denuncias" />
        </Tabs>

        {section === "relevamientos" ? (
          <TablaCargarRelevamientosGlideStyled showTitle={false} />
        ) : (
          <DenunciaForm showTitle={false} />
        )}
      </Box>
    </ThemeProvider>
  );
};

export default CargarRelevamientos;