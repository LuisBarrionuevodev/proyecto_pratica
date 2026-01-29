import { Box, Typography, Avatar } from "@mui/material";
import FotoAvatar from "../../../assets/FotoAvatar.png";
import VerifiedIcon from "@mui/icons-material/Verified";

/**
 * BoxNombreUsuario - Hero Header estilo Spotify Profile
 * 
 * Estructura visual:
 * - Fondo con degradado oscuro
 * - Avatar grande a la izquierda
 * - Nombre grande + badge "Perfil verificado"
 */
const BoxNombreUsuario = () => {
    // const nombreUsuario = localStorage.getItem("Nombre de Usuario")
    const nombreUsuario = "Luis Barrionuevo";

    return (
        <Box
            sx={{
                // Degradado estilo Spotify profile header
                background: "linear-gradient(180deg, #3a3d44 0%, #2B2E34 50%, #1A1C20 100%)",
                minHeight: { xs: "180px", sm: "200px", md: "220px" },
                padding: { xs: 3, sm: 4, md: 5 },
                display: "flex",
                alignItems: "flex-end",
                gap: { xs: 2, sm: 3 },
            }}
        >
            {/* Avatar grande - estilo Spotify */}
            <Avatar
                src={FotoAvatar}
                alt={nombreUsuario}
                sx={{
                    width: { xs: 100, sm: 140, md: 180 },
                    height: { xs: 100, sm: 140, md: 180 },
                    border: "4px solid #1A1C20",
                    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
                }}
            />

            {/* Info del usuario */}
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 1,
                    pb: { xs: 1, sm: 2 },
                }}
            >
                {/* Badge "Perfil" */}
                <Box
                    sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.5,
                    }}
                >
                    <VerifiedIcon
                        sx={{
                            fontSize: { xs: 14, sm: 16 },
                            color: "#0166FF",
                        }}
                    />
                    <Typography
                        sx={{
                            fontFamily: '"Tactic Sans", sans-serif',
                            fontWeight: 500,
                            fontSize: { xs: "11px", sm: "12px" },
                            color: "#FFFFFF",
                            textTransform: "uppercase",
                            letterSpacing: "1px",
                        }}
                    >
                        Perfil verificado
                    </Typography>
                </Box>

                {/* Nombre grande */}
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        fontWeight: 800,
                        fontSize: { xs: "28px", sm: "42px", md: "56px", lg: "64px" },
                        color: "#FFFFFF",
                        lineHeight: 1.1,
                        letterSpacing: "-1px",
                    }}
                >
                    {nombreUsuario}
                </Typography>

                {/* Subtítulo opcional */}
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        fontWeight: 400,
                        fontSize: { xs: "12px", sm: "14px" },
                        color: "rgba(255, 255, 255, 0.7)",
                        mt: 0.5,
                    }}
                >
                    Administrador • SMT Digitaliza
                </Typography>
            </Box>
        </Box>
    );
};

export default BoxNombreUsuario;