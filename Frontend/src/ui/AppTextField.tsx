import type { TextFieldProps } from "@mui/material/TextField";
import TextField from "@mui/material/TextField";
import { useTheme } from "@mui/material/styles";
import { color as tokenColor } from "../theme/tokens";
import { fieldErrorOutlineSx } from "./fieldErrorSx";

export type AppTextFieldAppearance = "default" | "dense" | "glass";

export type AppTextFieldProps = TextFieldProps & {
  appearance?: AppTextFieldAppearance;
};

function glassFieldSx() {
  return {
    "& .MuiOutlinedInput-root": {
      backgroundColor: tokenColor.cardBg,
    },
    "& .MuiOutlinedInput-notchedOutline": {
      borderColor: tokenColor.borderMedium,
    },
    "&:hover .MuiOutlinedInput-notchedOutline": {
      borderColor: tokenColor.borderLight,
    },
    "& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
      borderColor: tokenColor.primary,
    },
    "& .MuiInputLabel-root.Mui-focused": {
      color: tokenColor.primary,
    },
  };
}

/**
 * Campo de texto del design system DIGITALIZA.
 *
 * Qué hace: TextField outlined con apariencias default | dense | glass (tokens).
 * Parámetros: props de MUI TextField; `appearance` opcional.
 * Retorno: TextField.
 */
export function AppTextField({
  appearance = "default",
  variant = "outlined",
  size,
  sx,
  slotProps,
  InputProps,
  error,
  ...rest
}: AppTextFieldProps) {
  const theme = useTheme();
  const resolvedSize = appearance === "dense" ? "small" : size ?? "medium";
  const appearanceSx = appearance === "glass" ? glassFieldSx() : {};
  const errorSx = error ? fieldErrorOutlineSx(theme) : {};

  return (
    <TextField
      variant={variant}
      size={resolvedSize}
      error={error}
      slotProps={slotProps}
      InputProps={InputProps}
      sx={[appearanceSx, errorSx, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
      {...rest}
    />
  );
}
