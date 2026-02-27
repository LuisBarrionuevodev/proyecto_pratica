import { useEffect, useState, type JSX } from "react";
import CardsInicio from "./Components/CardsInicio";
import TopBar from "../../Componets/TopBar";
import { Box, Slide, Typography } from "@mui/material";
import { GLASS_COLORS } from "../../styles/GlassStyles";
import { apiClient } from "../../api/apiClient";

type MeResponse = {
    user: {
        username: string;
    };
    profile: {
        nickname: string | null;
    };
};

/**
 * Inicio - Vista principal estilo Early Bird
 * - Hero transparente arriba con buscador (deja ver el fondo)
 * - Cards abajo en caja glass ocupando todo el ancho
 */
const Inicio = (): JSX.Element => {
    const [displayName, setDisplayName] = useState("Usuario");

    useEffect(() => {
        const fetchMe = async () => {
            try {
                const res = await apiClient.get<MeResponse>("/api/profile/me");
                setDisplayName(res.data.profile.nickname || res.data.user.username || "Usuario");
            } catch {
                setDisplayName("Usuario");
            }
        };
        fetchMe();
    }, []);

    return (
        <Box
            sx={{
                display: "flex",
                flexDirection: "column",
                height: "100vh",
                width: "100vw",
                overflow: "hidden",
                bgcolor: "transparent",
            }}
        >
            {/* TopBar fijo arriba */}
            <Box
                component="header"
                sx={{
                    height: "56px",
                    flexShrink: 0,
                    bgcolor: "transparent",
                }}
            >
                <TopBar  />
            </Box>

            {/* Hero Section - Transparente con buscador */}
            <Box
                sx={{
                    display: "flex",
                    flexDirection: "column",
                    height: "30%",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: { xs: 4, sm: 5, md: 6 },
                    backgroundColor: "transparent", // Deja ver el fondo
                }}
            >
                {/* Título opcional */}
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        fontSize: { xs: "24px", sm: "28px", md: "32px" },
                        fontWeight: 500,
                        color: "rgba(255, 255, 255, 0.9)",
                        marginBottom: 3,
                        textAlign: "center",
                    }}
                >
                    Bienvenido, {displayName}
                </Typography>
            </Box>

            {/* Cards Section - Al final, ocupando todo el ancho */}
            <Box
                sx={{
                    flex: 1,
                    backgroundColor: GLASS_COLORS.contentBg,
                    borderTopLeftRadius: "24px",
                    borderTopRightRadius: "24px",
                    border: `1px solid ${GLASS_COLORS.borderLight}`,
                    borderBottom: "none",
                    overflow: "auto",
                    "&::-webkit-scrollbar": {
                        width: "6px",
                    },
                    "&::-webkit-scrollbar-thumb": {
                        backgroundColor: "rgba(255, 255, 255, 0.1)",
                        borderRadius: "3px",
                    },
                }}
            >
                <Slide direction="up" in={true} appear timeout={400}>
                    <Box>
                        <CardsInicio />
                    </Box>
                </Slide>
            </Box>
        </Box>
    );
};

export default Inicio;