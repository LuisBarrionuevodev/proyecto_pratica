import { Box, Slide } from "@mui/material";
import BoxCambiarInfo from "./Components/BoxCambiarInfo";
import BoxNombreUsuario from "./Components/BoxNombreUsuario";

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

            <BoxNombreUsuario

            // Esto despues se mandara o recibira de esta manera al backend:

                // nombre={user.nombre}
                // rol={user.rol}
                // avatarInicial={user.avatar}
                // onAvatarChange={(newAvatar) => {
                //     axios.put("/api/users/avatar", {
                //         userId: user.id,
                //         avatar: newAvatar,
                //     }); 
                // }}
                // onNameChange={(newName) => {
                //     axios.put("/api/user/name", { nombre: newName });
                // }}
            />

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