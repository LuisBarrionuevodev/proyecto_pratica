import { Button, TextField, Typography } from "@mui/material";
import { useState } from "react";
import {
  ButtonRecuperarStyles,
  ErrorTextRecuperarStyles,
  InputRecuperarStyles,
} from "../../../styles/RecuperarCuentaStyles";
import { apiClient } from "../../../api/apiClient";
import { RecuperarCuentaStepShell } from "./RecuperarCuentaStepShell";

interface NuevaContraseñaProps {
  email: string;
  code: string;
  onSuccess: () => void;
}

const NuevaContraseña = ({ email, code, onSuccess }: NuevaContraseñaProps) => {
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [error, setError] = useState("");

  const handleContraseña = async () => {
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

    try {
      await apiClient.post("/api/auth/password-reset/confirm", {
        email,
        code,
        new_password: password,
        new_password2: repeatPassword,
      });
      setError("");
      onSuccess();
    } catch {
      setError("Código inválido o vencido");
    }
  };

  return (
    <RecuperarCuentaStepShell title="Recuperar contraseña" subtitle="Ingrese una nueva contraseña">
      <TextField
        type="password"
        placeholder="Contraseña"
        fullWidth
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        sx={InputRecuperarStyles}
        inputProps={{ autoComplete: "new-password" }}
      />

      <TextField
        type="password"
        placeholder="Repetir contraseña"
        fullWidth
        value={repeatPassword}
        onChange={(e) => setRepeatPassword(e.target.value)}
        sx={InputRecuperarStyles}
        inputProps={{ autoComplete: "new-password" }}
      />

      {error ? <Typography sx={ErrorTextRecuperarStyles}>{error}</Typography> : null}

      <Button onClick={handleContraseña} sx={ButtonRecuperarStyles} fullWidth>
        Confirmar
      </Button>
    </RecuperarCuentaStepShell>
  );
};

export default NuevaContraseña;
