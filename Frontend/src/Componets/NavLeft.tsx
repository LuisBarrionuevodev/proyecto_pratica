import { useState } from "react";
import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, IconButton, Avatar, Divider, Tooltip, } from "@mui/material";
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import KeyboardDoubleArrowLeftIcon from '@mui/icons-material/KeyboardDoubleArrowLeft';
import { Link, useNavigate } from "react-router-dom";
import { StyleDivider, StyleDrawer, StyleListItems, StyleListItemsIcon, StyleLogo } from "../styles/NavBarStyles";
import { menuItems } from "../constants/menuItems";
import LogoSMT from "../assets/LogoSMT.svg"
import TextDigitaliza from "../assets/TextDigitaliza.svg"
import FotoAvatar from "../assets/FotoAvatar.png"

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

                {/* Lista de ítems */}
                <List sx={StyleListItems}>
                    {menuItems.map(({ text, icon, path }) => (
                        <Tooltip key={text} title={!open ? text : ""} placement="right">
                            <ListItem disablePadding>
                                <ListItemButton onClick={() => navigate(path)}>
                                    <ListItemIcon sx={StyleListItemsIcon(open)}>
                                        {icon}
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={text}
                                        slotProps={{primary: {
                                            fontFamily:"Tactic Sans",
                                        }}}
                                        sx={{ opacity: open ? 1 : 0,  whiteSpace: "wrap"  }}
                                    />
                                </ListItemButton>
                            </ListItem>
                        </Tooltip>
                    ))}
                </List>

                <Divider sx={StyleDivider} />

                {/* Avatar de usuario abajo */}
                <Box sx={{ padding: 2 }}>
                    <Avatar src={FotoAvatar} alt="Usuario"/>
                </Box>

                {/* Botón de expansión */}
                <IconButton
                    onClick={() => setOpen(!open)}
                    sx={{ color: "white", marginBottom: 2 }}
                >
                    { open ? <KeyboardDoubleArrowLeftIcon /> : <KeyboardDoubleArrowRightIcon /> }
                </IconButton>
            </Drawer>
        </Box>
    );
};

export default NavLeft;