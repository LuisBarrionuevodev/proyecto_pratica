import { Button, TextField, Typography } from "@mui/material";
import { useState } from "react";
import {
  ButtonRecuperarStyles,
  ErrorTextRecuperarStyles,
  InputRecuperarStyles,
} from "../../../styles/RecuperarCuentaStyles";
import { RecuperarCuentaStepShell } from "./RecuperarCuentaStepShell";

interface CodigoBoxProps {
  email: string;
  onCodeChange: (code: string) => void;
  onSuccess: () => void;
}

const CodigoBox = ({ email, onCodeChange, onSuccess }: CodigoBoxProps) => {
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState("");

  const handleCodigo = () => {
    if (codigo.trim().length === 6) {
      setError("");
      onCodeChange(codigo.trim());
      onSuccess();
    } else {
      setError("El código debe tener 6 dígitos");
    }
  };

  return (
    <RecuperarCuentaStepShell
      title="Recuperar contraseña"
      subtitle={
        <>
          Verifique el código enviado a <strong>{email}</strong>
        </>
      }
    >
      <TextField
        placeholder="Código de verificación"
        fullWidth
        value={codigo}
        onChange={(e) => setCodigo(e.target.value)}
        sx={InputRecuperarStyles}
        inputProps={{ inputMode: "numeric", autoComplete: "one-time-code" }}
      />

      {error ? <Typography sx={ErrorTextRecuperarStyles}>{error}</Typography> : null}

      <Button onClick={handleCodigo} sx={ButtonRecuperarStyles} fullWidth>
        Verificar
      </Button>
    </RecuperarCuentaStepShell>
  );
};

export default CodigoBox;
