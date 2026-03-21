import type { MenuItemProps } from "@mui/material/MenuItem";
import MenuItem from "@mui/material/MenuItem";
import type { TextFieldProps } from "@mui/material/TextField";
import TextField from "@mui/material/TextField";
import type { ReactNode } from "react";
import { color as tokenColor } from "../theme/tokens";

export type AppSelectAppearance = "default" | "dense" | "glass";

export type AppSelectOption = {
  value: string | number;
  label: ReactNode;
  disabled?: boolean;
  MenuItemProps?: Partial<MenuItemProps>;
};

export type AppSelectProps = Omit<TextFieldProps, "select" | "type"> & {
  appearance?: AppSelectAppearance;
  options?: AppSelectOption[];
  children?: ReactNode;
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
 * Select del design system DIGITALIZA (TextField + select).
 *
 * Qué hace: Select outlined con `options` o `children` (MenuItem).
 * Parámetros: props de TextField (sin select/type); `appearance`; `options` o `children`.
 * Retorno: TextField en modo select.
 */
export function AppSelect({
  appearance = "default",
  variant = "outlined",
  size,
  sx,
  options,
  children,
  SelectProps,
  slotProps,
  InputProps,
  ...rest
}: AppSelectProps) {
  const resolvedSize = appearance === "dense" ? "small" : size ?? "medium";
  const appearanceSx = appearance === "glass" ? glassFieldSx() : {};

  const selectChildren =
    options?.map((opt) => (
      <MenuItem
        key={String(opt.value)}
        value={opt.value as string | number}
        disabled={opt.disabled}
        {...opt.MenuItemProps}
      >
        {opt.label}
      </MenuItem>
    )) ?? children;

  return (
    <TextField
      select
      variant={variant}
      size={resolvedSize}
      SelectProps={SelectProps}
      slotProps={slotProps}
      InputProps={InputProps}
      sx={[appearanceSx, ...(Array.isArray(sx) ? sx : sx ? [sx] : [])]}
      {...rest}
    >
      {selectChildren}
    </TextField>
  );
}
