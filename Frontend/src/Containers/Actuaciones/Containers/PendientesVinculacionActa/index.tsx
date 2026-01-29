import { ThemeProvider } from "@emotion/react";
import { darkTheme } from "../../../../configs/theme";
import TablaPendientesVinculacionActa from "./Components/TablaPendientesVinculacionActa";

const PendientesVinculacionActa = () => {
    return (
        <ThemeProvider theme={darkTheme}>
            <TablaPendientesVinculacionActa />
        </ThemeProvider>
    );
};

export default PendientesVinculacionActa;