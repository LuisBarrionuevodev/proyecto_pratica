import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import { planificacionTextFieldSx, rutasInstitutionalPanelPaperSx } from "../styles/institutionalVisual";
import type { PlanificacionFiltrosLista, PlanificacionOrdenM4 } from "./types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

const panelTitleSx = {
  fontFamily: tactic,
  fontWeight: 700,
  fontSize: "0.95rem",
  color: GLASS_COLORS.textPrimary,
  letterSpacing: "0.02em",
} as const;

const panelSubtitleSx = {
  fontFamily: tactic,
  fontSize: "0.75rem",
  color: GLASS_COLORS.textMuted,
} as const;

const TIPO_OPCIONES: { value: string; label: string }[] = [
  { value: "", label: "Todos (según card superior)" },
  { value: "DENUNCIA", label: "Denuncia" },
  { value: "RELEVAMIENTO", label: "Relevamiento" },
  { value: "REINSPECCION_NOTIFICACION", label: "Reinspección notificación" },
  { value: "REINSPECCION_OFICIO", label: "Reinspección oficio" },
  { value: "VERIFICAR_INFORMAR_OFICIO", label: "Verificar e informar (oficio)" },
  { value: "RATIFICACION_CLAUSURA_OFICIO", label: "Ratificación clausura" },
  { value: "RATIFICACION_DECOMISO_OFICIO", label: "Ratificación decomiso" },
];

const ORDEN_OPCIONES: { value: PlanificacionOrdenM4; label: string }[] = [
  { value: "prioridad", label: "Prioridad (mayor primero)" },
  { value: "prioridad_asc", label: "Prioridad (menor primero)" },
  { value: "fecha_asc", label: "Fecha origen (más antigua)" },
  { value: "fecha_desc", label: "Fecha origen (más reciente)" },
];

export type PendientesContextoPanelProps = {
  distritoActivoId: number | null;
  distritoNombre?: string | null;
  filtros: PlanificacionFiltrosLista;
  onFiltrosChange: (patch: Partial<PlanificacionFiltrosLista>) => void;
  rows: IRutaIniciadorPendienteRow[];
  meta: { total: number; page: number; perPage: number };
  loading: boolean;
  onApplyBusqueda: (q: string) => void;
  onPageChange: (page: number) => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
};

/**
 * Columna izquierda: sin distrito = empty state; con distrito = filtros locales + lista M4.
 */
export function PendientesContextoPanel({
  distritoActivoId,
  distritoNombre,
  filtros,
  onFiltrosChange,
  rows,
  meta,
  loading,
  onApplyBusqueda,
  onPageChange,
  onAgregar,
}: PendientesContextoPanelProps) {
  const [localQ, setLocalQ] = useState("");

  useEffect(() => {
    setLocalQ("");
  }, [distritoActivoId]);

  const totalPages = Math.max(1, Math.ceil(meta.total / meta.perPage) || 1);

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
        <MapOutlinedIcon sx={{ fontSize: 44, color: GLASS_COLORS.primary, opacity: 0.9 }} aria-hidden />
        <Typography sx={{ ...panelTitleSx, textAlign: "center" }}>Pendientes del contexto</Typography>
        <Typography
          sx={{
            fontFamily: tactic,
            color: GLASS_COLORS.textSecondary,
            textAlign: "center",
            maxWidth: 300,
            lineHeight: 1.55,
            fontSize: "0.875rem",
          }}
        >
          Elegí un distrito en el <strong style={{ color: GLASS_COLORS.textPrimary }}>mapa central</strong>. Los filtros
          de abajo se habilitan con el territorio; las <strong style={{ color: GLASS_COLORS.textPrimary }}>cards KPI</strong>{" "}
          siguen refinar el alcance.
        </Typography>
        <Typography sx={{ ...panelSubtitleSx, textAlign: "center", maxWidth: 280, fontSize: "0.72rem" }}>
          Listado contextual: no es el universo global del sistema.
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
        <Typography sx={panelTitleSx}>Pendientes del contexto</Typography>
        <Typography sx={panelSubtitleSx}>
          Distrito:{" "}
          <Box component="span" sx={{ color: GLASS_COLORS.textPrimary, fontWeight: 600 }}>
            {distritoNombre ?? `#${distritoActivoId}`}
          </Box>
        </Typography>
      </Box>

      <Stack spacing={1} sx={{ flexShrink: 0 }}>
        <FormControl size="small" fullWidth>
          <InputLabel id="planif-tipo-label" sx={{ fontFamily: tactic, color: GLASS_COLORS.textSecondary }}>
            Tipo de iniciador
          </InputLabel>
          <Select
            labelId="planif-tipo-label"
            label="Tipo de iniciador"
            value={filtros.tipo}
            onChange={(e) => onFiltrosChange({ tipo: e.target.value })}
            sx={{
              fontFamily: tactic,
              borderRadius: "10px",
              "& .MuiOutlinedInput-notchedOutline": { borderColor: GLASS_COLORS.borderLight },
            }}
          >
            {TIPO_OPCIONES.map((o) => (
              <MenuItem key={o.value || "all"} value={o.value} sx={{ fontFamily: tactic, fontSize: "0.85rem" }}>
                {o.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" fullWidth>
          <InputLabel id="planif-orden-label" sx={{ fontFamily: tactic, color: GLASS_COLORS.textSecondary }}>
            Ordenar por
          </InputLabel>
          <Select
            labelId="planif-orden-label"
            label="Ordenar por"
            value={filtros.orden}
            onChange={(e) => onFiltrosChange({ orden: e.target.value as PlanificacionOrdenM4 })}
            sx={{
              fontFamily: tactic,
              borderRadius: "10px",
              "& .MuiOutlinedInput-notchedOutline": { borderColor: GLASS_COLORS.borderLight },
            }}
          >
            {ORDEN_OPCIONES.map((o) => (
              <MenuItem key={o.value} value={o.value} sx={{ fontFamily: tactic, fontSize: "0.85rem" }}>
                {o.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Stack direction="row" spacing={1} alignItems="flex-start">
          <TextField
            size="small"
            fullWidth
            placeholder="Buscar domicilio…"
            value={localQ}
            onChange={(e) => setLocalQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onApplyBusqueda(localQ)}
            sx={planificacionTextFieldSx}
          />
          <AppButton dsVariant="secondary" dsSize="sm" onClick={() => onApplyBusqueda(localQ)}>
            Buscar
          </AppButton>
        </Stack>
      </Stack>

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.25 }}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={28} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.82rem", color: GLASS_COLORS.textSecondary, lineHeight: 1.5 }}>
            No hay pendientes con los filtros actuales. Probá otra card KPI, tipo u orden.
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
        gap={1}
        sx={{ flexShrink: 0, pt: 0.5, borderTop: `1px solid ${GLASS_COLORS.borderLight}` }}
      >
        <Typography sx={{ fontFamily: tactic, fontSize: "0.72rem", color: GLASS_COLORS.textMuted }}>
          {meta.total} total · pág. {meta.page}/{totalPages}
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
    </Stack>
  );
}
