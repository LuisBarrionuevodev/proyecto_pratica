import { Box, CircularProgress, Stack, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import {
  planificacionPanelFooterMetaSx,
  planificacionPanelTitleSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";

const tactic = '"Tactic Sans", sans-serif' as const;

export type UrgentesPanelProps = {
  rows: IRutaIniciadorPendienteRow[];
  loading: boolean;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
  meta: { total: number; page: number; perPage: number };
  onPageChange: (page: number) => void;
  /** Mismo flujo que pendientes del contexto: mapa interno + distrito si hace falta. */
  onVerEnMapa?: (row: IRutaIniciadorPendienteRow) => void;
};

/**
 * Bandeja M3: prioridad alta global (misma regla que backend: tipo ≠ RELEVAMIENTO, prioridad ≥ 3, planificables).
 * Scroll interno y paginación liviana; deduplicación con pool en el controller.
 */
export function UrgentesPanel({ rows, loading, onAgregar, meta, onPageChange, onVerEnMapa }: UrgentesPanelProps) {
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.perPage) || 1);
  const emptyCopy = meta.total === 0 ? "Sin urgentes." : "Sin ítems en esta página.";

  return (
    <Stack
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        flex: 1,
        minHeight: 0,
        maxHeight: "min(38vh, 360px)",
        display: "flex",
        overflow: "hidden",
      }}
      spacing={1}
    >
      <Box sx={{ flexShrink: 0 }}>
        <Typography sx={planificacionPanelTitleSx}>Urgentes</Typography>
      </Box>

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.5, ...rutasInstitutionalScrollSx }}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={26} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
            {emptyCopy}
          </Typography>
        ) : (
          <Stack spacing={0.75}>
            {rows.map((row) => (
              <PlanificacionIniciadorCompactCard
                key={row.id}
                row={row}
                agregarLabel="Agregar"
                agregarVariant="primary"
                onAgregar={() => onAgregar(row)}
                onVerEnMapa={onVerEnMapa}
              />
            ))}
          </Stack>
        )}
      </Box>

      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        flexWrap="wrap"
        gap={0.75}
        sx={{ flexShrink: 0, pt: 0.75, borderTop: `1px solid ${GLASS_COLORS.borderLight}` }}
      >
        <Typography sx={planificacionPanelFooterMetaSx}>
          {meta.total} · {meta.page}/{totalPages}
        </Typography>
        <Stack direction="row" spacing={0.5}>
          <AppButton dsVariant="ghost" dsSize="sm" disabled={meta.page <= 1 || loading} onClick={() => onPageChange(meta.page - 1)}>
            Anterior
          </AppButton>
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            disabled={meta.page >= totalPages || loading}
            onClick={() => onPageChange(meta.page + 1)}
          >
            Siguiente
          </AppButton>
        </Stack>
      </Stack>
    </Stack>
  );
}
