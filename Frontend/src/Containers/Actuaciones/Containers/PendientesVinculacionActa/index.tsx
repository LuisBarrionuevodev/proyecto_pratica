import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../../../Componets/NavLeft";
import { darkTheme } from "../../../../configs/theme";
import TablaPendientesVinculacionActa from "./Components/TablaPendientesVinculacionActa";

const PendientesVinculacionActa = () => {
    return (
        <>
            <NavLeft />

            <ThemeProvider theme={darkTheme}>
                <TablaPendientesVinculacionActa/>
            </ThemeProvider>
        </>
    )
};

export default PendientesVinculacionActa;