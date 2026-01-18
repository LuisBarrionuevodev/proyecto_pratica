import { useState } from "react";
import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, IconButton, Divider, Tooltip, } from "@mui/material";
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import KeyboardDoubleArrowLeftIcon from '@mui/icons-material/KeyboardDoubleArrowLeft';
import { Link, useNavigate } from "react-router-dom";
import { 
    StyleDivider, 
    StyleDrawer, 
    StyleListItems, 
    StyleListItemsIcon, 
    StyleLogo,
    StyleListItem,
    StyleListItemButton,
    StyleListItemText,
    StyleExpandButton,
} from "../styles/NavBarStyles";
import { menuItems } from "../constants/menuItems";
import LogoSMT from "../assets/LogoSMT.svg"
import TextDigitaliza from "../assets/TextDigitaliza.svg"

const NavLeft = () => {

    const navigate = useNavigate()

    const [open, setOpen] = useState(false);

    return (
        <Box sx={{ }}>

            <Drawer
                variant="permanent"
                open={open}
                sx={StyleDrawer(open)}
            >
                {/* Logo arriba */}
                <Link to="/inicio">
                <Box sx={StyleLogo}>

                        <img src={LogoSMT} alt="" />
                        {open ? <img src={TextDigitaliza} alt="" style={{ width: "150px" }} /> : null}
                    
                </Box>
                </Link>

                <Divider sx={StyleDivider} />

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

                {/* Botón de expansión */}
                <IconButton
                    onClick={() => setOpen(!open)}
                    sx={StyleExpandButton}
                >
                    {open ? <KeyboardDoubleArrowLeftIcon /> : <KeyboardDoubleArrowRightIcon />}
                </IconButton>
            </Drawer>
        </Box>
    );
};

export default NavLeft;