import { Alert, Box, Typography } from "@mui/material";
import { FONT_FAMILY_UI } from "../../../theme/typography";
import { AppButton, AppTextField } from "../../../ui";
import { ButtonStyle, InputStyles, LoginBoxGlobalStyle, LoginBoxInputStyles, LoginBoxStyle, LoginLogoStyle } from "../../../styles/LoginStyles";
import type { JSX } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiClient } from "../../../api/apiClient";
import { notifyAuthSessionRefresh } from "../../../auth/AppSessionProvider";
import { normalizeAppRole, postLoginPathForRole } from "../../../auth/roles";
import {
    consumeSessionEndFeedback,
    sessionEndUserMessage,
} from "../../../auth/sessionEndFeedback";
import {
    appWebUpdateButtonLabel,
    detectAppWebUpdateMode,
    runAppWebUpdate,
    type AppWebUpdateMode,
} from "../../../utils/appWebUpdate";

const LoginBox = (): JSX.Element => {
    
    const navigate = useNavigate();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [sessionInfo, setSessionInfo] = useState<string | null>(null);
    const [webUpdateMode, setWebUpdateMode] = useState<AppWebUpdateMode>("hard_reload");
    const [webUpdateBusy, setWebUpdateBusy] = useState(false);

    useEffect(() => {
        const payload = consumeSessionEndFeedback();
        if (payload) {
            setSessionInfo(sessionEndUserMessage(payload.reason));
        }
    }, []);

    useEffect(() => {
        void detectAppWebUpdateMode().then(setWebUpdateMode);
    }, []);

    const handleAppWebUpdate = () => {
        if (webUpdateBusy) return;
        setWebUpdateBusy(true);
        void runAppWebUpdate(webUpdateMode).finally(() => setWebUpdateBusy(false));
    };

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
            setSessionInfo(null);
            notifyAuthSessionRefresh();
            const apiRole = data?.user?.role ?? data?.role;
            navigate(postLoginPathForRole(normalizeAppRole(apiRole)));
        } catch {
            setError("Cuenta inválida");
        }
    };

    return (
        <Box sx={LoginBoxGlobalStyle}>
            <Box sx={LoginBoxStyle}>
                <Box sx={LoginLogoStyle}>
                    <Typography
                        sx={{
                            fontFamily: FONT_FAMILY_UI,
                            fontWeight: 500,
                            fontSize: { xs: "1.75rem", sm: "35px" },
                            textAlign: "center",
                        }}
                    >
                        Iniciar Sesión
                    </Typography>
                </Box>

                <Box sx={LoginBoxInputStyles}>
                    {sessionInfo && (
                        <Alert severity="info" sx={{ mb: 1.5, textAlign: "left" }} onClose={() => setSessionInfo(null)}>
                            {sessionInfo}
                        </Alert>
                    )}
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
                        sx={[ButtonStyle, { py: 0, boxSizing: "border-box", alignSelf: "center" }]}
                        fullWidth
                        onClick={handleLogin}
                    >
                        Ingresar
                    </AppButton>

                    <Typography
                        sx={{ mt: { xs: 1, sm: 1.25 }, mb: 0, textAlign: "center", fontSize: 14, color: "#0166FF", fontWeight: 500 }}
                    >
                        ¿Has olvidado tu contraseña?
                        <Link to={"/recuperarCuenta"} style={{fontWeight:800, textDecoration: "none", color: "#0166FF", }}> Haz click aqui</Link>
                    </Typography>

                    <AppButton
                        dsVariant="ghost"
                        dsSize="sm"
                        type="button"
                        disabled={webUpdateBusy}
                        onClick={handleAppWebUpdate}
                        sx={{
                            mt: { xs: 1.5, sm: 2 },
                            alignSelf: "center",
                            fontSize: 13,
                            color: "text.secondary",
                            fontWeight: 500,
                            textTransform: "none",
                            minHeight: 36,
                        }}
                    >
                        ↻ {appWebUpdateButtonLabel(webUpdateMode)}
                    </AppButton>
                </Box>
            </Box>
        </Box>
    );
};

export default LoginBox;
