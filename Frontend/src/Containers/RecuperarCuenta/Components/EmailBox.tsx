import { Box, Button, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { BoxRecuperarContenidoStyles, ButtonRecuperarStyles, ErrorTextRecuperarStyles, InputRecuperarStyles } from "../../../styles/RecuperarCuentaStyles";

interface EmailBoxProps {
  onSuccess: () => void;
  setEmailGlobal: (email: string) => void;
}

const EmailBox = ({ onSuccess, setEmailGlobal }: EmailBoxProps) => {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  const handleEmail = () => {
    if (email === "eliasasfoura7@gmail.com") {
      setError("");
      setEmailGlobal(email);
      onSuccess();
    } else {
      setError(
        "El correo ingresado no está asociado a una cuenta en nuestro sistema"
      );
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
        <Typography sx={{ fontSize: 20, fontWeight: 500 }}>
          Ingrese su Correo Electrónico
        </Typography>

        <TextField
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          sx={InputRecuperarStyles}
        />

        {error && (
          <Typography sx={ErrorTextRecuperarStyles}>
            {error}
          </Typography>
        )}

        <Button
          onClick={handleEmail}
          sx={ButtonRecuperarStyles}
        >
          Enviar
        </Button>
      </Box>
    </Box>
  );
};

export default EmailBox;