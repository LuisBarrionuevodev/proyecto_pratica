import { ThemeProvider } from "@mui/material";
import NavLeft from "../../Componets/NavLeft";
import TablaCargaRelevamientos from "./Components/TablaCargaRelevamientos";
import { darkTheme } from "../../configs/theme";

const CargarRelevamientos = () => {
    return (
    <>

    <NavLeft/>

    <ThemeProvider theme={darkTheme}>
    <TablaCargaRelevamientos/>
    </ThemeProvider>

    </>
    );
}

export default CargarRelevamientos;