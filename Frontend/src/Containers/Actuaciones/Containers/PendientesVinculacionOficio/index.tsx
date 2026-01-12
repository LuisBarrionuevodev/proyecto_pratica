import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../../../Componets/NavLeft";
import { darkTheme } from "../../../../configs/theme";
import TablaPendientesVinculacionOficio from "./Components/TablaPendientesVinculacionOficio";

const PendientesVinculacionOficio = () => {
    return (
        <>
            <NavLeft />

            <ThemeProvider theme={darkTheme}>
                <TablaPendientesVinculacionOficio/>
            </ThemeProvider>
        </>
    )
};

export default PendientesVinculacionOficio;