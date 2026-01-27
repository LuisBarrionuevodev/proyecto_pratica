import { useState } from "react";
import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, IconButton, Divider, Tooltip, } from "@mui/material";
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import KeyboardDoubleArrowLeftIcon from '@mui/icons-material/KeyboardDoubleArrowLeft';
import { useNavigate } from "react-router-dom";
import {
    StyleDivider,
    StyleDrawer,
    StyleListItems,
    StyleListItemsIcon,
    StyleListItem,
    StyleListItemButton,
    StyleListItemText,
    StyleExpandButton,
} from "../styles/NavBarStyles";
import { menuItems } from "../constants/menuItems";

const NavLeft = () => {

    const navigate = useNavigate()

    const [open, setOpen] = useState(false);

    return (
        <Box >

            <Drawer
                variant="permanent"
                open={open}
                sx={StyleDrawer(open)}
            >

                {/* Botón de expansión */}
                <IconButton
                    onClick={() => setOpen(!open)}
                    sx={StyleExpandButton}
                >
                    {open ? <KeyboardDoubleArrowLeftIcon /> : <KeyboardDoubleArrowRightIcon />}
                </IconButton>
                {/* Logo arriba */}
                
                {/* <Divider sx={StyleDivider} /> */}

                {/* Lista de ítems con alineación profesional */}
                <List sx={StyleListItems}>
                    {menuItems.map(({ text, icon, path }) => (
                        <Tooltip key={text} title={!open ? text : ""} placement="right" arrow>
                            <ListItem disablePadding sx={StyleListItem(open)}>
                                <ListItemButton
                                    onClick={() => navigate(path)}
                                    sx={StyleListItemButton(open)}
                                >
                                    <ListItemIcon sx={StyleListItemsIcon(open)}>
                                        {icon}
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={text}
                                        sx={StyleListItemText(open)}
                                    />
                                </ListItemButton>
                            </ListItem>
                        </Tooltip>
                    ))}
                </List>

                <Divider sx={StyleDivider} />


            </Drawer>
        </Box>
    );
};

export default NavLeft;