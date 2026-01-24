import { Box, Button, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { BoxNuevaContraseñaStyles, ButtonRecuperarStyles, ErrorTextRecuperarStyles, InputRecuperarStyles } from "../../../styles/RecuperarCuentaStyles";

const NuevaContraseña = () => {
    const [password, setPassword] = useState("");
    const [repeatPassword, setRepeatPassword] = useState("");
    const [error, setError] = useState("");

    const handleContraseña = () => {
        if (!password || !repeatPassword) {
            setError("Debe completar ambos campos");
            return;
        }

        if (password !== repeatPassword) {
            setError("Las contraseñas no coinciden");
            return;
        }

        if (password.length < 8) {
            setError("La contraseña debe tener al menos 8 caracteres");
            return;
        }

        setError("");
        console.log("Contraseña cambiada correctamente");
        
    };

    return (
        <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            flexDirection="column"
        >
            <Typography sx={{ fontWeight: 500, fontSize: 40 }}>
                Recuperar Contraseña
            </Typography>

            <Box
                sx={BoxNuevaContraseñaStyles}
            >

                <Typography sx={{ fontSize: 20, fontWeight: 500 }}>
                    Ingrese una nueva contraseña
                </Typography>

                <TextField
                    type="password"
                    placeholder="Contraseña"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    sx={InputRecuperarStyles}
                />

                <TextField
                    type="password"
                    placeholder="Repetir Contraseña"
                    value={repeatPassword}
                    onChange={(e) => setRepeatPassword(e.target.value)}
                    sx={InputRecuperarStyles}
                />

                {error && (
                    <Typography sx={ErrorTextRecuperarStyles}>
                        {error}
                    </Typography>
                )}

                <Button
                    onClick={handleContraseña}
                    sx={ButtonRecuperarStyles}
                >
                    Confirmar
                </Button>
            </Box>
        </Box>
    );
};

export default NuevaContraseña;