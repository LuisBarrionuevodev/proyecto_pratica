import { ThemeProvider } from "@emotion/react";
import { darkTheme } from "../../configs/theme";
import TablaCargarRelevamientosGlideStyled from "./Components/TablaCargarRelevamientosGlideStyled";

const CargarRelevamientos = () => {
  return (
    <ThemeProvider theme={darkTheme}>
      <TablaCargarRelevamientosGlideStyled />
    </ThemeProvider>
  );
};

export default CargarRelevamientos;