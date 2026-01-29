import type { JSX } from "react";
import CargaDeDatos from "./Components/CargaDeDatos";
import CardsInicio from "./Components/CardsInicio";
import TopBar from "../../Componets/TopBar";
import { Box, Slide, Typography } from "@mui/material";
import { GLASS_COLORS } from "../../styles/GlassStyles";

/**
 * Inicio - Vista principal estilo Early Bird
 * - Hero transparente arriba con buscador (deja ver el fondo)
 * - Cards abajo en caja glass ocupando todo el ancho
 */
const Inicio = (): JSX.Element => {
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
                    ¿En qué podemos ayudarte, teo?
                </Typography>
                
                {/* Buscador */}
                <CargaDeDatos />
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