import { ThemeProvider } from "@emotion/react";
import { darkTheme } from "../../../../configs/theme";
import TablaPendientes from "./Components/TablaPendientes";

const Pendientes = () => {
    return (
        <ThemeProvider theme={darkTheme}>
            <TablaPendientes />
        </ThemeProvider>
    );
};

export default Pendientes;