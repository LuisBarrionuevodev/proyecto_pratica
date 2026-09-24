import type { SxProps, Theme } from "@mui/material";
import { GLASS_COLORS } from "./GlassStyles";
import { color as tokenColor, layoutShell } from "../theme/tokens";

// =============================================================================
// ESTILOS GLASSMORPHISM PARA TOPBAR
// =============================================================================

// Paleta de colores (armonizada con NavLeft)
export const COLORS = {
    primary: tokenColor.primary,
    black: "#000000",
    white: "#FFFFFF",
    grayDark: GLASS_COLORS.sidebarBg,
    grayMedium: "#666666",
    grayLight: "#F5F5F5",
    success: "#2D9F4B",
};

// Color de borde consistente con glass
export const BORDER_COLOR = GLASS_COLORS.borderMedium;

// Contenedor TopBar - Fijo arriba, transparente
export const TopBarContainerStyles: SxProps<Theme> = {
    width: "100%",
    bgcolor: "transparent",
    zIndex: 1200,
    height: `${layoutShell.topBarHeightPx}px`,
    position: "relative",
    display: "flex",
    alignItems: "center",
    paddingX:0,
    paddingRight: 1.5,
};

// Botón del avatar (trigger del menú) - completamente transparente
export const AvatarButtonStyles: SxProps<Theme> = {
    display: "flex",
    alignItems: "center",
    gap: 1.5,
    padding: "8px 12px",
    backgroundColor: "transparent",
    border: "none",
    borderRadius: "12px",
    cursor: "pointer",
    transition: "all 0.15s ease",
    "&:hover": {
        backgroundColor: "rgba(255, 255, 255, 0.05)",
    },
};

// Avatar sin borde
export const AvatarStyles: SxProps<Theme> = {
    width: 36,
    height: 36,
    border: "none",
};

// Contenedor de info del usuario (nombre + rol)
export const UserInfoStyles: SxProps<Theme> = {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
};

// Nombre del usuario
export const UserNameStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 600,
    fontSize: "14px",
    color: GLASS_COLORS.textPrimary,
    lineHeight: 1.2,
};

// Badge del rol (pequeño, junto al nombre)
export const RoleBadgeSmallStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "10px",
    color: COLORS.primary,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
};

// Icono de flecha
export const ArrowIconStyles: SxProps<Theme> = {
    color: COLORS.white,
    fontSize: 18,
    transition: "transform 0.2s ease",
};

// =============================================================================
// ESTILOS DEL MENÚ DESPLEGABLE
// =============================================================================

// Paper del menú - alineado con el layout, mismo estilo glass
export const MenuPaperStyles = {
    backgroundColor: GLASS_COLORS.sidebarBg,
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    borderRadius: "12px",
    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
    marginTop: "4px",
    marginRight: "4px",
    minWidth: "180px",
    overflow: "hidden",
};

// Header del menú (avatar + info)
export const MenuHeaderStyles: SxProps<Theme> = {
    display: "flex",
    alignItems: "center",
    gap: 2,
    padding: "20px 20px 16px 20px",
    borderBottom: `1px solid rgba(255, 255, 255, 0.15)`,
};

// Avatar grande en el menú
export const MenuAvatarStyles: SxProps<Theme> = {
    width: 56,
    height: 56,
    border: `1px solid ${BORDER_COLOR}`,
};

// Contenedor de info en el menú
export const MenuUserInfoStyles: SxProps<Theme> = {
    display: "flex",
    flexDirection: "column",
    gap: 0.5,
};

// Nombre grande en el menú
export const MenuUserNameStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "16px",
    color: COLORS.white,
    lineHeight: 1.2,
};

// Chip del rol con borde simple
export const RoleChipStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 600,
    fontSize: "11px",
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    border: `1px solid ${BORDER_COLOR}`,
    borderRadius: "6px",
    height: "24px",
    "& .MuiChip-label": {
        padding: "0 8px",
    },
};

// Email del usuario
export const MenuEmailStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 400,
    fontSize: "13px",
    color: "rgba(255, 255, 255, 0.7)",
};

// Items del menú
export const MenuItemStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "14px",
    color: COLORS.white,
    padding: "14px 20px",
    gap: 1.5,
    transition: "all 0.15s ease",
    "&:hover": {
        backgroundColor: "rgba(255, 255, 255, 0.1)",
    },
    "&:first-of-type": {
        marginTop: "8px",
    },
};

// Divider del menú
export const MenuDividerStyles: SxProps<Theme> = {
    margin: "8px 12px",
    borderColor: "rgba(255, 255, 255, 0.15)",
};

// Item de cerrar sesión (rojo)
export const MenuItemLogoutStyles: SxProps<Theme> = {
    ...MenuItemStyles,
    color: "#FF6B6B",
    marginBottom: "8px",
    "&:hover": {
        backgroundColor: "rgba(229, 57, 53, 0.15)",
    },
};
