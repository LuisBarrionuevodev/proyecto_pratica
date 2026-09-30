import { useState } from "react";
import { Box, Typography } from "@mui/material";
import { AppButton, AppTextField } from "../../../ui";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import {
  buttonStyle,
  profileFieldLabelSx,
  profileInputStyle,
  profilePasswordCardSx,
} from "../../../styles/PerfilStyles";
import { FONT_FAMILY_UI } from "../../../theme/typography";

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
    <Box sx={profilePasswordCardSx}>
      
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <LockOutlinedIcon sx={{ color: "#0166FF", fontSize: 24 }} />
        <Typography
          sx={{
            fontFamily: FONT_FAMILY_UI,
            fontSize: { xs: 18, sm: 20 },
            fontWeight: 700,
            color: "var(--d-text-primary)",
          }}
        >
          Cambiar contraseña
        </Typography>
      </Box>


      <Box>
        <Typography sx={profileFieldLabelSx}>Contraseña actual</Typography>
        <AppTextField
          appearance="default"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          placeholder="Ingresa tu contraseña actual"
          size="small"
          type="password"
          fullWidth
          sx={profileInputStyle}
        />
      </Box>

      <Box>
        <Typography sx={profileFieldLabelSx}>Nueva contraseña</Typography>
        <AppTextField
          appearance="default"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="••••••••••"
          type="password"
          size="small"
          fullWidth
          sx={profileInputStyle}
        />
      </Box>

      <Box>
        <Typography sx={profileFieldLabelSx}>Confirmar contraseña</Typography>
        <AppTextField
          appearance="default"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="••••••••••"
          type="password"
          size="small"
          fullWidth
          error={!!error}
          helperText={error}
          sx={profileInputStyle}
        />
      </Box>

      {/* Botón */}
      <AppButton dsVariant="primary" sx={buttonStyle} onClick={handleSave}>
        Guardar cambios
      </AppButton>
    </Box>
  );
};

export default BoxCambiarInfo;