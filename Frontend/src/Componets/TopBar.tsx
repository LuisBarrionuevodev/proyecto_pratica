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
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
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
    MenuItemLogoutStyles,
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

const TopBar = () => {
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
        navigate("/perfil"); // <-- Redirige a /perfil
    };

    const handleInicio = () => {
        navigate("/inicio")
    }

    const handleAboutUs = () => {
        handleClose();
        navigate("/nosotros"); // <-- Redirige a /nosotros
    };

    const handleLogout = () => {
        handleClose();
        // TODO: implementar logout real
        navigate("/login"); // <-- Redirige a login
    };

    return (
        <Box sx={TopBarContainerStyles}>
            <Box ml={1} display={"flex"} onClick={handleInicio} sx={{ cursor: "pointer" }}>
                <Box
                    component={"img"}
                    src={LogoSMT}
                    sx={{ width: "100px", }} />

                <Box
                    component={"img"}
                    src={TextDigitaliza}
                    sx={{ width: "250px" }} />
            </Box>
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

            {/* Menú desplegable - solo opciones, sin duplicar foto */}
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
                        sx: MenuPaperStyles,
                    },
                }}
            >
                {/* Opciones del menú */}

                <MenuItem onClick={handleViewProfile} sx={MenuItemStyles}>
                    <PersonOutlineIcon fontSize="small" />
                    Ver perfil
                </MenuItem>


                <MenuItem onClick={handleAboutUs} sx={MenuItemStyles}>
                    <InfoOutlinedIcon fontSize="small" />
                    Nosotros
                </MenuItem>

                <Divider sx={MenuDividerStyles} />

                <MenuItem onClick={handleLogout} sx={MenuItemLogoutStyles}>
                    <LogoutIcon fontSize="small" />
                    Cerrar sesión
                </MenuItem>
            </Menu>
        </Box>
    );
};

export default TopBar;
