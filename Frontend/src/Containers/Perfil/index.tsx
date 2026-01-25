import { Box, Slide } from "@mui/material";
import BoxCambiarInfo from "./Components/BoxCambiarInfo";
import BoxNombreUsuario from "./Components/BoxNombreUsuario";

const Perfil = () => {
    return (
        <>
            <BoxNombreUsuario />


                <Slide
                    direction="right"
                    in={true}
                    appear
                    timeout={1000}
                ><Box>
                    <BoxCambiarInfo />
                </Box>
                </Slide>
            
        </>
    )
}

export default Perfil;