import { ThemeProvider } from "@emotion/react";
import NavLeft from "../../../../Componets/NavLeft";
import TablaRelevamientos from "./Components/TablaRelevamientos";
import { darkTheme } from "../../../../configs/theme";

const Relevamientos = () => {
    return (
        <>
            <NavLeft />

            <ThemeProvider theme={darkTheme}>
                <TablaRelevamientos />
            </ThemeProvider>
        </>
    )
};

export default Relevamientos;