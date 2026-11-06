import { Box, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppTextField } from "../../../ui";
import {
  CARACTER_PERSONA_ATENDIO_VALORES,
  type CaracterPersonaAtendio,
} from "../utils/inspeccionAtencion";
import { InspeccionActaSegmentedRow } from "./InspeccionActaSegmentedRow";

export type SolicitaCarnetAtencionUi = "" | "si" | "no";

export type InspeccionAtencionEstablecimientoFieldsProps = {
  caracter: CaracterPersonaAtendio | null;
  contrato: boolean | null;
  onCaracterChange: (value: CaracterPersonaAtendio | null) => void;
  onContratoChange: (value: boolean | null) => void;
  disabled?: boolean;
  readOnly?: boolean;
  hideHeading?: boolean;
  showCarnet?: boolean;
  carnet?: SolicitaCarnetAtencionUi;
  onCarnetChange?: (value: SolicitaCarnetAtencionUi) => void;
  telefonoCarnet?: string;
  onTelefonoCarnetChange?: (value: string) => void;
  carnetDisabled?: boolean;
  errors?: {
    caracter?: string;
    contrato?: string;
    carnet?: string;
    telefonoCarnet?: string;
  };
};

/**
 * Selectores de atención en el establecimiento (carácter, carnet opcional, contrato).
 * Mismo diseño que «Tiene habilitación»: visibles siempre; `disabled` los bloquea sin ocultarlos.
 */
export function InspeccionAtencionEstablecimientoFields({
  caracter,
  contrato,
  onCaracterChange,
  onContratoChange,
  disabled = false,
  readOnly = false,
  hideHeading = false,
  showCarnet = false,
  carnet = "",
  onCarnetChange,
  telefonoCarnet = "",
  onTelefonoCarnetChange,
  carnetDisabled = false,
  errors,
}: InspeccionAtencionEstablecimientoFieldsProps) {
  const caracterUi = caracter ?? "";
  const contratoUi = contrato === true ? "si" : contrato === false ? "no" : "";
  const dimmed = disabled && !readOnly;
  const carnetLocked = disabled || carnetDisabled;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 0.75,
        width: "100%",
        mt: 1.5,
        mb: 0.5,
        opacity: dimmed ? 0.72 : 1,
        transition: "opacity 0.15s ease",
      }}
    >
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

      <InspeccionActaSegmentedRow
        label="Carácter de quien atendió"
        value={caracterUi}
        disabled={disabled}
        readOnly={readOnly}
        error={errors?.caracter}
        onChange={(next) => {
          onCaracterChange(next === "" ? null : (next as CaracterPersonaAtendio));
        }}
        options={[
          { value: "", label: "—", ariaLabel: "Sin indicar" },
          ...CARACTER_PERSONA_ATENDIO_VALORES.map((opt) => ({
            value: opt,
            label: opt,
            ariaLabel: opt,
            minWidth: 88,
          })),
        ]}
      />

      {showCarnet ? (
        <>
          <InspeccionActaSegmentedRow
            label="¿El personal presente solicita carnet de manipulador de alimentos?"
            value={carnet}
            disabled={carnetLocked}
            readOnly={readOnly}
            error={errors?.carnet}
            onChange={(next) => {
              if (!onCarnetChange) return;
              onCarnetChange(next === "si" || next === "no" ? next : "");
            }}
            options={[
              { value: "", label: "—", ariaLabel: "Sin indicar" },
              { value: "si", label: "SÍ", ariaLabel: "Sí", minWidth: 44 },
              { value: "no", label: "NO", ariaLabel: "No", minWidth: 44 },
            ]}
          />
          {carnet === "si" || (readOnly && telefonoCarnet.trim()) ? (
            <AppTextField
              appearance="glass"
              label="Teléfono de contacto del personal solicitante"
              value={telefonoCarnet}
              onChange={(e) => onTelefonoCarnetChange?.(e.target.value)}
              fullWidth
              sx={{ mt: 0.5 }}
              disabled={carnetLocked || readOnly}
              inputProps={{ maxLength: 32, readOnly: readOnly || carnetLocked }}
              error={Boolean(errors?.telefonoCarnet)}
              helperText={errors?.telefonoCarnet || undefined}
            />
          ) : null}
        </>
      ) : null}

      <InspeccionActaSegmentedRow
        label="¿Posee contrato de retiro de residuos sólidos urbanos?"
        value={contratoUi}
        disabled={disabled}
        readOnly={readOnly}
        error={errors?.contrato}
        onChange={(next) => {
          if (next === "") onContratoChange(null);
          else onContratoChange(next === "si");
        }}
        options={[
          { value: "", label: "—", ariaLabel: "Sin indicar" },
          { value: "si", label: "SÍ", ariaLabel: "Sí", minWidth: 44 },
          { value: "no", label: "NO", ariaLabel: "No", minWidth: 44 },
        ]}
      />
    </Box>
  );
}
