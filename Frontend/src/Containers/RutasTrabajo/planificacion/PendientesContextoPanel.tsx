import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { PlanificacionIniciadorCompactCard } from "./components/PlanificacionIniciadorCompactCard";
import {
  planificacionPanelFooterMetaSx,
  planificacionPanelSubtitleSx,
  planificacionPanelTitleSx,
  planificacionTextFieldSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";
import type { PlanificacionFiltrosLista, PlanificacionOrdenM4 } from "./types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

/**
 * Alto máximo del viewport de la lista (solo este bloque hace scroll).
 * Calibrado para ~2 `PlanificacionIniciadorCompactCard` + `Stack.spacing` entre ítems.
 */
const PENDIENTES_LISTA_VIEWPORT_MAX = "min(17.5rem, 38vh)";

/** Centinela MUI Select: `value=""` suele dar comportamientos raros; en estado seguimos usando `tipo: ""`. */
const TIPO_FILTRO_TODOS_SENTINEL = "__planif_tipo_todos__";

const TIPO_OPCIONES: { value: string; label: string }[] = [
  { value: TIPO_FILTRO_TODOS_SENTINEL, label: "Todos" },
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
  /** Limpia búsqueda/filtros del panel y relanza M4 (lista + mapa), sin recargar la página. */
  onReiniciarContextoPanel: () => void;
  onPageChange: (page: number) => void;
  onAgregar: (row: IRutaIniciadorPendienteRow) => void;
  /** Centrar mapa y abrir card en el punto (requiere coords en el row). */
  onVerEnMapa?: (row: IRutaIniciadorPendienteRow) => void;
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
  onReiniciarContextoPanel,
  onPageChange,
  onAgregar,
  onVerEnMapa,
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

      <Stack spacing={1} sx={{ flexShrink: 0 }}>
        <FormControl size="small" fullWidth>
          <InputLabel id="planif-tipo-label" sx={{ fontFamily: tactic, color: GLASS_COLORS.textSecondary }}>
            Tipo de iniciador
          </InputLabel>
          <Select
            labelId="planif-tipo-label"
            label="Tipo de iniciador"
            value={filtros.tipo === "" ? TIPO_FILTRO_TODOS_SENTINEL : filtros.tipo}
            onChange={(e) => {
              const v = e.target.value;
              onFiltrosChange({ tipo: v === TIPO_FILTRO_TODOS_SENTINEL ? "" : v });
            }}
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
            placeholder="Buscar…"
            value={localQ}
            onChange={(e) => setLocalQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onApplyBusqueda(localQ)}
            sx={planificacionTextFieldSx}
          />
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => onApplyBusqueda(localQ)}>
            Buscar
          </AppButton>
          <Tooltip title="Restablecer búsqueda y filtros del panel">
            <IconButton
              size="small"
              onClick={() => {
                setLocalQ("");
                onReiniciarContextoPanel();
              }}
              aria-label="Restablecer búsqueda y filtros del panel"
              sx={{
                mt: 0.25,
                color: GLASS_COLORS.textSecondary,
                border: `1px solid ${GLASS_COLORS.borderLight}`,
                borderRadius: "10px",
                "&:hover": { color: GLASS_COLORS.primary, borderColor: GLASS_COLORS.borderMedium },
              }}
            >
              <RefreshIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>

      <Box
        sx={{
          maxHeight: PENDIENTES_LISTA_VIEWPORT_MAX,
          minHeight: 0,
          overflow: "auto",
          flexShrink: 0,
          pr: 0.5,
          ...rutasInstitutionalScrollSx,
        }}
      >
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={28} sx={{ color: GLASS_COLORS.primary }} />
          </Box>
        ) : rows.length === 0 ? (
          <Typography sx={{ fontFamily: tactic, fontSize: "0.8125rem", color: GLASS_COLORS.textMuted, lineHeight: 1.45 }}>
            Sin resultados.
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

      {/* Absorbe el alto sobrante de la columna: la paginación queda abajo sin estirar la lista. */}
      <Box sx={{ flexGrow: 1, minHeight: 0, flexShrink: 0 }} aria-hidden />

      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        flexWrap="wrap"
        gap={1}
        sx={{ flexShrink: 0, pt: 0.5, borderTop: `1px solid ${GLASS_COLORS.borderLight}` }}
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
    </Stack>
  );
}
