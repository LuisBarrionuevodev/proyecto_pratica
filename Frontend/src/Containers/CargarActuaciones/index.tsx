import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../Componets/NavLeft";
import TablaCargarActuaciones from "./Components/TablaCargarActuaciones";
import { darkTheme } from "../../configs/theme";

const CargarActuaciones = () => {
    return(
        <>

        <NavLeft/>

        <ThemeProvider theme={darkTheme}>
        <TablaCargarActuaciones/>
        </ThemeProvider>
        </>
    )
}

export default CargarActuaciones;