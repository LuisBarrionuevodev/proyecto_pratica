import { Box, Button, TextField, Typography } from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";

/**
 * BoxCambiarInfo - Card de cambio de contraseña estilo Spotify/dark theme
 * 
 * Estilo: card oscura con bordes suaves, inputs dark mode
 */
const BoxCambiarInfo = () => {
    // Estilos dark mode para inputs
    const inputDarkStyle = {
        width: "100%",
        "& .MuiInputBase-input": {
            fontFamily: '"Tactic Sans", sans-serif',
            fontWeight: 500,
            color: "#FFFFFF",
            fontSize: "14px",
        },
        "& .MuiOutlinedInput-root": {
            backgroundColor: "#2B2E34",
            borderRadius: "8px",
            "& fieldset": {
                borderColor: "#3a3d44",
            },
            "&:hover fieldset": {
                borderColor: "#535353",
            },
            "&.Mui-focused fieldset": {
                borderColor: "#0166FF",
                borderWidth: "2px",
            },
        },
        "& .MuiInputBase-input::placeholder": {
            color: "rgba(255, 255, 255, 0.5)",
            opacity: 1,
        },
    };

    const buttonStyle = {
        backgroundColor: "#0166FF",
        color: "#FFFFFF",
        fontFamily: '"Tactic Sans", sans-serif',
        fontWeight: 600,
        fontSize: "14px",
        height: "48px",
        width: "100%",
        borderRadius: "24px",
        textTransform: "none",
        mt: 2,
        transition: "all 0.2s ease",
        "&:hover": {
            backgroundColor: "#0055DD",
            transform: "scale(1.02)",
        },
    };

    return (
        <Box
            sx={{
                backgroundColor: "#2B2E34",
                borderRadius: "16px",
                border: "1px solid #3a3d44",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
                display: "flex",
                flexDirection: "column",
                width: "100%",
                gap: 3,
                p: { xs: 3, sm: 4 },
            }}
        >
            {/* Header del card */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <LockOutlinedIcon sx={{ color: "#0166FF", fontSize: 24 }} />
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        fontSize: { xs: 18, sm: 20 },
                        fontWeight: 700,
                        color: "#FFFFFF",
                    }}
                >
                    Cambiar contraseña
                </Typography>
            </Box>

            {/* Campo Nombre */}
            <Box>
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        ml: 1,
                        mb: 1,
                        fontSize: 13,
                        fontWeight: 500,
                        color: "rgba(255, 255, 255, 0.7)",
                    }}
                >
                    Nombre
                </Typography>
                <TextField
                    placeholder="Ingresa tu nombre"
                    size="small"
                    fullWidth
                    sx={inputDarkStyle}
                />
            </Box>

            {/* Campo Contraseña */}
            <Box>
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        ml: 1,
                        mb: 1,
                        fontSize: 13,
                        fontWeight: 500,
                        color: "rgba(255, 255, 255, 0.7)",
                    }}
                >
                    Nueva contraseña
                </Typography>
                <TextField
                    placeholder="••••••••••"
                    type="password"
                    size="small"
                    fullWidth
                    sx={inputDarkStyle}
                />
            </Box>

            {/* Campo Repetir Contraseña */}
            <Box>
                <Typography
                    sx={{
                        fontFamily: '"Tactic Sans", sans-serif',
                        ml: 1,
                        mb: 1,
                        fontSize: 13,
                        fontWeight: 500,
                        color: "rgba(255, 255, 255, 0.7)",
                    }}
                >
                    Confirmar contraseña
                </Typography>
                <TextField
                    placeholder="••••••••••"
                    type="password"
                    size="small"
                    fullWidth
                    sx={inputDarkStyle}
                />
            </Box>

            {/* Botón Guardar */}
            <Button sx={buttonStyle}>
                Guardar cambios
            </Button>
        </Box>
    );
};

export default BoxCambiarInfo;