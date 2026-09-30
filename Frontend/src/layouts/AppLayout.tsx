import { useEffect, useState } from "react";
import { setBodyAuthenticatedRoute } from "../theme/bodyRouteClass";
import { Outlet, useLocation } from "react-router-dom";
import { resolveBreadcrumbLabel } from "../utils/breadcrumbLabel";
import { Box, useMediaQuery, useTheme } from "@mui/material";
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
const OUTER_MARGIN = layoutShell.outerMarginPx;
const LAYOUT_HEIGHT = "calc(100vh - 24px)";

/**
 * AppLayout - Layout principal estilo "app window"
 *
 * Desktop (≥ md): sidebar permanente colapsable + ContentShell.
 * Mobile (< md): sin reserva lateral; menú en drawer temporal desde TopBar.
 */
const AppLayout = () => {
    const theme = useTheme();
    const isDesktopShell = useMediaQuery(theme.breakpoints.up(layoutShell.desktopMinBreakpoint));
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
    const location = useLocation();

    const currentSidebarWidth = sidebarOpen ? SIDEBAR_EXPANDED : SIDEBAR_COLLAPSED;
    const currentLabel = resolveBreadcrumbLabel(location.pathname);

    useEffect(() => {
        setBodyAuthenticatedRoute(true);
        return () => setBodyAuthenticatedRoute(false);
    }, []);

    useEffect(() => {
        setMobileNavOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        if (isDesktopShell) {
            setMobileNavOpen(false);
        }
    }, [isDesktopShell]);

    return (
        <Box
            sx={{
                display: "flex",
                flexDirection: "column",
                height: "100vh",
                width: "100%",
                maxWidth: "100%",
                overflow: "hidden",
                bgcolor: "transparent",
            }}
        >
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
                <TopBar
                    sidebarWidth={layoutShell.sidebarCollapsedPx}
                    showMobileMenuButton={!isDesktopShell}
                    onMobileMenuOpen={() => setMobileNavOpen(true)}
                />
            </Box>

            {!isDesktopShell ? (
                <NavLeft
                    mobileTemporary={{
                        open: mobileNavOpen,
                        onClose: () => setMobileNavOpen(false),
                    }}
                />
            ) : null}

            <Box
                sx={{
                    display: "flex",
                    marginTop: `${TOPBAR_HEIGHT}px`,
                    height: isDesktopShell ? LAYOUT_HEIGHT : `calc(100vh - ${TOPBAR_HEIGHT}px)`,
                    overflow: "hidden",
                    padding: isDesktopShell ? `${OUTER_MARGIN}px` : 1,
                    paddingTop: 0,
                    boxSizing: "border-box",
                    width: "100%",
                    maxWidth: "100%",
                }}
            >
                {isDesktopShell ? (
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
                ) : null}

                <Box
                    component="main"
                    sx={{
                        flex: 1,
                        minWidth: 0,
                        marginLeft: isDesktopShell ? "4px" : 0,
                        height: "100%",
                        overflow: "hidden",
                    }}
                >
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
                        <InstitutionalViewHeaderBar title={currentLabel} />

                        <Box
                            sx={{
                                flex: 1,
                                minHeight: 0,
                                overflowY: "auto",
                                overflowX: "hidden",
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
