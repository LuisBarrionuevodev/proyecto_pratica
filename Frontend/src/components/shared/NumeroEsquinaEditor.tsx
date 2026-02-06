import { Autocomplete, Box, TextField, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useEffect, useMemo, useState, type MouseEvent } from "react";

type EditorMode = "NUMERO" | "ESQUINA";

const hasLetters = (value: string) => /[a-zA-ZáéíóúñÁÉÍÓÚÑ]/.test(value);
const isOnlyDigits = (value: string) => /^\d+$/.test(value);

interface NumeroEsquinaEditorProps {
  value: string | null;
  onChange: (newValue: string | null) => void;
  calles: string[];
  label?: string;
  error?: boolean;
  helperText?: string;
  allowFreeSolo?: boolean;
  onModeChange?: (mode: "NUMERO" | "ESQUINA") => void;
  initialMode?: "NUMERO" | "ESQUINA";
}

const NumeroEsquinaEditor = ({
  value,
  onChange,
  calles,
  label = "Número",
  error = false,
  helperText = "",
  allowFreeSolo = false,
  onModeChange,
  initialMode: initialModeProp,
}: NumeroEsquinaEditorProps) => {
  const initialMode: EditorMode = useMemo(() => {
    if (initialModeProp) return initialModeProp;
    if (!value) return "NUMERO";
    return hasLetters(value) ? "ESQUINA" : "NUMERO";
  }, [value, initialModeProp]);

  const [mode, setMode] = useState<EditorMode>(initialMode);
  const [inputValue, setInputValue] = useState(value ?? "");

  useEffect(() => {
    setMode(initialMode);
    setInputValue(value ?? "");
  }, [initialMode, value]);

  useEffect(() => {
    onModeChange?.(mode);
  }, [mode, onModeChange]);

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
    <Box sx={{ display: "flex", gap: 1, alignItems: "center", width: "100%" }}>
      <ToggleButtonGroup
        size="small"
        exclusive
        value={mode}
        onChange={handleModeChange}
        aria-label="modo numero esquina"
      >
        <ToggleButton value="NUMERO">Número</ToggleButton>
        <ToggleButton value="ESQUINA">Esquina</ToggleButton>
      </ToggleButtonGroup>

      {mode === "NUMERO" ? (
        <TextField
          label={label}
          size="small"
          value={value ?? ""}
          error={error}
          helperText={helperText}
          inputProps={{ inputMode: "numeric", pattern: "[0-9]*" }}
          onChange={(event) => {
            const digitsOnly = event.target.value.replace(/\D+/g, "");
            onChange(digitsOnly.length > 0 ? digitsOnly : null);
          }}
          sx={{ flex: 1 }}
        />
      ) : (
        <Autocomplete
          size="small"
          freeSolo={allowFreeSolo}
          options={calles}
          openOnFocus
          autoHighlight
          value={calles.includes(value ?? "") ? value : null}
          inputValue={inputValue}
          onInputChange={(_, newInputValue, reason) => {
            setInputValue(newInputValue);
            if (reason === "clear") {
              onChange(null);
              return;
            }
            if (reason === "input") {
              onChange(newInputValue.length > 0 ? newInputValue : null);
            }
          }}
          onChange={(_, newValue) => {
            const next = typeof newValue === "string" ? newValue : newValue ?? "";
            onChange(next.length > 0 ? next : null);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label={`${label} (esquina)`}
              error={error}
              helperText={helperText}
            />
          )}
          sx={{ flex: 1 }}
        />
      )}
    </Box>
  );
};

export default NumeroEsquinaEditor;
