import { useState } from "react";
import { Box, Button, TextField, Typography } from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { buttonStyle, inputDarkStyle } from "../../../styles/PerfilStyles";

interface Props {
  onPasswordChange?: (data: {
    currentPassword: string;
    newPassword: string;
  }) => void;
}

const BoxCambiarInfo = ({ onPasswordChange }: Props) => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSave = () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError("Todos los campos son obligatorios.");
      return;
    }

    if (newPassword.length < 6) {
      setError("La nueva contraseña debe tener al menos 6 caracteres.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setError(null);

    onPasswordChange?.({
      currentPassword,
      newPassword,
    });

    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  return (
    <Box
      sx={{
        backgroundColor: "#2B2E34",
        borderRadius: "16px",
        border: "1px solid #3a3d44",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
        display: "flex",
        flexDirection: "column",
        width: { xs: "230px", sm: "450px", md: "550px" },
        gap: 3,
        p: { xs: 3, sm: 4 },
      }}
    >
      
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
          Contraseña actual
        </Typography>
        <TextField
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          placeholder="Ingresa tu contraseña actual"
          size="small"
          type="password"
          fullWidth
          sx={inputDarkStyle}
        />
      </Box>

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
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="••••••••••"
          type="password"
          size="small"
          fullWidth
          sx={inputDarkStyle}
        />
      </Box>

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
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="••••••••••"
          type="password"
          size="small"
          fullWidth
          error={!!error}
          helperText={error}
          sx={inputDarkStyle}
        />
      </Box>

      {/* Botón */}
      <Button sx={buttonStyle} onClick={handleSave}>
        Guardar cambios
      </Button>
    </Box>
  );
};

export default BoxCambiarInfo;