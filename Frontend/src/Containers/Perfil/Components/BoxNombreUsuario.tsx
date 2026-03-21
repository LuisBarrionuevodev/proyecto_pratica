import { useEffect, useState } from "react";
import { Box, Typography, Avatar, Popover, IconButton } from "@mui/material";
import { AppTextField } from "../../../ui";
import EditIcon from "@mui/icons-material/Edit";
import { AvatarPerfilStye, BoxPerfilStyle, EditNombreStyle, NombrePerfilStyle, RolPerfilStyle } from "../../../styles/PerfilStyles";

type AvatarType =
    | "avatar1"
    | "avatar2"
    | "avatar3"
    | "avatar4"
    | "avatar5";

const avatars: AvatarType[] = [
    "avatar1",
    "avatar2",
    "avatar3",
    "avatar4",
    "avatar5",
];

interface Props {
    user?: string;
    nombre?: string;
    rol?: string;
    avatarInicial?: AvatarType;
    onAvatarChange?: (avatar: AvatarType) => void;
    onNameChange?: (name: string) => void;
}

const BoxNombreUsuario = ({
    user = "",
    nombre = "",
    rol = "Administrador",
    avatarInicial = "avatar1",
    onAvatarChange,
    onNameChange,
}: Props) => {
    const [avatar, setAvatar] = useState<AvatarType>(avatarInicial);
    const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

    const [editing, setEditing] = useState(false);
    const [nameValue, setNameValue] = useState(nombre);

    useEffect(() => {
        setAvatar(avatarInicial);
    }, [avatarInicial]);

    useEffect(() => {
        setNameValue(nombre);
    }, [nombre]);

    const open = Boolean(anchorEl);

    const handleSelectAvatar = (selected: AvatarType) => {
        setAvatar(selected);
        setAnchorEl(null);
        onAvatarChange?.(selected);
    };

    const handleOpen = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorEl(event.currentTarget);
    };


    const handleClose = () => {
        setAnchorEl(null);
    };


    const handleSaveName = () => {
        setEditing(false);
        onNameChange?.(nameValue);
    };

    return (
        <Box
            sx={BoxPerfilStyle}
        >
            {/* Avatar clickeable */}
            <Avatar
                src={`https://api.dicebear.com/9.x/lorelei-neutral/svg?seed=${avatar}`}
                alt={nombre}
                onClick={handleOpen}
                sx={AvatarPerfilStye}
            />

            {/* Popover selector */}
            <Popover
                open={open}
                anchorEl={anchorEl}
                onClose={handleClose}
                anchorOrigin={{
                    vertical: "bottom",
                    horizontal: "left",
                }}
            >
                <Box
                    sx={{
                        display: "flex",
                        gap: 2,
                        p: 2,
                        backgroundColor: "#1A1C20",
                    }}
                >
                    {avatars.map((av) => (
                        <Avatar
                            key={av}
                            src={`/avatars/${av}.png`}
                            onClick={() => handleSelectAvatar(av)}
                            sx={{
                                width: 70,
                                height: 70,
                                cursor: "pointer",
                                border:
                                    avatar === av
                                        ? "3px solid #1976d2"
                                        : "2px solid transparent",
                            }}
                        />
                    ))}
                </Box>
            </Popover>

            {/* Info */}
            <Box sx={{ display: "flex", flexDirection: "column",alignItems:{xs:"center",md:"normal"}, gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    <Typography
                        sx={RolPerfilStyle}
                    >
                        {rol} • SMT Digitaliza • {user}
                    </Typography>
                </Box>

                {/* Nombre editable */}
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    {editing ? (
                        <AppTextField
                            appearance="default"
                            value={nameValue}
                            onChange={(e) => {
                                if (e.target.value.length <= 20) {
                                    setNameValue(e.target.value);
                                }
                            }}
                            onBlur={handleSaveName}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") handleSaveName();
                                if (e.key === "Escape") {
                                    setNameValue(nombre || "");
                                    setEditing(false);
                                }
                            }}
                            autoFocus
                            variant="standard"
                            slotProps={{
                                htmlInput: {
                                    maxLength: 20,
                                },
                            }}
                            helperText={`${nameValue.length} / 20`}
                            sx={EditNombreStyle}
                        />
                    ) : (
                        <>
                            <Typography
                                sx={NombrePerfilStyle}
                            >
                                {nameValue}
                            </Typography>

                            <IconButton
                                onClick={() => setEditing(true)}
                                sx={{ color: "#fff" }}
                            >
                                <EditIcon />
                            </IconButton>
                        </>
                    )}
                </Box>

            </Box>
        </Box>
    );
};

export default BoxNombreUsuario;