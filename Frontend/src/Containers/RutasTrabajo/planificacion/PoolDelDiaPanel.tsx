import { Box, Chip, Stack, Typography } from "@mui/material";
import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import {
  planificacionFixedSectionSx,
  planificacionPanelColumnSx,
  planificacionPanelTitleSx,
  planificacionPoolListViewportSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import {
  distritoNombrePendiente,
  etiquetaTipoCorta,
  lineaPrincipalPendiente,
  prioridadCategoriaRow,
  rubroLineaPendiente,
} from "./utils/iniciadorDisplay";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PoolDelDiaPanelProps = {
  items: IRutaIniciadorPendienteRow[];
  onQuitar: (id: number) => void;
  onContinuarAsignacion: () => void;
};

/**
 * Pool del día: header fijo, lista con scroll propio, acción fija abajo.
 */
export function PoolDelDiaPanel({ items, onQuitar, onContinuarAsignacion }: PoolDelDiaPanelProps) {
  return (
    <Stack
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        ...planificacionPanelColumnSx,
      }}
      spacing={1}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="baseline"
        sx={planificacionFixedSectionSx}
        gap={1}
      >
        <Typography sx={planificacionPanelTitleSx}>Pool del día</Typography>
        <Typography
          sx={{
            fontFamily: tactic,
            fontSize: "0.75rem",
            fontWeight: 600,
            color: GLASS_COLORS.textSecondary,
            flexShrink: 0,
          }}
        >
          {items.length}
        </Typography>
      </Stack>

      <Box sx={{ ...planificacionPoolListViewportSx, ...rutasInstitutionalScrollSx }}>
        {items.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
            Sin ítems.
          </Typography>
        ) : (
          <Stack spacing={0.75}>
            {items.map((row) => {
              const distritoTxt = distritoNombrePendiente(row);
              return (
                <Stack
                  key={row.id}
                  spacing={0.5}
                  sx={{
                    py: 0.75,
                    borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
                    "&:last-of-type": { borderBottom: "none", pb: 0 },
                  }}
                >
                  <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1}>
                    <Stack spacing={0.35} sx={{ minWidth: 0, flex: 1 }}>
                      <Typography
                        sx={{
                          fontFamily: tactic,
                          fontSize: "0.78rem",
                          fontWeight: 600,
                          color: GLASS_COLORS.textPrimary,
                          lineHeight: 1.35,
                        }}
                      >
                        {lineaPrincipalPendiente(row)}
                      </Typography>
                      <Typography
                        sx={{
                          fontFamily: tactic,
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          lineHeight: 1.3,
                          color: GLASS_COLORS.textPrimary,
                          wordBreak: "break-word",
                        }}
                      >
                        {rubroLineaPendiente(row)}
                      </Typography>
                      <Typography
                        sx={{
                          fontFamily: tactic,
                          fontSize: "0.68rem",
                          fontWeight: 500,
                          lineHeight: 1.25,
                          color:
                            distritoTxt !== "—"
                              ? GLASS_COLORS.textSecondary
                              : "rgba(255,255,255,0.28)",
                          wordBreak: "break-word",
                        }}
                      >
                        {distritoTxt}
                      </Typography>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        <Chip
                          size="small"
                          label={etiquetaTipoCorta(row)}
                          variant="outlined"
                          sx={{
                            height: 22,
                            fontFamily: tactic,
                            fontSize: "0.62rem",
                            borderColor: GLASS_COLORS.borderMedium,
                            color: GLASS_COLORS.textSecondary,
                          }}
                        />
                        <Chip
                          size="small"
                          label={prioridadCategoriaRow(row)}
                          variant="outlined"
                          sx={{
                            height: 22,
                            fontFamily: tactic,
                            fontSize: "0.62rem",
                            fontWeight: 700,
                            borderColor: GLASS_COLORS.borderLight,
                            color: GLASS_COLORS.textSecondary,
                          }}
                        />
                      </Stack>
                    </Stack>
                    <AppButton dsVariant="ghost" dsSize="sm" onClick={() => onQuitar(row.id)} sx={{ flexShrink: 0 }}>
                      Quitar
                    </AppButton>
                  </Stack>
                </Stack>
              );
            })}
          </Stack>
        )}
      </Box>

      <Box sx={{ ...planificacionFixedSectionSx, pt: 1 }}>
        <AppButton dsVariant="primary" fullWidth onClick={onContinuarAsignacion} disabled={items.length === 0}>
          Continuar a asignación
        </AppButton>
      </Box>
    </Stack>
  );
}
