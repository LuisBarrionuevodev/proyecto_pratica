import { Box, Paper, Stack, Typography } from "@mui/material";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { RutaContextoLine } from "../Components/RutaContextoLine";
import { RutasOperativaChip } from "../Components/RutasOperativaChip";
import { planificacionPanelTitleSx, rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";
import type { PlanificacionPoolStripItem } from "./utils/buildPlanificacionPoolStripItems";

const tactic = '"Tactic Sans", sans-serif' as const;

const cardSx = {
  flex: "0 0 auto",
  minWidth: 220,
  maxWidth: 320,
  p: 1,
  borderRadius: "10px",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  bgcolor: "rgba(255,255,255,0.04)",
} as const;

export type PlanificacionPoolCardsStripProps = {
  ruta: IRutaTrabajo;
  items: PlanificacionPoolStripItem[];
  enPool: number;
  enGrupo: number;
  loading?: boolean;
  onQuitarDelPool?: (poolId: number) => void | Promise<void>;
};

/**
 * Strip horizontal compacto: pool armado de la ruta (OPER-RUTA.7C.3).
 */
export function PlanificacionPoolCardsStrip({
  ruta,
  items,
  enPool,
  enGrupo,
  loading = false,
  onQuitarDelPool,
}: PlanificacionPoolCardsStripProps) {
  return (
    <Paper
      elevation={0}
      data-testid="planificacion-pool-strip"
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        px: 1.5,
        py: 1,
        flexShrink: 0,
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="baseline"
        spacing={1}
        flexWrap="wrap"
        useFlexGap
        sx={{ mb: items.length > 0 ? 0.75 : 0 }}
      >
        <Typography sx={{ ...planificacionPanelTitleSx, fontSize: "0.875rem" }}>Pool de la ruta</Typography>
        <RutaContextoLine ruta={ruta} suffix={`En pool: ${enPool}`} variant="compact" />
      </Stack>

      {loading ? (
        <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted }}>
          Cargando pool…
        </Typography>
      ) : items.length === 0 ? (
        <Typography
          data-testid="planificacion-pool-strip-empty"
          sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}
        >
          Todavía no agregaste pendientes al pool.
        </Typography>
      ) : (
        <Box
          data-testid="planificacion-pool-strip-cards"
          sx={{
            display: "flex",
            flexDirection: "row",
            gap: 0.75,
            overflowX: "auto",
            overflowY: "hidden",
            pb: 0.25,
            scrollSnapType: "x proximity",
            "&::-webkit-scrollbar": { height: 6 },
            "&::-webkit-scrollbar-thumb": {
              backgroundColor: "rgba(255,255,255,0.12)",
              borderRadius: 3,
            },
          }}
        >
          {items.map((item) => (
            <Stack
              key={item.key}
              spacing={0.5}
              data-testid={`planificacion-pool-card-${item.iniciadorId}`}
              sx={{ ...cardSx, scrollSnapAlign: "start" }}
            >
              <Stack direction="row" spacing={0.7} flexWrap="wrap" useFlexGap alignItems="center">
                <RutasOperativaChip label={item.tipoLabel} />
                <RutasOperativaChip
                  label={item.estadoLabel}
                  color={item.estado === "grupo" ? "primary" : "default"}
                />
              </Stack>
              <Typography
                sx={{
                  fontFamily: tactic,
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  color: GLASS_COLORS.textPrimary,
                  lineHeight: 1.3,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {item.titulo}
              </Typography>
              {item.detalle ? (
                <Typography
                  sx={{
                    fontFamily: tactic,
                    fontSize: "0.68rem",
                    color: GLASS_COLORS.textMuted,
                    lineHeight: 1.3,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.detalle}
                </Typography>
              ) : null}
              <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={0.5}>
                <Typography sx={{ fontFamily: tactic, fontSize: "0.68rem", color: GLASS_COLORS.textSecondary }}>
                  {item.distritoLabel}
                  {item.grupoNombre ? ` · ${item.grupoNombre}` : ""}
                </Typography>
                {item.puedeQuitar && item.poolId != null && onQuitarDelPool ? (
                  <AppButton dsVariant="danger" dsSize="sm" onClick={() => void onQuitarDelPool(item.poolId!)}>
                    Quitar
                  </AppButton>
                ) : null}
              </Stack>
            </Stack>
          ))}
        </Box>
      )}
    </Paper>
  );
}
