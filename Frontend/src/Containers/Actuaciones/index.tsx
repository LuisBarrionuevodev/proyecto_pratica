import type { JSX } from "react"
import NavLeft from "../../Componets/NavLeft";
import TablaActuaciones from "./Components/TableActuaciones";
import { ThemeProvider } from "@mui/material";
import { darkTheme } from "../../configs/theme";

const Actuaciones = (): JSX.Element => {

    return (
        <>

            <NavLeft />

            <ThemeProvider theme={darkTheme}>
                <TablaActuaciones />
            </ThemeProvider>


        </>
    )

}

export default Actuaciones;