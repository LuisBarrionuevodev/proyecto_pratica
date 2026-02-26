import { Box, Slide } from "@mui/material";
import BoxCambiarInfo from "./Components/BoxCambiarInfo";
import BoxNombreUsuario from "./Components/BoxNombreUsuario";
import axios from "axios";

const Perfil = () => {

    const handlePasswordChange = async ({
    currentPassword,
    newPassword,
  }: {
    currentPassword: string;
    newPassword: string;
  }) => {
    try {
      await axios.put("http://localhost:3000/api/user/change-password", {
        currentPassword,
        newPassword,
      });

      console.log("Contraseña actualizada correctamente");
    } catch (error) {
      console.error("Error al cambiar contraseña", error);
    }
  };


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

                // user={user.user}
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
                        <BoxCambiarInfo onPasswordChange={handlePasswordChange} />
                    </Box>
                </Slide>
            </Box>
        </Box>
    );
};

export default Perfil;