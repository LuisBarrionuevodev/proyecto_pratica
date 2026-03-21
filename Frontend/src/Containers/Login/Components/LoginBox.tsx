import { Box, Typography } from "@mui/material";
import { AppButton, AppTextField } from "../../../ui";
import { ButtonStyle, InputStyles, LoginBoxGlobalStyle, LoginBoxInputStyles, LoginBoxStyle, LoginLogoStyle } from "../../../styles/LoginStyles";
import LogoSMT from "../../../assets/LogoSMT.svg"
import TextDigitaliza from "../../../assets/TextDigitaliza.svg"
import type { JSX } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { apiClient } from "../../../api/apiClient";

const LoginBox = (): JSX.Element => {
    
    const navigate = useNavigate();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");

    const handleLogin = async () => {
        try {
            const response = await apiClient.post("/api/auth/login", {
                username,
                password,
            });
            const data = response.data;
            if (data?.access_token) {
                localStorage.setItem("access_token", data.access_token);
            }
            setError("");
            navigate("/inicio");
        } catch {
            setError("Cuenta inválida");
        }
    };

    return (
        <Box sx={LoginBoxGlobalStyle}>
            <Box sx={LoginBoxStyle}>
                <Box sx={LoginLogoStyle}>
                    <img src={LogoSMT} alt="" style={{width:"120px"}} />
                    <img src={TextDigitaliza} alt="" style={{ width: "200px" }} />
                </Box>

                <Box sx={LoginLogoStyle}>
                    <Typography sx={{ fontFamily: "Tactic Sans", fontWeight: 500, fontSize: "35px" }}>
                        Iniciar Sesión
                    </Typography>
                </Box>

                <Box sx={LoginBoxInputStyles}>
                    <AppTextField
                        appearance="default"
                        sx={InputStyles}
                        placeholder="Usuario"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />

                    <AppTextField
                        appearance="default"
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

                    <AppButton
                        dsVariant="primary"
                        dsSize="sm"
                        sx={[ButtonStyle, { minHeight: 25, height: 25, py: 0, boxSizing: "border-box" }]}
                        onClick={handleLogin}
                    >
                        Ingresar
                    </AppButton>

                    <Typography mt={2} textAlign={"center"} fontSize={14}  color="#0166FF" fontWeight={500}>¿Has olvidado tu contraseña? 
                        <Link to={"/recuperarCuenta"} style={{fontWeight:800, textDecoration: "none", color: "#0166FF", }}> Haz click aqui</Link>
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

export default LoginBox;
