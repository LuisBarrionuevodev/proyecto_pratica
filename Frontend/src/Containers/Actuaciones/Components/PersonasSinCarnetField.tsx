import { memo } from "react";

import { AppTextField } from "../../../ui";

export type PersonasSinCarnetFieldProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  error?: string;
  appearance?: "glass" | "default";
};

export const PersonasSinCarnetField = memo(function PersonasSinCarnetField({
  value,
  onChange,
  disabled = false,
  error,
  appearance = "glass",
}: PersonasSinCarnetFieldProps) {
  return (
    <AppTextField
      appearance={appearance}
      label="Personas sin carnet de sanidad"
      type="number"
      inputProps={{ min: 0, step: 1 }}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      fullWidth
      error={Boolean(error)}
      helperText={error || undefined}
    />
  );
});

export function isValidActaNotificacionNum(value: string | null | undefined): boolean {
  const t = String(value ?? "").trim();
  return t.length > 0 && /^\d+$/.test(t);
}
