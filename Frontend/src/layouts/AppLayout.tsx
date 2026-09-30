import { useEffect, useState } from "react";
import { setBodyAuthenticatedRoute } from "../theme/bodyRouteClass";
import { Outlet, useLocation } from "react-router-dom";
import { resolveBreadcrumbLabel } from "../utils/breadcrumbLabel";
import { Box } from "@mui/material";
import { InstitutionalViewHeaderBar } from "./InstitutionalViewHeaderBar";
import NavLeft from "../Componets/NavLeft";
import TopBar from "../Componets/TopBar";
import { RoleRouteGuard } from "./RoleRouteGuard";
import { TRANSITION, glassContent } from "../styles/GlassStyles";
import { CSS_VAR_NAMES } from "../theme/applyCssVariables";
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
    const currentLabel = resolveBreadcrumbLabel(location.pathname);

    useEffect(() => {
        setBodyAuthenticatedRoute(true);
        return () => setBodyAuthenticatedRoute(false);
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
                            ...glassContent,
                            height: "100%",
                            borderRadius: "16px",
                            overflow: "hidden",
                            display: "flex",
                            flexDirection: "column",
                        }}
                    >
                        {/* Header institucional: vista + fecha de hoy (F3.8a) */}
                        <InstitutionalViewHeaderBar title={currentLabel} />

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
                                    backgroundColor: `var(${CSS_VAR_NAMES.scrollbarThumb})`,
                                    borderRadius: "3px",
                                },
                                "&::-webkit-scrollbar-thumb:hover": {
                                    backgroundColor: `var(${CSS_VAR_NAMES.scrollbarThumbHover})`,
                                },
                            }}
                        >
                            <RoleRouteGuard>
                                <Outlet />
                            </RoleRouteGuard>
                        </Box>
                    </Box>
                </Box>
            </Box>
        </Box>
    );
};

export default AppLayout;
