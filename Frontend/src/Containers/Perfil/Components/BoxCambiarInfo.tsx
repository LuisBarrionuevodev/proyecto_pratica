import { Box, Button, TextField, Typography } from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { buttonStyle, inputDarkStyle } from "../../../styles/PerfilStyles";

const BoxCambiarInfo = () => {

    return (
        <Box
            sx={{
                backgroundColor: "#2B2E34",
                borderRadius: "16px",
                border: "1px solid #3a3d44",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
                display: "flex",
                flexDirection: "column",
                width: {xs:"230px",sm:"450px",md:"550px"},
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
                    Contraseña Actual
                </Typography>
                <TextField
                    placeholder="Ingresa tu contraseña actual"
                    size="small"
                    type="password"
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