import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../../../Componets/NavLeft";
import { darkTheme } from "../../../../configs/theme";
import TablaPendientes from "./Components/TablaPendientes";

const Pendientes = () => {
    return (
        <>
            <NavLeft />

            <ThemeProvider theme={darkTheme}>
                <TablaPendientes/>
            </ThemeProvider>
        </>
    )
};

export default Pendientes;