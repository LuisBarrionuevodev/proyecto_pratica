import { useMemo, useState } from "react";
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
import { logoutItem } from "../constants/menuItems";
import { getVisibleMenuSections } from "../auth/accessConfig";
import { useAppSession } from "../auth/AppSessionProvider";

interface NavLeftProps {
    onToggle?: (open: boolean) => void;
}

const NavLeft: React.FC<NavLeftProps> = ({ onToggle }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const { status, role } = useAppSession();

    const visibleSections = useMemo(() => {
        if (!role) return [];
        return getVisibleMenuSections(role);
    }, [role]);

    const isActive = (path: string) => location.pathname === path;

    return (
        <Box>
            <Drawer
                variant="permanent"
                open={open}
                sx={StyleDrawer(open)}
            >
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

                <List sx={StyleListItems(open)}>
                    {status === "loading" ? null : visibleSections.map((section) => (
                        <Box key={section.label}>
                            <Typography sx={StyleSectionHeader(open)}>
                                {section.label}
                            </Typography>
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
                            }}>
                                {logoutItem.icon}
                            </ListItemIcon>
                            <ListItemText
                                primary={logoutItem.text}
                                sx={{
                                    opacity: open ? 1 : 0,
                                    transition: "opacity 0.2s ease",
                                    "& .MuiTypography-root": {
                                        color: "#FF6B6B",
                                        fontFamily: '"Tactic Sans", sans-serif',
                                        fontSize: "13px",
                                        fontWeight: 600,
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
