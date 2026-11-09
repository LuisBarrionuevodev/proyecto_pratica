import { Box, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";

export type InspeccionActaSegmentedOption = {
  value: string;
  label: string;
  ariaLabel?: string;
  minWidth?: number;
};

export type InspeccionActaSegmentedRowProps = {
  label: string;
  required?: boolean;
  value: string;
  options: InspeccionActaSegmentedOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  readOnly?: boolean;
  error?: string;
  /** Si true, volver a pulsar la opción activa la limpia (mismo comportamiento que ToggleButtonGroup exclusive). */
  allowDeselect?: boolean;
};

export const inspeccionActaToggleSx = {
  color: GLASS_COLORS.textSecondary,
  borderColor: GLASS_COLORS.borderMedium,
  fontSize: "0.75rem",
  fontWeight: 500,
  letterSpacing: 0.2,
  px: 1.25,
  py: 0.5,
  minWidth: 52,
  whiteSpace: "nowrap",
  "&:hover": { backgroundColor: GLASS_COLORS.hoverBg },
  "&.Mui-selected": {
    color: GLASS_COLORS.textPrimary,
    backgroundColor: `var(${V.actionTabPrimarySelected})`,
    borderColor: GLASS_COLORS.borderActive,
  },
  "&.Mui-selected:hover": {
    backgroundColor: `var(${V.actionTabPrimarySelectedHover})`,
  },
  "&.Mui-disabled": {
    color: GLASS_COLORS.textMuted,
    opacity: 0.55,
    borderColor: GLASS_COLORS.borderMedium,
  },
} as const;

/**
 * Fila etiqueta izquierda + botones a la derecha (paridad con «Tiene habilitación»).
 */
export function InspeccionActaSegmentedRow({
  label,
  required = false,
  value,
  options,
  onChange,
  disabled = false,
  readOnly = false,
  error,
  allowDeselect = false,
}: InspeccionActaSegmentedRowProps) {
  const interactionDisabled = disabled || readOnly;
  const toggleSx = {
    ...inspeccionActaToggleSx,
    "&.Mui-disabled": {
      ...inspeccionActaToggleSx["&.Mui-disabled"],
      opacity: readOnly ? 1 : 0.55,
    },
  } as const;

  return (
    <Box sx={{ width: "100%" }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          width: "100%",
          flexWrap: { xs: "wrap", sm: "nowrap" },
        }}
      >
        <Typography
          sx={{
            color: GLASS_COLORS.textPrimary,
            fontSize: "0.9rem",
            fontWeight: 400,
            flex: { xs: "1 1 100%", sm: "1 1 auto" },
            minWidth: { sm: 150 },
            pr: { sm: 1 },
          }}
        >
          {label}
          {required ? " *" : ""}
        </Typography>
        <ToggleButtonGroup
          exclusive
          size="small"
          disabled={interactionDisabled}
          value={value}
          onChange={(_, next: string | null) => {
            if (interactionDisabled) return;
            if (next == null) {
              if (!allowDeselect) return;
              onChange("");
              return;
            }
            onChange(next);
          }}
          sx={{
            flexShrink: 0,
            flex: { xs: "1 1 100%", sm: "0 1 auto" },
            justifyContent: { xs: "flex-start", sm: "flex-end" },
            flexWrap: "wrap",
            "& .MuiToggleButtonGroup-grouped": { height: 32 },
          }}
        >
          {options.map((opt) => (
            <ToggleButton
              key={opt.value}
              value={opt.value}
              aria-label={opt.ariaLabel ?? opt.label}
              sx={{ ...toggleSx, minWidth: opt.minWidth ?? toggleSx.minWidth }}
            >
              {opt.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>
      {error ? (
        <Typography variant="caption" color="error" sx={{ mt: 0.5, display: "block" }}>
          {error}
        </Typography>
      ) : null}
    </Box>
  );
}
