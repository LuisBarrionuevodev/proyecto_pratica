import { useState } from "react";
import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, IconButton, Typography, Tooltip } from "@mui/material";
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import KeyboardDoubleArrowLeftIcon from '@mui/icons-material/KeyboardDoubleArrowLeft';
import { useNavigate, useLocation } from "react-router-dom";
import {
    StyleDrawer,
    StyleListItems,
    StyleListItemsIcon,
    StyleListItem,
    StyleListItemButton,
    StyleListItemText,
    StyleExpandButton,
    StyleSectionHeader,
    StyleLogoutContainer,
    StyleLogoutButton,
} from "../styles/NavBarStyles";
import { menuSections, logoutItem } from "../constants/menuItems";

interface NavLeftProps {
    onToggle?: (open: boolean) => void;
}

const NavLeft: React.FC<NavLeftProps> = ({ onToggle }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [open, setOpen] = useState(false);

    const isActive = (path: string) => location.pathname === path;

    return (
        <Box>
            <Drawer
                variant="permanent"
                open={open}
                sx={StyleDrawer(open)}
            >
                {/* Botón de expansión */}
                <IconButton
                    onClick={() => {
                        const next = !open;
                        setOpen(next);
                        onToggle?.(next);
                    }}
                    sx={StyleExpandButton}
                >
                    {open ? <KeyboardDoubleArrowLeftIcon /> : <KeyboardDoubleArrowRightIcon />}
                </IconButton>

                {/* Lista de secciones con items agrupados */}
                <List sx={StyleListItems}>
                    {menuSections.map((section) => (
                        <Box key={section.label}>
                            {/* Header de sección */}
                            <Typography sx={StyleSectionHeader(open)}>
                                {section.label}
                            </Typography>
                            
                            {/* Items de la sección */}
                            {section.items.map(({ text, icon, path }) => {
                                const active = isActive(path);
                                return (
                                    <Tooltip key={text} title={!open ? text : ""} placement="right" arrow>
                                        <ListItem disablePadding sx={StyleListItem(open)}>
                                            <ListItemButton
                                                onClick={() => navigate(path)}
                                                sx={StyleListItemButton(open, active)}
                                            >
                                                <ListItemIcon sx={StyleListItemsIcon(open, active)}>
                                                    {icon}
                                                </ListItemIcon>
                                                <ListItemText
                                                    primary={text}
                                                    sx={StyleListItemText(open, active)}
                                                />
                                            </ListItemButton>
                                        </ListItem>
                                    </Tooltip>
                                );
                            })}
                        </Box>
                    ))}
                </List>

                {/* Logout al final (sticky bottom) */}
                <Box sx={StyleLogoutContainer(open)}>
                    <Tooltip title={!open ? logoutItem.text : ""} placement="right" arrow>
                        <ListItemButton
                            onClick={() => navigate(logoutItem.path)}
                            sx={StyleLogoutButton(open)}
                        >
                            <ListItemIcon sx={{ 
                                color: "#FF6B6B", 
                                minWidth: 0, 
                                marginRight: open ? 1.5 : 0,
                                justifyContent: "center",
                                "& .MuiSvgIcon-root": { fontSize: "1.3rem" }
                            }}>
                                {logoutItem.icon}
                            </ListItemIcon>
                            <ListItemText
                                primary={logoutItem.text}
                                sx={{
                                    opacity: open ? 1 : 0,
                                    width: open ? "auto" : 0,
                                    overflow: "hidden",
                                    whiteSpace: "nowrap",
                                    transition: "opacity 0.15s ease-out, width 0.2s ease-out",
                                    "& .MuiTypography-root": {
                                        fontFamily: '"Tactic Sans", sans-serif',
                                        fontSize: "13px",
                                        fontWeight: 500,
                                        color: "#FF6B6B",
                                    },
                                }}
                            />
                        </ListItemButton>
                    </Tooltip>
                </Box>
            </Drawer>
        </Box>
    );
};

export default NavLeft;