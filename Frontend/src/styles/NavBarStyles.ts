import type { SxProps, Theme } from "@mui/material";

// Estilos del logo superior
export const StyleLogo = {
    padding: 2,
    display: "flex",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
};

// Divisor con espaciado consistente
export const StyleDivider = {
    width: "85%",
    marginTop: 1,
    marginBottom: 1,
    borderColor: "rgba(255, 255, 255, 0.15)",
};

// Contenedor de la lista con espaciado interno
export const StyleListItems = {
    flexGrow: 1,
    width: "100%",
    paddingTop: 1,
    paddingBottom: 1,
};

// Drawer principal con transición suave
export const StyleDrawer = (open: boolean): SxProps<Theme> => ({
    width: open ? 240 : 70,
    flexShrink: 0,
    "& .MuiDrawer-paper": {
        width: open ? 240 : 70,
        transition: "width 0.3s ease-in-out",
        overflowX: "hidden",
        backgroundColor: "#2B2E34",
        color: "white",
        borderRadius: "20px",
        position: "fixed",
        height: "97vh",
        marginLeft: "15px",
        marginTop: "10px",
        marginBottom: "10px",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
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

// Texto del item: oculto completamente cuando cerrado, wrap cuando abierto
export const StyleListItemText = (open: boolean): SxProps<Theme> => ({
    display: open ? "block" : "none",
    whiteSpace: "normal",
    wordWrap: "break-word",
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
    marginBottom: 2,
    padding: 1,
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: "rgba(255, 255, 255, 0.1)",
    },
};