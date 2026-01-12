import type { JSX } from "react"
import CargaDeDatos from "./Components/CargaDeDatos";
import CardsInicio from "./Components/CardsInicio"

const Inicio = () : JSX.Element => {
    
    return(
        <>

        <CargaDeDatos/>

        <CardsInicio/>

        </>
    )

}

export default Inicio;