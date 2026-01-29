import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Box } from "@mui/material";
import NavLeft from "../Componets/NavLeft";
import TopBar from "../Componets/TopBar";

// Constantes de dimensiones (estilo Spotify)
const TOPBAR_HEIGHT = 70;
const SIDEBAR_COLLAPSED = 80;
const SIDEBAR_EXPANDED = 240;

// Colores base estilo Spotify (NavLeft y ContentShell mismo color)
const COLORS = {
    // Fondo compartido entre sidebar y content
    baseBg: "#1A1C20",
    // Borde sutil
    border: "#3a3d44",
};

/**
 * AppLayout - Layout principal estilo Spotify
 * 
 * Estructura:
 * - TopBar fijo arriba
 * - NavLeft (sidebar) fijo a la izquierda
 * - ContentShell (main) con scroll interno
 * 
 * El body NO scrollea, solo el ContentShell.
 */
const AppLayout = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const currentSidebarWidth = sidebarOpen ? SIDEBAR_EXPANDED : SIDEBAR_COLLAPSED;

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
                    position: "fixed",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: TOPBAR_HEIGHT,
                    zIndex: 1200,
                    bgcolor: "transparent",
                }}
            >
                <TopBar />
            </Box>

            {/* Contenedor principal (sidebar + content) */}
            <Box
                sx={{
                    display: "flex",
                    flex: 1,
                    marginTop: `${TOPBAR_HEIGHT}px`,
                    height: `calc(100vh - ${TOPBAR_HEIGHT}px)`,
                    overflow: "hidden",
                }}
            >
                {/* Sidebar - NavLeft */}
                <Box
                    component="nav"
                    sx={{
                        position: "fixed",
                        top: TOPBAR_HEIGHT,
                        left: 0,
                        height: `calc(100vh - ${TOPBAR_HEIGHT}px)`,
                        zIndex: 1100,
                    }}
                >
                    <NavLeft onToggle={(open) => setSidebarOpen(open)} />
                </Box>

                {/* Main Content Area - ContentShell */}
                <Box
                    component="main"
                    sx={{
                        flex: 1,
                        marginLeft: `${currentSidebarWidth + 15}px`, // +15 para el margin del drawer
                        transition: "margin-left 0.3s ease-in-out",
                        height: "100%",
                        overflow: "hidden",
                        padding: "12px 16px 16px 8px",
                    }}
                >
                    {/* ContentShell - mismo color que NavLeft */}
                    <Box
                        sx={{
                            height: "100%",
                            bgcolor: COLORS.baseBg,
                            borderRadius: "16px",
                            border: `1px solid ${COLORS.border}`,
                            boxShadow: "0 4px 24px rgba(0, 0, 0, 0.3)",
                            overflow: "hidden",
                            display: "flex",
                            flexDirection: "column",
                        }}
                    >
                        {/* Área scrolleable */}
                        <Box
                            sx={{
                                flex: 1,
                                overflowY: "auto",
                                overflowX: "hidden",
                                // Scrollbar estilo Spotify
                                "&::-webkit-scrollbar": {
                                    width: "12px",
                                },
                                "&::-webkit-scrollbar-track": {
                                    background: "#121212",
                                    borderRadius: "6px",
                                },
                                "&::-webkit-scrollbar-thumb": {
                                    backgroundColor: "#3a3d44",
                                    borderRadius: "6px",
                                    border: "3px solid #121212",
                                },
                                "&::-webkit-scrollbar-thumb:hover": {
                                    backgroundColor: "#535353",
                                },
                            }}
                        >
                            <Outlet />
                        </Box>
                    </Box>
                </Box>
            </Box>
        </Box>
    );
};

export default AppLayout;
