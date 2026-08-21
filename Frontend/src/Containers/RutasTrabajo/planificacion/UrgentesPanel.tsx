import { Box, Chip, CircularProgress, Stack, Tooltip, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import {
  planificacionFixedSectionSx,
  planificacionPanelColumnSx,
  planificacionPanelFooterMetaSx,
  planificacionPanelFooterSx,
  planificacionPanelTitleSx,
  planificacionUrgentesListViewportSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import { planificacionSidebarListViewportSx } from "./planificacionMyMapsLayout";
import type { UrgentesFiltrosAplicados } from "./types/planificacion.types";
import { UrgentesFiltroPanel } from "./UrgentesFiltroPanel";

const tactic = '"Tactic Sans", sans-serif' as const;

export type UrgentesPanelProps = {
  /** `embedded`: dentro del sidebar 7C (sin paper ni filtros duplicados). */
  variant?: "standalone" | "embedded";
  rows: IRutaIniciadorPendienteRow[];
  loading: boolean;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
  meta: { total: number; page: number; perPage: number };
  onPageChange: (page: number) => void;
  /** Filas de la página M3 ya en pool (solo ese ítem se oculta, no toda la bandeja). */
  ocultosPorPoolEnPagina?: number;
  onVerEnMapa?: (row: IRutaIniciadorPendienteRow) => void;
  onFiltrar?: (filtros: UrgentesFiltrosAplicados) => void;
  onLimpiarFiltros?: () => void;
};

/**
 * Bandeja M3 global: independiente del distrito del mapa y de KPIs.
 */
export function UrgentesPanel({
  variant = "standalone",
  rows,
  loading,
  onAgregar,
  meta,
  onPageChange,
  ocultosPorPoolEnPagina = 0,
  onVerEnMapa,
  onFiltrar,
  onLimpiarFiltros,
}: UrgentesPanelProps) {
  const embedded = variant === "embedded";
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.perPage) || 1);
  const poolHidden = ocultosPorPoolEnPagina > 0;
  const emptyCopy =
    meta.total === 0
      ? "Sin urgentes."
      : poolHidden && rows.length === 0
        ? `Las ${ocultosPorPoolEnPagina} fila${ocultosPorPoolEnPagina === 1 ? "" : "s"} de esta página están en el pool del día. Use «Siguiente» o quite ítems del pool.`
        : "Sin ítems en esta página.";

  const listViewportSx = embedded
    ? { ...planificacionSidebarListViewportSx, ...rutasInstitutionalScrollSx }
    : { ...planificacionUrgentesListViewportSx, ...rutasInstitutionalScrollSx };

  const content = (
    <>
      {!embedded ? (
        <Box sx={planificacionFixedSectionSx}>
          <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap" useFlexGap>
            <Typography sx={planificacionPanelTitleSx}>Urgentes globales</Typography>
            <Tooltip title="Bandeja global: no cambia al seleccionar distrito en el mapa." arrow placement="top">
              <Chip
                label="Global"
                size="small"
                color="primary"
                variant="outlined"
                sx={{ height: 22, fontSize: "0.6875rem", fontWeight: 600, cursor: "help" }}
              />
            </Tooltip>
          </Stack>
        </Box>
      ) : null}

      {!embedded && onFiltrar && onLimpiarFiltros ? (
        <Box sx={planificacionFixedSectionSx}>
          <UrgentesFiltroPanel onFiltrar={onFiltrar} onLimpiar={onLimpiarFiltros} loading={loading} />
        </Box>
      ) : null}

      <Box className="planificacion-list-body" data-testid="planificacion-sidebar-flex-list" sx={listViewportSx}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={26} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
            {emptyCopy}
          </Typography>
        ) : (
          <Stack spacing={0.75} sx={{ pb: 0.5 }}>
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
        className="planificacion-pagination-footer"
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        flexWrap="wrap"
        gap={0.75}
        sx={{
          ...planificacionPanelFooterSx,
          pt: 0.75,
          borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
        }}
      >
        <Stack direction="column" spacing={0.25} sx={{ minWidth: 0, flex: 1 }}>
          <Typography sx={planificacionPanelFooterMetaSx}>
            {meta.total} total global · {meta.page}/{totalPages}
            {rows.length > 0 ? ` · visibles ${rows.length}` : ""}
          </Typography>
          {poolHidden ? (
            <Typography
              sx={{
                ...planificacionPanelFooterMetaSx,
                fontSize: "0.6875rem",
                color: GLASS_COLORS.textMuted,
                lineHeight: 1.35,
              }}
            >
              {ocultosPorPoolEnPagina} en pool del día (no listados aquí)
            </Typography>
          ) : null}
        </Stack>
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
    </>
  );

  if (embedded) {
    return (
      <Stack sx={{ ...planificacionPanelColumnSx, flex: 1, minHeight: 0, gap: 0.75 }}>
        {content}
      </Stack>
    );
  }

  return (
    <Stack
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        ...planificacionPanelColumnSx,
        gap: 0.75,
      }}
    >
      {content}
    </Stack>
  );
}
