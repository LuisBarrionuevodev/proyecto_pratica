import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Box, Typography } from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import NavLeft from "../Componets/NavLeft";
import TopBar from "../Componets/TopBar";
import { TRANSITION, GLASS_COLORS } from "../styles/GlassStyles";
import { routeLabels } from "../constants/menuItems";
import { layoutShell } from "../theme/tokens";

const TOPBAR_HEIGHT = layoutShell.topBarHeightPx;
const SIDEBAR_COLLAPSED = layoutShell.sidebarCollapsedPx;
const SIDEBAR_EXPANDED = layoutShell.sidebarExpandedPx;
const OUTER_MARGIN = 12; // Margen exterior uniforme
// Altura del layout en desktop: 95vh (deja margen abajo como "app window")
const LAYOUT_HEIGHT = "calc(100vh - 24px)"; // 100vh menos margen arriba y abajo

/**
 * AppLayout - Layout principal estilo "app window"
 * 
 * En desktop: altura fija ~95vh, centrado con margen exterior
 * NavLeft y ContentShell tienen la misma altura y color
 */
const AppLayout = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const location = useLocation();

    const currentSidebarWidth = sidebarOpen ? SIDEBAR_EXPANDED : SIDEBAR_COLLAPSED;
    const currentLabel = routeLabels[location.pathname] || "Vista";

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
                <TopBar sidebarWidth={layoutShell.sidebarCollapsedPx} />
            </Box>

            {/* Contenedor principal con altura fija "app window" */}
            <Box
                sx={{
                    display: "flex",
                    marginTop: `${TOPBAR_HEIGHT}px`,
                    height: LAYOUT_HEIGHT,
                    overflow: "hidden",
                    padding: `${OUTER_MARGIN}px`,
                    paddingTop: 0,
                }}
            >
                {/* Sidebar - NavLeft */}
                <Box
                    component="nav"
                    sx={{
                        height: "100%",
                        flexShrink: 0,
                        width: currentSidebarWidth,
                        transition: TRANSITION.css,
                    }}
                >
                    <NavLeft onToggle={(open) => setSidebarOpen(open)} />
                </Box>

                {/* Main Content Area - ContentShell */}
                <Box
                    component="main"
                    sx={{
                        flex: 1,
                        marginLeft: "4px",
                        height: "100%",
                        overflow: "hidden",
                    }}
                >
                    {/* ContentShell - mismo color que NavLeft */}
                    <Box
                        sx={{
                            height: "100%",
                            backgroundColor: GLASS_COLORS.contentBg,
                            borderRadius: "16px",
                            border: `1px solid ${GLASS_COLORS.borderLight}`,
                            overflow: "hidden",
                            display: "flex",
                            flexDirection: "column",
                        }}
                    >
                        {/* Header breadcrumb "> Vista" */}
                        <Box
                            sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 0.5,
                                paddingX: 2.5,
                                paddingY: 1.25,
                                borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
                                flexShrink: 0,
                            }}
                        >
                            <ChevronRightIcon 
                                sx={{ 
                                    fontSize: 14, 
                                    color: GLASS_COLORS.textMuted,
                                }} 
                            />
                            <Typography
                                sx={{
                                    fontFamily: '"Tactic Sans", sans-serif',
                                    fontSize: "12px",
                                    fontWeight: 500,
                                    color: GLASS_COLORS.textSecondary,
                                    letterSpacing: "0.3px",
                                }}
                            >
                                {currentLabel}
                            </Typography>
                        </Box>

                        {/* Área scrolleable */}
                        <Box
                            sx={{
                                flex: 1,
                                overflowY: "auto",
                                overflowX: "auto",
                                "&::-webkit-scrollbar": {
                                    width: "6px",
                                },
                                "&::-webkit-scrollbar-track": {
                                    background: "transparent",
                                },
                                "&::-webkit-scrollbar-thumb": {
                                    backgroundColor: "rgba(255, 255, 255, 0.1)",
                                    borderRadius: "3px",
                                },
                                "&::-webkit-scrollbar-thumb:hover": {
                                    backgroundColor: "rgba(255, 255, 255, 0.18)",
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
