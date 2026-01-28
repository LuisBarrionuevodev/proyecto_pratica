import { Box, Slide } from "@mui/material";
import BoxCambiarInfo from "./Components/BoxCambiarInfo";
import BoxNombreUsuario from "./Components/BoxNombreUsuario";
import NavLeft from "../../Componets/NavLeft";
import TopBar from "../../Componets/TopBar";

const Perfil = () => {
    return (
        <>
        
            <BoxNombreUsuario />
            <Slide
                direction="right"
                in={true}
                appear
                timeout={1000}
            ><Box display={"flex"} justifyContent={"center"}>
                    <BoxCambiarInfo />
                </Box>
            </Slide>
        </>
    )
}

export default Perfil;