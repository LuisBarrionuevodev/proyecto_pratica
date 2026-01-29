import { ThemeProvider } from "@emotion/react";
import { darkTheme } from "../../../../configs/theme";
import TablaPendientesVinculacionOficio from "./Components/TablaPendientesVinculacionOficio";

const PendientesVinculacionOficio = () => {
    return (
        <ThemeProvider theme={darkTheme}>
            <TablaPendientesVinculacionOficio />
        </ThemeProvider>
    );
};

export default PendientesVinculacionOficio;