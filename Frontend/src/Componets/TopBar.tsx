import { useState } from "react";

import {
    Box,
    Avatar,
    Typography,
    Menu,
    MenuItem,
    Divider,
    Skeleton,
    IconButton,
    Tooltip,
} from "@mui/material";

import { getAvatarUrl } from "../utils/avatarUrl";

import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import { useDigitalizaTheme } from "../theme/DigitalizaThemeProvider";

import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import LogoutIcon from "@mui/icons-material/Logout";

import MenuIcon from "@mui/icons-material/Menu";

import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import TextDigitaliza from "../assets/TextDigitaliza.svg"

import { useAppSession, notifyAuthSessionRefresh } from "../auth/AppSessionProvider";

import {

    TopBarContainerStyles,

    AvatarButtonStyles,

    AvatarStyles,

    UserInfoStyles,

    UserNameStyles,

    RoleBadgeSmallStyles,

    ArrowIconStyles,

    MenuPaperStyles,

    MenuItemStyles,

    MenuDividerStyles,

} from "../styles/TopBarStyles";



import { useNavigate } from "react-router-dom";



interface TopBarProps {
    sidebarWidth?: number;
    showMobileMenuButton?: boolean;
    onMobileMenuOpen?: () => void;
}

const topBarIconButtonSx = {
    color: "var(--d-text-secondary)",
    flexShrink: 0,
    "&:hover": { color: "var(--d-text-primary)", backgroundColor: "var(--d-action-hover)" },
};

const TopBar: React.FC<TopBarProps> = ({
    sidebarWidth: _sidebarWidth = 72,
    showMobileMenuButton = false,
    onMobileMenuOpen,
}) => {
    const { mode, toggleMode } = useDigitalizaTheme();

    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

    const open = Boolean(anchorEl);

    const navigate = useNavigate();

    const session = useAppSession();

    const loading = session.status === "loading";



    const handleClick = (event: React.MouseEvent<HTMLElement>) => {

        setAnchorEl(event.currentTarget);

    };



    const handleClose = () => {

        setAnchorEl(null);

    };



    const handleViewProfile = () => {

        handleClose();

        navigate("/perfil");

    };



    const handleInicio = () => {

        navigate("/inicio");

    };



    const handleLogout = () => {

        handleClose();

        localStorage.removeItem("access_token");
        notifyAuthSessionRefresh();
        navigate("/login");

    };



    return (

        <Box sx={TopBarContainerStyles}>
            {showMobileMenuButton ? (
                <Tooltip title="Menú de navegación">
                    <IconButton
                        onClick={onMobileMenuOpen}
                        size="small"
                        aria-label="Abrir menú de navegación"
                        sx={{ ...topBarIconButtonSx, ml: 0.5 }}
                    >
                        <MenuIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
            ) : null}

            <Box
                onClick={handleInicio}
                sx={{
                    cursor: "pointer",
                    width: "auto",
                    minWidth: 0,
                    flex: { xs: 1, md: "0 1 auto" },
                    maxWidth: { xs: "calc(100% - 120px)", sm: "none" },
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "flex-start",
                    ml: showMobileMenuButton ? 0.5 : { xs: 2, sm: 2.25 },
                    mt: 1,
                }}
            >
                <Box
                    component="img"
                    src={TextDigitaliza}
                    alt="Digitaliza"
                    sx={{
                        width: { xs: 175, sm: 205, lg: 230, xl: 240 },
                        height: "auto",
                        objectFit: "contain",
                        objectPosition: "left center",
                        display: "block",
                    }}
                />
            </Box>

            

            <Box sx={{ flex: 1, minWidth: 0, display: { xs: "none", md: "block" } }} />

            <Tooltip title={mode === "dark" ? "Usar modo claro" : "Usar modo oscuro"}>
                <IconButton
                    onClick={toggleMode}
                    size="small"
                    aria-label={mode === "dark" ? "Usar modo claro" : "Usar modo oscuro"}
                    sx={{ ...topBarIconButtonSx, mr: 0.5 }}
                >
                    {mode === "dark" ? (
                        <LightModeOutlinedIcon fontSize="small" />
                    ) : (
                        <DarkModeOutlinedIcon fontSize="small" />
                    )}
                </IconButton>
            </Tooltip>

            <Box
                onClick={handleClick}
                sx={{
                    ...AvatarButtonStyles,
                    flexShrink: 0,
                    padding: { xs: "6px 8px", sm: "8px 12px" },
                    gap: { xs: 0.75, sm: 1.5 },
                }}
            >

                {loading ? (

                    <Skeleton variant="circular" width={36} height={36} />

                ) : (

                    <Avatar

                        src={getAvatarUrl(session.avatarKey)}

                        alt={session.toolbarPrimary}

                        sx={AvatarStyles}

                    />

                )}

                <Box sx={{ ...UserInfoStyles, display: { xs: "none", sm: "flex" } }}>

                    {loading ? (

                        <>

                            <Skeleton variant="text" width={88} height={18} />

                            <Skeleton variant="text" width={64} height={14} />

                        </>

                    ) : (

                        <>

                            <Typography sx={UserNameStyles} noWrap title={session.toolbarPrimary}>

                                {session.toolbarPrimary}

                            </Typography>

                            {session.toolbarShowRoleBadge ? (

                                <Typography sx={RoleBadgeSmallStyles} noWrap>

                                    ● {session.toolbarRoleLabel}

                                </Typography>

                            ) : null}

                        </>

                    )}

                </Box>

                <KeyboardArrowDownIcon
                    sx={{
                        ...ArrowIconStyles,
                        display: { xs: "none", sm: "block" },
                        transform: open ? "rotate(180deg)" : "rotate(0deg)",
                    }}
                />

            </Box>



            <Menu

                anchorEl={anchorEl}

                open={open}

                onClose={handleClose}

                anchorOrigin={{

                    vertical: "bottom",

                    horizontal: "right",

                }}

                transformOrigin={{

                    vertical: "top",

                    horizontal: "right",

                }}

                slotProps={{

                    paper: {

                        sx: {

                            ...MenuPaperStyles,

                            minWidth: "180px",

                            padding: "4px",

                        },

                    },

                }}

            >

                <MenuItem 

                    onClick={handleViewProfile} 

                    sx={{

                        ...MenuItemStyles,

                        display: "flex",

                        justifyContent: "space-between",

                        alignItems: "center",

                    }}

                >

                    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>

                        <PersonOutlineIcon fontSize="small" />

                        Perfil

                    </Box>

                    <OpenInNewIcon sx={{ fontSize: 14, opacity: 0.7 }} />

                </MenuItem>



                <Divider sx={MenuDividerStyles} />



                <MenuItem onClick={handleLogout} sx={MenuItemStyles}>

                    <LogoutIcon fontSize="small" />

                    Cerrar sesión

                </MenuItem>

            </Menu>

        </Box>

    );

};



export default TopBar;

