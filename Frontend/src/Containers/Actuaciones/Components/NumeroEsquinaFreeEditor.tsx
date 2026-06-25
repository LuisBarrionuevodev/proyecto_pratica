import { Box, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

import { AppTextField } from "../../../ui";

type EditorMode = "NUMERO" | "ESQUINA";

const isOnlyDigits = (value: string) => /^\d+$/.test(value);

export type NumeroEsquinaFreeEditorProps = {
  value: string | null;
  onChange: (newValue: string | null) => void;
  onModeChange?: (mode: EditorMode) => void;
  label?: string;
  error?: boolean;
  helperText?: string;
  initialMode?: EditorMode;
  disabled?: boolean;
};

/**
 * Editor liviano de número / esquina sin catálogo ni fetch de calles.
 * Usado en Actuaciones CRUD; la validación fina queda en Nomenclatura/normalizador.
 */
export function NumeroEsquinaFreeEditor({
  value,
  onChange,
  onModeChange,
  label = "Número o referencia",
  error = false,
  helperText,
  initialMode: initialModeProp,
  disabled,
}: NumeroEsquinaFreeEditorProps) {
  const initialMode: EditorMode = useMemo(() => {
    if (initialModeProp) return initialModeProp;
    if (!value) return "NUMERO";
    return isOnlyDigits(value) ? "NUMERO" : "ESQUINA";
  }, [value, initialModeProp]);

  const [mode, setMode] = useState<EditorMode>(initialMode);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  const onModeChangeRef = useRef(onModeChange);
  onModeChangeRef.current = onModeChange;
  useEffect(() => {
    onModeChangeRef.current?.(mode);
  }, [mode]);

  const handleModeChange = (_: MouseEvent<HTMLElement>, newMode: EditorMode | null) => {
    if (!newMode) return;
    setMode(newMode);
    onModeChange?.(newMode);
    if (!value) return;
    if (newMode === "NUMERO" && !isOnlyDigits(value)) {
      onChange(null);
    }
    if (newMode === "ESQUINA" && isOnlyDigits(value)) {
      onChange(null);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, width: "100%" }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={mode}
        onChange={handleModeChange}
        disabled={disabled}
        aria-label="modo numero esquina"
        sx={{
          alignSelf: "flex-start",
          "& .MuiToggleButton-root": {
            textTransform: "none",
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "0.8125rem",
            color: "rgba(255,255,255,0.75)",
            borderColor: "rgba(255,255,255,0.28)",
            px: 1.5,
          },
          "& .Mui-selected": {
            bgcolor: "rgba(255,255,255,0.12) !important",
            color: "rgba(255,255,255,0.95) !important",
          },
        }}
      >
        <ToggleButton value="NUMERO">Número</ToggleButton>
        <ToggleButton value="ESQUINA">Esquina</ToggleButton>
      </ToggleButtonGroup>

      {mode === "NUMERO" ? (
        <AppTextField
          appearance="glass"
          label={label}
          value={value ?? ""}
          disabled={disabled}
          error={error}
          helperText={helperText}
          fullWidth
          inputProps={{ inputMode: "numeric", pattern: "[0-9]*" }}
          onChange={(ev) => {
            const digitsOnly = ev.target.value.replace(/\D+/g, "");
            onChange(digitsOnly.length > 0 ? digitsOnly : null);
          }}
        />
      ) : (
        <AppTextField
          appearance="glass"
          label={`${label} (esquina)`}
          value={value ?? ""}
          disabled={disabled}
          error={error}
          helperText={helperText}
          fullWidth
          onChange={(ev) => {
            const next = ev.target.value;
            onChange(next.trim() ? next : null);
          }}
        />
      )}
    </Box>
  );
}
