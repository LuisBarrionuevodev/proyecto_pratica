import { Box, CircularProgress, Stack, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import { rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";

const tactic = '"Tactic Sans", sans-serif' as const;

export type UrgentesPanelProps = {
  rows: IRutaIniciadorPendienteRow[];
  loading: boolean;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
  meta: { total: number; page: number; perPage: number };
  onPageChange: (page: number) => void;
};

/**
 * Bandeja M3: prioridad alta global (misma regla que backend: tipo ≠ RELEVAMIENTO, prioridad ≥ 3, planificables).
 * Scroll interno y paginación liviana; deduplicación con pool en el controller.
 */
export function UrgentesPanel({ rows, loading, onAgregar, meta, onPageChange }: UrgentesPanelProps) {
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.perPage) || 1);
  const emptyCopy =
    meta.total === 0
      ? "No hay iniciadores elegibles como urgentes en esta ruta (prioridad alta, no relevamiento, pendientes de planificar). Si acabas de migrar prioridades, revisá que existan filas con prioridad ≥ 3."
      : "Nada que mostrar aquí: puede que los ítems de esta página estén ya en el pool del día, o probá otra página.";

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
        <Typography
          sx={{
            fontFamily: tactic,
            fontWeight: 700,
            fontSize: "0.95rem",
            color: GLASS_COLORS.textPrimary,
            letterSpacing: "0.02em",
          }}
        >
          Urgentes para hoy
        </Typography>
        <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45, mt: 0.25 }}>
          Globales (no dependen del distrito). Incluye prioridad alta real (p. ej. denuncia, reinspección notificación,
          derivados de oficio); nunca relevamiento. Pueden coincidir con la izquierda; al pasar al pool desaparecen de
          ambas columnas.
        </Typography>
      </Box>

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.25 }}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={26} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.82rem", color: GLASS_COLORS.textSecondary, lineHeight: 1.5 }}>
            {emptyCopy}
          </Typography>
        ) : (
          <Stack spacing={0.75}>
            {rows.map((row) => (
              <PlanificacionIniciadorCompactCard
                key={row.id}
                row={row}
                agregarLabel="A ruta"
                agregarVariant="secondary"
                onAgregar={() => onAgregar(row)}
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
        <Typography sx={{ fontFamily: tactic, fontSize: "0.7rem", color: GLASS_COLORS.textMuted }}>
          {meta.total} total · {meta.page}/{totalPages}
        </Typography>
        <Stack direction="row" spacing={0.5}>
          <AppButton dsVariant="ghost" dsSize="sm" disabled={meta.page <= 1 || loading} onClick={() => onPageChange(meta.page - 1)}>
            Ant.
          </AppButton>
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            disabled={meta.page >= totalPages || loading}
            onClick={() => onPageChange(meta.page + 1)}
          >
            Sig.
          </AppButton>
        </Stack>
      </Stack>
    </Stack>
  );
}
