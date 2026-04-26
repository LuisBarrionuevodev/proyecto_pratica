import type { SxProps, Theme } from "@mui/material";
import { Alert, Box, ButtonBase, Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { rutasInstitutionalScrollSx } from "../../RutasTrabajo/styles/institutionalVisual";
import { validationRailRootSx } from "../styles/cargarRelevamientosStyles";

const TACTIC = '"Tactic Sans", sans-serif' as const;

export type ValidationRailEntry = {
  rowIndex: number;
  lines: string[];
};

type ValidationErrorsRailProps = {
  globalError: string | null;
  onDismissGlobal: () => void;
  entries: ValidationRailEntry[];
  /** Si es false, no se muestra el texto “sin errores” (p. ej. antes de iniciar batch). */
  showEmptyHint?: boolean;
  onGoToRow?: (rowIndex: number) => void;
  sx?: SxProps<Theme>;
};

/**
 * Panel lateral de validación: errores globales de API y detalle por fila.
 * Scroll propio; no forma parte del flujo vertical que empuja la grilla Glide.
 */
export function ValidationErrorsRail({
  globalError,
  onDismissGlobal,
  entries,
  showEmptyHint = true,
  onGoToRow,
  sx,
}: ValidationErrorsRailProps) {
  const hasRowErrors = entries.length > 0;
  const showEmpty = showEmptyHint && !globalError && !hasRowErrors;

  return (
    <Box sx={{ ...validationRailRootSx, ...rutasInstitutionalScrollSx, ...sx }}>
      <Typography
        sx={{
          fontFamily: TACTIC,
          fontWeight: 700,
          fontSize: "0.8125rem",
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          color: GLASS_COLORS.textPrimary,
          mb: 1,
        }}
      >
        Validación
      </Typography>

      {globalError ? (
        <Alert severity="error" onClose={onDismissGlobal} variant="outlined" sx={{ mb: 1.25, borderRadius: "10px", py: 0.5 }}>
          {globalError}
        </Alert>
      ) : null}

      {hasRowErrors ? (
        <>
          <Typography
            sx={{
              fontFamily: TACTIC,
              fontSize: "0.72rem",
              fontWeight: 600,
              color: GLASS_COLORS.textMuted,
              mb: 0.75,
            }}
          >
            Filas con error
          </Typography>
          <Stack spacing={0.75}>
            {entries.map(({ rowIndex, lines }) => (
              <ButtonBase
                key={rowIndex}
                disableRipple={!onGoToRow}
                onClick={onGoToRow ? () => onGoToRow(rowIndex) : undefined}
                sx={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  borderRadius: "10px",
                  p: 1,
                  bgcolor: "rgba(255,255,255,0.04)",
                  border: `1px solid ${GLASS_COLORS.borderLight}`,
                  transition: "background-color 0.15s ease, border-color 0.15s ease",
                  cursor: onGoToRow ? "pointer" : "default",
                  "&:hover": onGoToRow
                    ? {
                        bgcolor: "rgba(255,255,255,0.07)",
                        borderColor: GLASS_COLORS.borderMedium,
                      }
                    : undefined,
                }}
              >
                <Typography
                  sx={{
                    fontFamily: TACTIC,
                    fontWeight: 700,
                    fontSize: "0.78rem",
                    color: GLASS_COLORS.primary,
                    mb: 0.35,
                  }}
                >
                  Fila {rowIndex + 1}
                </Typography>
                {lines.map((line, i) => (
                  <Typography
                    key={i}
                    component="div"
                    sx={{
                      fontFamily: TACTIC,
                      fontSize: "0.72rem",
                      lineHeight: 1.45,
                      color: GLASS_COLORS.textSecondary,
                    }}
                  >
                    {line}
                  </Typography>
                ))}
              </ButtonBase>
            ))}
          </Stack>
        </>
      ) : null}

      {showEmpty ? (
        <Typography sx={{ fontFamily: TACTIC, fontSize: "0.72rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
          Sin errores de validación en filas cargadas.
        </Typography>
      ) : null}
    </Box>
  );
}
