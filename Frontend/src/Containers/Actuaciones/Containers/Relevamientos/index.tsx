import { ThemeProvider } from "@emotion/react";
import TablaRelevamientos from "./Components/TablaRelevamientos";
import { darkTheme } from "../../../../configs/theme";

const Relevamientos = () => {
    return (
        <ThemeProvider theme={darkTheme}>
            <TablaRelevamientos />
        </ThemeProvider>
    );
};

export default Relevamientos;