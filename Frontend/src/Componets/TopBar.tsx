import { useState } from "react";
import {
    Box,
    Avatar,
    Typography,
    Menu,
    MenuItem,
    Divider,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import LogoutIcon from "@mui/icons-material/Logout";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import TextDigitaliza from "../assets/TextDigitaliza.svg"
import LogoSMT from "../assets/LogoSMT.svg"
// Estilos Neo-Brutalistas
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

// Avatar del usuario
import FotoAvatar from "../assets/FotoAvatar.png";
import { useNavigate } from "react-router-dom";

// Datos del usuario (temporales - luego vendrán de contexto/auth)
const USER_DATA = {
    name: "John Smith",
    role: "Administrator",
    email: "john.smith@smt.gob",
    avatar: FotoAvatar,
};

interface TopBarProps {
    sidebarWidth?: number;
}

const TopBar: React.FC<TopBarProps> = ({ sidebarWidth = 72 }) => {
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
    const open = Boolean(anchorEl);

    const navigate = useNavigate();

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
        navigate("/login");
    };

    return (
        <Box sx={TopBarContainerStyles}>
            {/* Logo alineado con el centro del sidebar colapsado */}
            <Box 
                display="flex" 
                alignItems="center"
                onClick={handleInicio} 
                sx={{ 
                    cursor: "pointer",
                    width: sidebarWidth, // Ancho del sidebar + margen
                    justifyContent: "start",
                    flexShrink: 0,
                    ml:"15px"
                }}
            >
                <Box
                    component="img"
                    src={LogoSMT}
                    sx={{ width: "60px" }}
                />
            </Box>
            
            {/* Texto Digitaliza */}
            <Box 
                component="img"
                src={TextDigitaliza}
                onClick={handleInicio}
                sx={{ 
                    width: {lg:"200px", xl:"230px"}, 
                    cursor: "pointer",
                    marginLeft: -2.5,
                    mt:1
                }} 
            />
            
            {/* Spacer */}
            <Box sx={{ flex: 1 }} />
            {/* Botón del Avatar (trigger del menú) - sin caja */}
            <Box
                onClick={handleClick}
                sx={AvatarButtonStyles}
            >
                <Avatar
                    src={USER_DATA.avatar}
                    alt={USER_DATA.name}
                    sx={AvatarStyles}
                />
                <Box sx={UserInfoStyles}>
                    <Typography sx={UserNameStyles}>
                        {USER_DATA.name}
                    </Typography>
                    <Typography sx={RoleBadgeSmallStyles}>
                        ● {USER_DATA.role}
                    </Typography>
                </Box>
                <KeyboardArrowDownIcon
                    sx={{
                        ...ArrowIconStyles,
                        transform: open ? "rotate(180deg)" : "rotate(0deg)",
                    }}
                />
            </Box>

            {/* Menú desplegable estilo Spotify */}
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
                {/* Perfil - estilo Spotify */}
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

                {/* Cerrar sesión */}
                <MenuItem onClick={handleLogout} sx={MenuItemStyles}>
                    <LogoutIcon fontSize="small" />
                    Cerrar sesión
                </MenuItem>
            </Menu>
        </Box>
    );
};

export default TopBar;
