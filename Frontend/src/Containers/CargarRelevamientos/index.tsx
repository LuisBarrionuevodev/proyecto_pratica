import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../Componets/NavLeft";
import { darkTheme } from "../../configs/theme";
import TablaCargarRelevamientosGlideStyled from "./Components/TablaCargarRelevamientosGlideStyled";

const CargarRelevamientos = () => {
  return (
    <>
      <NavLeft />
      <ThemeProvider theme={darkTheme}>
        <TablaCargarRelevamientosGlideStyled />
      </ThemeProvider>
    </>
  );
};

export default CargarRelevamientos;