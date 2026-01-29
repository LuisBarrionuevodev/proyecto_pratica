import type { SxProps, Theme } from "@mui/material";

// Estilos del logo superior
export const StyleLogo = {
    padding: 1,
    display: "flex",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
};

// Divisor con espaciado consistente
export const StyleDivider = {
    width: "85%",
    borderColor: "rgba(255, 255, 255, 0.15)",
};

// Contenedor de la lista con espaciado interno
export const StyleListItems = {
    flexGrow: 1,
    width: "100%",
    paddingTop: 1,
    paddingBottom: 1,
};

// Drawer principal estilo Spotify
// Color igual al ContentShell para armonía visual
export const StyleDrawer = (open: boolean): SxProps<Theme> => ({
    width: open ? 240 : 70,
    flexShrink: 0,
    "& .MuiDrawer-paper": {
        width: open ? 240 : 80,
        transition: "width 0.2s ease-out", // Más rápido como Spotify
        overflowX: "hidden",
        backgroundColor: "#1A1C20", // Mismo color que ContentShell
        color: "white",
        borderRadius: "16px",
        position: "relative",
        height: "calc(100% - 24px)",
        marginLeft: "12px",
        marginTop: "12px",
        marginBottom: "12px",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        border: "1px solid #3a3d44",
        boxShadow: "0 4px 24px rgba(0, 0, 0, 0.2)",
    },
});

// Estilos para cada item del menú
export const StyleListItem = (open: boolean): SxProps<Theme> => ({
    display: "block",
    paddingX: open ? 1.5 : 0,
    paddingY: 0.5,
});

// Botón de cada item con alineación profesional
export const StyleListItemButton = (open: boolean): SxProps<Theme> => ({
    minHeight: open ? 48 : 44,
    justifyContent: open ? "flex-start" : "center",
    paddingX: open ? 2 : 2.5,
    paddingY: open ? 1.25 : 1,
    borderRadius: "12px",
    marginX: open ? 0 : 0.5,
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: "rgba(255, 255, 255, 0.1)",
    },
});

// Iconos centrados y alineados
export const StyleListItemsIcon = (open: boolean): SxProps<Theme> => ({
    color: "white",
    minWidth: 0,
    marginRight: open ? 2 : 0,
    justifyContent: "center",
    display: "flex",
    alignItems: "center",
    "& .MuiSvgIcon-root": {
        fontSize: "1.4rem",
    },
});

// Texto del item: animación estilo Spotify (aparece rápido hacia la derecha)
export const StyleListItemText = (open: boolean): SxProps<Theme> => ({
    opacity: open ? 1 : 0,
    width: open ? "auto" : 0,
    overflow: "hidden",
    whiteSpace: "nowrap",
    transition: "opacity 0.15s ease-out, width 0.2s ease-out",
    "& .MuiTypography-root": {
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "13px",
        fontWeight: 500,
        letterSpacing: "0.3px",
        lineHeight: 1.3,
    },
});

// Botón de expansión
export const StyleExpandButton: SxProps<Theme> = {
    color: "white",
    mt: 2,
    padding: 1,
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: "rgba(255, 255, 255, 0.1)",
    },
};