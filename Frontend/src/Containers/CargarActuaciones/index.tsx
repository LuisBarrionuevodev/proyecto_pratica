import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../Componets/NavLeft";
import TablaCargarActuacionesGlideStyled from "./Components/TablaCargarActuacionesGlideStyled";
import { darkTheme } from "../../configs/theme";

const CargarActuaciones = () => {
    return(
        <>
        <ThemeProvider theme={darkTheme}>
        <TablaCargarActuacionesGlideStyled/>
        </ThemeProvider>
        </>
    )
}

export default CargarActuaciones;