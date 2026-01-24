import { Box, Button, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { BoxRecuperarContenidoStyles, ButtonRecuperarStyles, ErrorTextRecuperarStyles, InputRecuperarStyles } from "../../../styles/RecuperarCuentaStyles";

interface CodigoBoxProps {
    email: string;
    onSuccess: () => void;
}

const CodigoBox = ({ email, onSuccess }: CodigoBoxProps) => {
    const [codigo, setCodigo] = useState("");
    const [error, setError] = useState("");

    const handleCodigo = () => {
        if (codigo === "1234") {
            setError("");
            onSuccess(); // 👈 avisa al padre
        } else {
            setError("El código ingresado es incorrecto");
        }
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
                sx={BoxRecuperarContenidoStyles}
            >

                <Typography sx={{ fontWeight: 500, fontSize: 25 }}>
                    Verifica el codigo
                </Typography>

                <Typography sx={{ fontSize: 15 }}>
                    Enviamos un código a <strong>{email}</strong>
                </Typography>

                <TextField
                    placeholder="Código de verificación"
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value)}
                    sx={InputRecuperarStyles}
                />

                {error && (
                    <Typography sx={ErrorTextRecuperarStyles}>
                        {error}
                    </Typography>
                )}

                <Button
                    onClick={handleCodigo}
                    sx={ButtonRecuperarStyles}
                >
                    Verificar
                </Button>
            </Box>
        </Box>
    );
};

export default CodigoBox;