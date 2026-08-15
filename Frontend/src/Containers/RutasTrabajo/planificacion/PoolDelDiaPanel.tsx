import { Box, Chip, CircularProgress, Stack, Tooltip, Typography } from "@mui/material";
import type { IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import {
  planificacionFixedSectionSx,
  planificacionPanelColumnSx,
  planificacionPanelFooterSx,
  planificacionPanelTitleSx,
  planificacionPoolListViewportSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import { poolDiaOrigenLabel } from "../utils/poolDiaDisplay";
import { puedeSacarDelPoolPanel } from "../../../utils/operRutaPoolAcciones";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PoolDelDiaPanelProps = {
  items: IRutaPoolDiaRow[];
  loading?: boolean;
  onQuitar: (poolId: number) => void | Promise<void>;
  onContinuarAsignacion?: () => void;
  /** Oculta pie «Continuar a asignación» (vista Asignación). */
  compact?: boolean;
};

function estadoPoolLabel(estado: string | null | undefined): string {
  const key = (estado ?? "").trim().toUpperCase();
  if (key === "EN_POOL") return "En pool";
  if (key === "ASIGNADO_A_RUTA") return "Asignado";
  return estado?.trim() || "—";
}

/**
 * Pool del día desde backend (`GET /ruta-pool-dia`): header fijo, lista con scroll, acción abajo.
 */
export function PoolDelDiaPanel({
  items,
  loading = false,
  onQuitar,
  onContinuarAsignacion,
  compact = false,
}: PoolDelDiaPanelProps) {
  return (
    <Stack
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        ...planificacionPanelColumnSx,
        gap: 1,
      }}
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

      <Box
        className="planificacion-list-body"
        data-testid="pool-del-dia-list"
        sx={{ ...planificacionPoolListViewportSx, ...rutasInstitutionalScrollSx }}
      >
        {loading ? (
          <Stack direction="row" alignItems="center" spacing={1} sx={{ py: 1 }}>
            <CircularProgress size={18} />
            <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted }}>
              Cargando pool…
            </Typography>
          </Stack>
        ) : items.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
            Sin ítems en pool.
          </Typography>
        ) : (
          <Stack spacing={0.75} sx={{ pb: 0.5 }}>
            {items.map((row) => {
              const origenLabel = poolDiaOrigenLabel(row.origen_tipo);
              const puedeSacar = puedeSacarDelPoolPanel(row);
              const enGrupo = row.ruta_item_id != null;
              return (
                <Stack
                  key={row.pool_id}
                  spacing={0.5}
                  data-testid={`pool-del-dia-row-${row.pool_id}`}
                  sx={{
                    py: 0.75,
                    borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
                    "&:last-of-type": { borderBottom: "none" },
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
                          wordBreak: "break-word",
                        }}
                      >
                        {row.domicilio_texto?.trim() || "—"}
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
                        {row.rubro_nombre?.trim() || "—"}
                      </Typography>
                      <Typography
                        sx={{
                          fontFamily: tactic,
                          fontSize: "0.68rem",
                          fontWeight: 500,
                          lineHeight: 1.25,
                          color: GLASS_COLORS.textSecondary,
                        }}
                      >
                        {row.fecha ?? "—"} · {estadoPoolLabel(row.estado)}
                      </Typography>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        <Chip
                          size="small"
                          label={origenLabel}
                          variant="outlined"
                          sx={{
                            height: 22,
                            fontFamily: tactic,
                            fontSize: "0.62rem",
                            borderColor: GLASS_COLORS.borderMedium,
                            color: GLASS_COLORS.textSecondary,
                          }}
                        />
                      </Stack>
                    </Stack>
                    {puedeSacar ? (
                      <AppButton
                        dsVariant="ghost"
                        dsSize="sm"
                        onClick={() => void onQuitar(row.pool_id)}
                        sx={{ flexShrink: 0 }}
                        data-testid={`pool-sacar-${row.pool_id}`}
                      >
                        Sacar del pool
                      </AppButton>
                    ) : enGrupo ? (
                      <Tooltip title="Primero eliminá el ítem del grupo. Luego podrás sacarlo del pool.">
                        <span>
                          <AppButton dsVariant="ghost" dsSize="sm" disabled sx={{ flexShrink: 0 }}>
                            Sacar del pool
                          </AppButton>
                        </span>
                      </Tooltip>
                    ) : null}
                  </Stack>
                </Stack>
              );
            })}
          </Stack>
        )}
      </Box>

      {!compact && onContinuarAsignacion ? (
        <Box className="planificacion-panel-footer" sx={{ ...planificacionPanelFooterSx, pt: 1 }}>
          <AppButton dsVariant="primary" fullWidth onClick={onContinuarAsignacion} disabled={items.length === 0}>
            Continuar a asignación
          </AppButton>
        </Box>
      ) : null}
    </Stack>
  );
}
