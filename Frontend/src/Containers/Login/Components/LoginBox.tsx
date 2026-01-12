import { Box, Button, TextField, Typography } from "@mui/material";
import { ButtonStyle, InputStyles, LoginBoxGlobalStyle, LoginBoxInputStyles, LoginBoxStyle, LoginLogoStyle } from "../../../styles/LoginStyles";
import Logo from "../assets-login/Logo.svg";
import type { JSX } from "react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

const LoginBox = (): JSX.Element => {
    
    const navigate = useNavigate();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");

    const handleLogin = () => {
        if (username === "PeritoMercantil3" && password === "1234") {
            setError("");
            navigate("/inicio");
        } else {
            setError("Cuenta inválida");
        }
    };

    return (
        <Box sx={LoginBoxGlobalStyle}>
            <Box sx={LoginBoxStyle}>
                <Box sx={LoginLogoStyle}>
                    <img src={Logo} alt="" style={{ width: "100px" }} />
                </Box>

                <Box sx={LoginLogoStyle}>
                    <Typography sx={{ fontFamily: "Tactic Sans", fontWeight: 500, fontSize: "35px" }}>
                        Iniciar Sesión
                    </Typography>
                </Box>

                <Box sx={LoginBoxInputStyles}>
                    <TextField 
                        sx={InputStyles}
                        placeholder="Usuario"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />

                    <TextField 
                        sx={InputStyles}
                        placeholder="Contraseña"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />

                    {error && (
                        <Typography sx={{ color: "red", fontSize: "14px", marginTop: "5px" }}>
                            {error}
                        </Typography>
                    )}

                    <Button sx={ButtonStyle} onClick={handleLogin}>
                        Ingresar
                    </Button>
                </Box>
            </Box>
        </Box>
    );
};

export default LoginBox;
