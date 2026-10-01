import { Box, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";

import { AppTextField } from "../../../ui";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";
import { FONT_FAMILY_UI } from "../../../theme/typography";

type EditorMode = "NUMERO" | "ESQUINA";

const isOnlyDigits = (value: string) => /^\d+$/.test(value);

const numeroEsquinaToggleGroupSx = {
  "& .MuiToggleButton-root": {
    textTransform: "none" as const,
    fontFamily: FONT_FAMILY_UI,
    fontSize: "0.8125rem",
    color: GLASS_COLORS.textSecondary,
    borderColor: GLASS_COLORS.borderMedium,
    px: 1.5,
  },
  "& .Mui-selected": {
    bgcolor: `var(${V.actionSelected}) !important`,
    color: `${GLASS_COLORS.textPrimary} !important`,
  },
} as const;

export type NumeroEsquinaFreeEditorProps = {
  value: string | null;
  onChange: (newValue: string | null) => void;
  onModeChange?: (mode: EditorMode) => void;
  label?: string;
  /** Toggle e input en una línea; oculta el label del campo. */
  compact?: boolean;
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
  compact = false,
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

  const compactFieldSx = {
    flex: 1,
    minWidth: 0,
    "& .MuiFormHelperText-root": { mt: 0.25, mx: 0 },
  } as const;

  if (compact) {
    return (
      <Box
        data-testid="numero-esquina-compact"
        sx={{ display: "flex", flexDirection: "column", gap: 0.5, width: "100%" }}
      >
        <Box aria-hidden data-testid="numero-esquina-compact-label-spacer" sx={{ height: 20, flexShrink: 0 }} />
        <Box
          data-testid="numero-esquina-compact-row"
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            alignItems: { xs: "stretch", sm: "end" },
            gap: 0.5,
            width: "100%",
          }}
        >
          <ToggleButtonGroup
            size="small"
            exclusive
            value={mode}
            onChange={handleModeChange}
            disabled={disabled}
            aria-label="modo numero esquina"
            sx={{
              alignSelf: { xs: "flex-start", sm: "auto" },
              flexShrink: 0,
              ...numeroEsquinaToggleGroupSx,
            }}
          >
            <ToggleButton value="NUMERO">Número</ToggleButton>
            <ToggleButton value="ESQUINA">Esquina</ToggleButton>
          </ToggleButtonGroup>

          {mode === "NUMERO" ? (
            <AppTextField
              appearance="glass"
              value={value ?? ""}
              disabled={disabled}
              error={error}
              helperText={helperText}
              fullWidth
              sx={compactFieldSx}
              inputProps={{ inputMode: "numeric", pattern: "[0-9]*" }}
              onChange={(ev) => {
                const digitsOnly = ev.target.value.replace(/\D+/g, "");
                onChange(digitsOnly.length > 0 ? digitsOnly : null);
              }}
            />
          ) : (
            <AppTextField
              appearance="glass"
              value={value ?? ""}
              disabled={disabled}
              error={error}
              helperText={helperText}
              fullWidth
              sx={compactFieldSx}
              onChange={(ev) => {
                const next = ev.target.value;
                onChange(next.trim() ? next : null);
              }}
            />
          )}
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1,
        width: "100%",
      }}
    >
      <ToggleButtonGroup
        size="small"
        exclusive
        value={mode}
        onChange={handleModeChange}
        disabled={disabled}
        aria-label="modo numero esquina"
        sx={{
          alignSelf: "flex-start",
          ...numeroEsquinaToggleGroupSx,
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
