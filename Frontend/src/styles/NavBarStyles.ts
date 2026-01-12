import type { SxProps, Theme } from "@mui/material";

export const StyleLogo = {
    padding: 2,
    display: "flex",
    flexDirection: "row",
    justifyContent: "center"
}

export const StyleDivider = {
    width: "100%",
    marginBottom: 2,
    borderColor: "#b3b3b3ff"
}

export const StyleListItems = {
    flexGrow: 1,
    width: "100%",
}

export const StyleDrawer = (open: boolean): SxProps<Theme> => ({
    width: open ? 230 : 70,
    flexShrink: 0,
    fontSize:"10px",
    "& .MuiDrawer-paper": {
        width: open ? 230 : 70,
        transition: "width 0.3s",
        overflowX: "hidden",
        backgroundColor: "#2B2E34",
        color: "white",
        borderRadius: "25px",
        position: "fixed",
        height:"97vh",
        marginLeft: "20px",
        marginTop: "10px",
        marginBottom:"10px",
        alignItems: "center",
    },
}
);

export const StyleListItemsIcon = (open: boolean): SxProps<Theme> => ({
    color: "white",
    minWidth: 0,
    marginRight: open ? 2 : "auto",
})