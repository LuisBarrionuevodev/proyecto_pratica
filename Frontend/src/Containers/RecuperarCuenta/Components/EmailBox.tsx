import { Button, TextField, Typography } from "@mui/material";
import { useState } from "react";
import {
  ButtonRecuperarStyles,
  ErrorTextRecuperarStyles,
  InputRecuperarStyles,
} from "../../../styles/RecuperarCuentaStyles";
import { apiClient } from "../../../api/apiClient";
import { RecuperarCuentaStepShell } from "./RecuperarCuentaStepShell";

interface EmailBoxProps {
  onSuccess: () => void;
  setEmailGlobal: (email: string) => void;
}

const EmailBox = ({ onSuccess, setEmailGlobal }: EmailBoxProps) => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  const handleEmail = async () => {
    try {
      await apiClient.post("/api/auth/password-reset/request", { email });
      setError("");
      setEmailGlobal(email);
      onSuccess();
    } catch {
      setError("No se pudo enviar el código. Verifique el correo e intente nuevamente.");
    }
  };

  return (
    <RecuperarCuentaStepShell
      title="Recuperar contraseña"
      subtitle="Ingrese su correo electrónico"
    >
      <TextField
        placeholder="Email"
        type="email"
        fullWidth
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        sx={InputRecuperarStyles}
        inputProps={{ autoComplete: "email" }}
      />

      {error ? <Typography sx={ErrorTextRecuperarStyles}>{error}</Typography> : null}

      <Button onClick={handleEmail} sx={ButtonRecuperarStyles} fullWidth>
        Enviar
      </Button>
    </RecuperarCuentaStepShell>
  );
};

export default EmailBox;
