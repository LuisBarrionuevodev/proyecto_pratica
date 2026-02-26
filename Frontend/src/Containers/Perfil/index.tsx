import { Box, Slide } from "@mui/material";
import { useEffect, useState } from "react";
import BoxCambiarInfo from "./Components/BoxCambiarInfo";
import BoxNombreUsuario from "./Components/BoxNombreUsuario";
import { apiClient } from "../../api/apiClient";

type MeResponse = {
  user: {
    id: number;
    username: string;
    email: string;
    role: "admin" | "usuario";
  };
  profile: {
    nickname: string | null;
    avatar_key: "avatar1" | "avatar2" | "avatar3" | "avatar4" | "avatar5";
  };
};

const Perfil = () => {
  const [me, setMe] = useState<MeResponse | null>(null);

  const fetchMe = async () => {
    try {
      const res = await apiClient.get<MeResponse>("/api/profile/me");
      setMe(res.data);
    } catch (error) {
      console.error("Error al cargar perfil", error);
    }
  };

  useEffect(() => {
    fetchMe();
  }, []);

    const handlePasswordChange = async ({
    currentPassword,
    newPassword,
  }: {
    currentPassword: string;
    newPassword: string;
  }) => {
    try {
      await apiClient.post("/api/profile/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
        new_password2: newPassword,
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
                user={me?.user.username ?? ""}
                nombre={me?.profile.nickname ?? ""}
                rol={me?.user.role === "admin" ? "Administrador" : "Usuario"}
                avatarInicial={me?.profile.avatar_key ?? "avatar1"}
                onAvatarChange={async (newAvatar) => {
                    try {
                        await apiClient.patch("/api/profile/me", { avatar_key: newAvatar });
                        await fetchMe();
                        window.dispatchEvent(new Event("profile:updated"));
                    } catch (error) {
                        console.error("Error al actualizar avatar", error);
                    }
                }}
                onNameChange={async (newName) => {
                    try {
                        await apiClient.patch("/api/profile/me", { nickname: newName });
                        await fetchMe();
                        window.dispatchEvent(new Event("profile:updated"));
                    } catch (error) {
                        console.error("Error al actualizar nickname", error);
                    }
                }}
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