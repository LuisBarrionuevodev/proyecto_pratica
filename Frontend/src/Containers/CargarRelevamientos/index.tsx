import { ThemeProvider } from "@mui/material";
import NavLeft from "../../Componets/NavLeft";
import TablaCargaRelevamientos from "./Components/TablaCargaRelevamientos";
import { darkTheme } from "../../configs/theme";

const CargarRelevamientos = () => {
    return (
    <>
    <ThemeProvider theme={darkTheme}>
    <TablaCargaRelevamientos/>
    </ThemeProvider>
    </>
    );
}

export default CargarRelevamientos;