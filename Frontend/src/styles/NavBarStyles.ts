import type { SxProps, Theme } from "@mui/material";
import { TRANSITION, GLASS_COLORS } from "./GlassStyles";

// =============================================================================
// ESTILOS GLASSMORPHISM PARA NAVLEFT
// =============================================================================

// Estilos del logo superior
export const StyleLogo = {
    padding: 1,
    display: "flex",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
};

// Divisor glass sutil
export const StyleDivider = {
    width: "85%",
    borderColor: GLASS_COLORS.borderLight,
    opacity: 0.6,
    marginY: 1,
};

// Contenedor de la lista con espaciado interno
export const StyleListItems = {
    flexGrow: 1,
    width: "100%",
    paddingTop: 0,
    paddingBottom: 1,
    overflowY: "auto",
    overflowX: "hidden",
    "&::-webkit-scrollbar": {
        width: "4px",
    },
    "&::-webkit-scrollbar-thumb": {
        backgroundColor: "rgba(255, 255, 255, 0.2)",
        borderRadius: "4px",
    },
};

// Drawer principal - misma altura que ContentShell
export const StyleDrawer = (open: boolean): SxProps<Theme> => ({
    width: open ? 260 : 72,
    flexShrink: 0,
    "& .MuiDrawer-paper": {
        width: open ? 260 : 72,
        transition: TRANSITION.css,
        overflowX: "hidden",
        backgroundColor: GLASS_COLORS.sidebarBg,
        color: "white",
        borderRadius: "16px",
        position: "relative",
        height: "50%", // Ocupa toda la altura del contenedor padre
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        border: `1px solid ${GLASS_COLORS.borderLight}`,
    },
});

// Header de sección (CARGA, GESTIÓN, etc.)
export const StyleSectionHeader = (open: boolean): SxProps<Theme> => ({
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "10px",
    fontWeight: 600,
    letterSpacing: "1.5px",
    textTransform: "uppercase",
    color: GLASS_COLORS.textMuted,
    paddingX: 2,
    paddingY: 0.75,
    marginTop: 1.5,
    opacity: open ? 1 : 0,
    height: open ? "auto" : 0,
    overflow: "hidden",
    transition: "opacity 0.15s ease, height 0.2s ease",
});

// Estilos para cada item del menú
export const StyleListItem = (open: boolean): SxProps<Theme> => ({
    display: "block",
    paddingX: open ? 1 : 0.5,
    paddingY: 0.25,
    //aca se cambia la altura de la nav left
    height: open ? "5.9vh" : "6.6vh" ,
});

// Botón de cada item con glassmorphismo
export const StyleListItemButton = (open: boolean, isActive: boolean = false): SxProps<Theme> => ({
    minHeight: 44,
    justifyContent: open ? "flex-start" : "center",
    paddingX: open ? 2 : 1.5,
    paddingY: 1,
    borderRadius: "12px",
    marginX: open ? 0 : 0.25,
    transition: "all 0.2s ease",
    position: "relative",
    // Estado activo
    ...(isActive && {
        backgroundColor: GLASS_COLORS.activeBg,
        "&::before": {
            content: '""',
            position: "absolute",
            left: 0,
            top: "50%",
            transform: "translateY(-50%)",
            width: "3px",
            height: "60%",
            backgroundColor: GLASS_COLORS.primary,
            borderRadius: "0 2px 2px 0",
            boxShadow: `0 0 8px ${GLASS_COLORS.primaryGlow}`,
        },
    }),
    "&:hover": {
        backgroundColor: isActive ? GLASS_COLORS.activeBg : GLASS_COLORS.hoverBg,
    },
});

// Iconos centrados y alineados
export const StyleListItemsIcon = (open: boolean, isActive: boolean = false): SxProps<Theme> => ({
    color: isActive ? GLASS_COLORS.primary : GLASS_COLORS.textSecondary,
    minWidth: 0,
    marginRight: open ? 1.5 : 0,
    justifyContent: "center",
    display: "flex",
    alignItems: "center",
    transition: "color 0.2s ease",
    "& .MuiSvgIcon-root": {
        fontSize: "1.3rem",
    },
});

// Texto del item con animación horizontal
export const StyleListItemText = (open: boolean, isActive: boolean = false): SxProps<Theme> => ({
    opacity: open ? 1 : 0,
    width: open ? "auto" : 0,
    overflow: "hidden",
    whiteSpace: "nowrap",
    transition: "opacity 0.15s ease-out, width 0.2s ease-out",
    "& .MuiTypography-root": {
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "13px",
        fontWeight: isActive ? 600 : 500,
        letterSpacing: "0.2px",
        lineHeight: 1.3,
        color: isActive ? GLASS_COLORS.textPrimary : GLASS_COLORS.textSecondary,
    },
});

// Botón de expansión
export const StyleExpandButton: SxProps<Theme> = {
    color: GLASS_COLORS.textSecondary,
    mt: 1.5,
    mb: 0.5,
    padding: 1,
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: GLASS_COLORS.hoverBg,
        color: GLASS_COLORS.textPrimary,
    },
};

// Contenedor del logout (sticky bottom)
export const StyleLogoutContainer = (open: boolean): SxProps<Theme> => ({
    width: "100%",
    height: "44px",
    paddingX: open ? 1 : 0.5,
    paddingY: 1,
    marginTop: "auto",
    borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
});

// Botón de logout
export const StyleLogoutButton = (open: boolean): SxProps<Theme> => ({
    minHeight: 44,
    justifyContent: open ? "flex-start" : "center",
    paddingX: open ? 2 : 1.5,
    paddingY: 1,
    borderRadius: "12px",
    marginX: open ? 0 : 0.25,
    transition: "all 0.2s ease",
    color: "#FF6B6B",
    "&:hover": {
        backgroundColor: "rgba(255, 107, 107, 0.12)",
    },
});