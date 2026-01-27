import type { JSX } from "react"
import CargaDeDatos from "./Components/CargaDeDatos";
import CardsInicio from "./Components/CardsInicio"
import { Box, Slide } from "@mui/material";

const Inicio = (): JSX.Element => {

    return (
        <>
        <Box bgcolor={"white"}>
            <CargaDeDatos />

            <Slide
                direction="right"
                in={true}
                appear
                timeout={800}>
                <Box>
                    <CardsInicio />
                </Box>
            </Slide>
        </Box>
        </>
    )

}

export default Inicio;