import {
  Box,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import { PendientesContextoFiltroPanel } from "./PendientesContextoFiltroPanel";
import {
  planificacionPanelColumnSx,
  planificacionPanelFooterMetaSx,
  planificacionPanelFooterSx,
  planificacionPanelSubtitleSx,
  planificacionPanelTitleSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import { planificacionSidebarListViewportSx } from "./planificacionMyMapsLayout";
import type { PlanificacionFiltrosLista } from "./types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

/**
 * Alto máximo del viewport de la lista (solo este bloque hace scroll).
 * Calibrado para ~2 `PlanificacionIniciadorCompactCard` + `Stack.spacing` entre ítems.
 */
const PENDIENTES_LISTA_VIEWPORT_MAX = "min(17.5rem, 38vh)";

export type PendientesContextoPanelProps = {
  /** `embedded`: dentro del sidebar 7C (sin paper ni filtros duplicados). */
  variant?: "standalone" | "embedded";
  distritoActivoId: number | null;
  distritoNombre?: string | null;
  rows: IRutaIniciadorPendienteRow[];
  meta: { total: number; page: number; perPage: number };
  loading: boolean;
  onFiltrar?: (filtros: PlanificacionFiltrosLista) => void;
  onLimpiar?: () => void;
  onPageChange: (page: number) => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
  /** Centrar mapa y abrir card en el punto (requiere coords en el row). */
  onVerEnMapa?: (row: IRutaIniciadorPendienteRow) => void;
};

/**
 * Columna izquierda: sin distrito = empty state; con distrito = filtros locales + lista M4.
 */
export function PendientesContextoPanel({
  variant = "standalone",
  distritoActivoId,
  distritoNombre,
  rows,
  meta,
  loading,
  onFiltrar,
  onLimpiar,
  onPageChange,
  onAgregar,
  onVerEnMapa,
}: PendientesContextoPanelProps) {
  const embedded = variant === "embedded";
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.perPage) || 1);

  const listBody = (
    <>
        <Box
        className="planificacion-list-body"
        data-testid="planificacion-sidebar-flex-list"
        sx={
          embedded
            ? { ...planificacionSidebarListViewportSx, ...rutasInstitutionalScrollSx }
            : {
                maxHeight: PENDIENTES_LISTA_VIEWPORT_MAX,
                minHeight: 0,
                overflow: "auto",
                flexShrink: 0,
                pr: 0.5,
                ...rutasInstitutionalScrollSx,
              }
        }
      >
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={28} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
            {distritoActivoId == null
              ? "Elegí un distrito en el mapa."
              : "Sin candidatos con los filtros actuales."}
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
        gap={1}
        sx={{
          ...(embedded ? planificacionPanelFooterSx : { flexShrink: 0, pt: 0.5 }),
          borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
        }}
      >
        <Typography sx={planificacionPanelFooterMetaSx}>
          {meta.total} · {meta.page}/{totalPages}
        </Typography>
        <Stack direction="row" spacing={0.5}>
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            disabled={meta.page <= 1 || loading}
            onClick={() => onPageChange(meta.page - 1)}
          >
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
        {listBody}
      </Stack>
    );
  }

  if (distritoActivoId == null) {
    return (
      <Box
        sx={{
          ...rutasInstitutionalPanelPaperSx,
          height: "100%",
          minHeight: 320,
          maxHeight: "min(78vh, 820px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          p: 3,
          gap: 2,
        }}
      >
        <MapOutlinedIcon sx={{ fontSize: 40, color: GLASS_COLORS.primary, opacity: 0.85 }} aria-hidden />
        <Typography sx={{ ...planificacionPanelTitleSx, textAlign: "center" }}>Pendientes del contexto</Typography>
        <Typography
          sx={{
            fontFamily: tactic,
            color: GLASS_COLORS.textMuted,
            textAlign: "center",
            maxWidth: 240,
            lineHeight: 1.4,
            fontSize: "0.8125rem",
          }}
        >
          Seleccioná un distrito en el mapa.
        </Typography>
      </Box>
    );
  }

  return (
    <Stack
      sx={{
        ...rutasInstitutionalPanelPaperSx,
        height: "100%",
        minHeight: 360,
        maxHeight: "min(78vh, 820px)",
        overflow: "hidden",
      }}
      spacing={1.1}
    >
      <Box sx={{ flexShrink: 0 }}>
        <Typography sx={planificacionPanelTitleSx}>Pendientes del contexto</Typography>
        <Typography sx={{ ...planificacionPanelSubtitleSx, color: GLASS_COLORS.textPrimary, fontWeight: 600 }}>
          {distritoNombre ?? `Distrito ${distritoActivoId}`}
        </Typography>
      </Box>

      {onFiltrar && onLimpiar ? (
        <PendientesContextoFiltroPanel
          key={distritoActivoId}
          onFiltrar={onFiltrar}
          onLimpiar={onLimpiar}
          loading={loading}
        />
      ) : null}

      {listBody}
    </Stack>
  );
}
