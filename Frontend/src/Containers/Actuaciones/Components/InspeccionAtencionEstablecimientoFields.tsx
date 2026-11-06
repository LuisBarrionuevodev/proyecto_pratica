import { Box, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";
import {
  CARACTER_PERSONA_ATENDIO_LABELS,
  CARACTER_PERSONA_ATENDIO_VALORES,
  type CaracterPersonaAtendio,
} from "../utils/inspeccionAtencion";

export type InspeccionAtencionEstablecimientoFieldsProps = {
  caracter: CaracterPersonaAtendio | null;
  contrato: boolean | null;
  onCaracterChange: (value: CaracterPersonaAtendio | null) => void;
  onContratoChange: (value: boolean | null) => void;
  disabled?: boolean;
  hideHeading?: boolean;
  errors?: {
    caracter?: string;
    contrato?: string;
  };
};

const toggleSx = {
  color: GLASS_COLORS.textSecondary,
  borderColor: GLASS_COLORS.borderMedium,
  fontSize: "0.75rem",
  fontWeight: 500,
  letterSpacing: 0.2,
  textTransform: "none" as const,
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

const groupSx = {
  flexWrap: "wrap" as const,
  "& .MuiToggleButtonGroup-grouped": { height: 32 },
};

/**
 * Bloque editable «Atención en el establecimiento» (carácter + contrato de residuos).
 */
export function InspeccionAtencionEstablecimientoFields({
  caracter,
  contrato,
  onCaracterChange,
  onContratoChange,
  disabled = false,
  hideHeading = false,
  errors,
}: InspeccionAtencionEstablecimientoFieldsProps) {
  const caracterUi = caracter ?? "";
  const contratoUi = contrato === true ? "si" : contrato === false ? "no" : "";

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, width: "100%" }}>
      {hideHeading ? null : (
      <Typography
        variant="caption"
        sx={{
          color: GLASS_COLORS.textMuted,
          fontWeight: 600,
          letterSpacing: 0.4,
          textTransform: "uppercase",
          fontSize: "0.7rem",
        }}
      >
        Atención en el establecimiento
      </Typography>
      )}

      <Box>
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mb: 0.75 }}>
          Carácter de quien atendió
        </Typography>
        <ToggleButtonGroup
          exclusive
          size="small"
          disabled={disabled}
          value={caracterUi}
          onChange={(_, value: string | null) => {
            if (value == null) return;
            onCaracterChange(value === "" ? null : (value as CaracterPersonaAtendio));
          }}
          sx={groupSx}
        >
          <ToggleButton value="" sx={toggleSx} aria-label="Sin indicar">
            —
          </ToggleButton>
          {CARACTER_PERSONA_ATENDIO_VALORES.map((opt) => (
            <ToggleButton key={opt} value={opt} sx={toggleSx} aria-label={CARACTER_PERSONA_ATENDIO_LABELS[opt]}>
              {CARACTER_PERSONA_ATENDIO_LABELS[opt]}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        {errors?.caracter ? (
          <Typography variant="caption" color="error" sx={{ mt: 0.5, display: "block" }}>
            {errors.caracter}
          </Typography>
        ) : null}
      </Box>

      <Box>
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, mb: 0.75 }}>
          ¿Posee contrato de retiro de residuos sólidos urbanos?
        </Typography>
        <ToggleButtonGroup
          exclusive
          size="small"
          disabled={disabled}
          value={contratoUi}
          onChange={(_, value: string | null) => {
            if (value == null) return;
            if (value === "") onContratoChange(null);
            else onContratoChange(value === "si");
          }}
          sx={groupSx}
        >
          <ToggleButton value="" sx={toggleSx} aria-label="Sin indicar">
            —
          </ToggleButton>
          <ToggleButton value="si" sx={toggleSx} aria-label="Sí">
            Sí
          </ToggleButton>
          <ToggleButton value="no" sx={toggleSx} aria-label="No">
            No
          </ToggleButton>
        </ToggleButtonGroup>
        {errors?.contrato ? (
          <Typography variant="caption" color="error" sx={{ mt: 0.5, display: "block" }}>
            {errors.contrato}
          </Typography>
        ) : null}
      </Box>
    </Box>
  );
}
