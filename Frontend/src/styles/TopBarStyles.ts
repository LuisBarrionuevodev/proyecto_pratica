import type { SxProps, Theme } from "@mui/material";

// =============================================================================
// ESTILOS NEO-BRUTALISTAS PARA TOPBAR - Menú de Usuario
// =============================================================================

// Paleta de colores Neo-Brutalista (consistente con el proyecto)
export const COLORS = {
    primary: "#0166FF",
    black: "#000000",
    white: "#FFFFFF",
    grayDark: "#2B2E34",
    grayMedium: "#666666",
    grayLight: "#F5F5F5",
    success: "#2D9F4B",
};

// Color de borde consistente con el resto de la app
export const BORDER_COLOR = "#3a3d44";

// Contenedor fijo en la esquina superior derecha
export const TopBarContainerStyles: SxProps<Theme> = {
    position: "fixed",
    top: 16,
    right: 24,
    zIndex: 1200,
    display: "flex",
    alignItems: "center",
    gap: 1.5,
};

// Botón del avatar (trigger del menú) - sin caja por defecto
export const AvatarButtonStyles: SxProps<Theme> = {
    display: "flex",
    alignItems: "center",
    gap: 1.5,
    padding: "8px 12px",
    backgroundColor: "transparent",
    border: "none",
    borderRadius: "12px",
    cursor: "pointer",
    transition: "all 0.2s ease-in-out",
    "&:hover": {
        backgroundColor: "rgba(255, 255, 255, 0.05)",
    },
};

// Avatar con borde simple
export const AvatarStyles: SxProps<Theme> = {
    width: 40,
    height: 40,
    border: `1px solid ${BORDER_COLOR}`,
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
    color: COLORS.white,
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

// Paper del menú - fondo gris oscuro con borde y sombra sutil
export const MenuPaperStyles = {
    backgroundColor: COLORS.grayDark,
    border: `1px solid ${BORDER_COLOR}`,
    borderRadius: "8px",
    boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
    marginTop: "12px",
    minWidth: "220px",
    overflow: "visible",
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
