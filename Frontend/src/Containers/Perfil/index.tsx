import { Box, Slide } from "@mui/material";
import BoxCambiarInfo from "./Components/BoxCambiarInfo";
import BoxNombreUsuario from "./Components/BoxNombreUsuario";

/**
 * Perfil - Layout estilo Spotify Profile
 * 
 * Estructura:
 * 1. Hero header con degradado oscuro (BoxNombreUsuario)
 * 2. Avatar grande + nombre a la izquierda
 * 3. Formulario de cambio de contraseña centrado abajo
 * 
 * Nota: NavLeft y TopBar vienen del AppLayout (no se importan aquí)
 */
const Perfil = () => {
    return (
        <Box
            sx={{
                display: "flex",
                flexDirection: "column",
                minHeight: "100%",
                bgcolor: "transparent",
            }}
        >
            {/* Hero Header - estilo Spotify profile */}
            <BoxNombreUsuario />
            
            {/* Contenido principal - Form centrado */}
            <Box
                sx={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    padding: { xs: 2, sm: 4 },
                    bgcolor: "transparent",
                }}
            >
                <Slide
                    direction="up"
                    in={true}
                    appear
                    timeout={600}
                >
                    <Box
                        sx={{
                            width: "100%",
                            maxWidth: "550px",
                            mt: { xs: 2, sm: 3 },
                        }}
                    >
                        <BoxCambiarInfo />
                    </Box>
                </Slide>
            </Box>
        </Box>
    );
};

export default Perfil;