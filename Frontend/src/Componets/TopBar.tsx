import { useEffect, useState } from "react";

import {

    Box,

    Avatar,

    Typography,

    Menu,

    MenuItem,

    Divider,

    Skeleton,

} from "@mui/material";

import { getAvatarUrl } from "../utils/avatarUrl";

import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";

import PersonOutlineIcon from "@mui/icons-material/PersonOutline";

import LogoutIcon from "@mui/icons-material/Logout";

import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import TextDigitaliza from "../assets/TextDigitaliza.svg"

import LogoSMT from "../assets/LogoSMT.svg"

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

}



const TopBar: React.FC<TopBarProps> = ({ sidebarWidth = 72 }) => {

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

            <Box 

                display="flex" 

                alignItems="center"

                onClick={handleInicio} 

                sx={{ 

                    cursor: "pointer",

                    width: sidebarWidth,

                    justifyContent: "start",

                    flexShrink: 0,

                    ml:{xs:"-5px", sm:"15px"}

                }}

            >

                <Box

                    component="img"

                    src={LogoSMT}

                    sx={{ width: "60px" }}

                />

            </Box>

            

            <Box 

                component="img"

                src={TextDigitaliza}

                onClick={handleInicio}

                sx={{ 

                    width: {lg:"200px", xl:"230px"}, 

                    cursor: "pointer",

                    ml:{xs:-3, sm:-2.5},

                    mt:1

                }} 

            />

            

            <Box sx={{ flex: 1 }} />

            <Box

                onClick={handleClick}

                sx={AvatarButtonStyles}

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

                <Box sx={UserInfoStyles}>

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

