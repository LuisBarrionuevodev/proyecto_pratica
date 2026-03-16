import { useCallback, useMemo } from "react";
import DataEditor, { type GridCell, GridCellKind, type GridColumn, type Item } from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
interface Props {
  rows: IRutaIniciadorPendienteRow[];
  total: number;
  page: number;
  perPage: number;
  loading: boolean;
  selectedIds: number[];
  filters: {
    q: string;
    tipo: string;
    prioridad: string;
    distrito: string;
    turno_sugerido: string;
  };
  onChangeFilters: (next: Props["filters"]) => void;
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
}

const TablaIniciadoresPendientes = ({
  rows,
  total,
  page,
  perPage,
  loading,
  selectedIds,
  filters,
  onChangeFilters,
  onPageChange,
  onPerPageChange,
  onSelectionChange,
  onAssignSelected,
}: Props) => {
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const prioridadText = useCallback((prioridad: number | null | undefined) => {
    if (prioridad === null || prioridad === undefined) return "Sin prioridad";
    if (prioridad >= 3) return "Alta";
    if (prioridad === 2) return "Media";
    return "Baja";
  }, []);

  const prioridadTheme = useCallback((prioridad: number | null | undefined) => {
    if (prioridad === null || prioridad === undefined) {
      return { bgCell: "rgba(95,110,140,0.24)", textDark: "#c6d3ed" };
    }
    if (prioridad >= 3) {
      return { bgCell: "rgba(184,120,34,0.28)", textDark: "#ffd9a2" };
    }
    if (prioridad === 2) {
      return { bgCell: "rgba(58,103,182,0.28)", textDark: "#c8dcff" };
    }
    return { bgCell: "rgba(28,115,80,0.30)", textDark: "#bdf2d7" };
  }, []);

  const columns = useMemo<GridColumn[]>(
    () => [
      { id: "select", title: "", width: 42 },
      { id: "tipo", title: "Tipo", width: 150, group: "Iniciador" },
      { id: "fecha", title: "Fecha", width: 104, group: "Iniciador" },
      { id: "prioridad", title: "Prioridad", width: 110, group: "Iniciador" },
      { id: "domicilio", title: "Domicilio", width: 260, group: "Domicilio" },
      { id: "distrito", title: "Distrito", width: 120, group: "Domicilio" },
      { id: "rubro", title: "Rubro", width: 140, group: "Domicilio" },
      { id: "observaciones", title: "Observaciones", width: 160, group: "Detalle" },
    ],
    []
  );

  const toggleRow = useCallback(
    (id: number) => {
      const exists = selectedSet.has(id);
      if (exists) onSelectionChange(selectedIds.filter((x) => x !== id));
      else onSelectionChange([...selectedIds, id]);
    },
    [onSelectionChange, selectedIds, selectedSet]
  );

  const getCellContent = useCallback(
    ([col, row]: Item): GridCell => {
      const current = rows[row];
      if (!current) {
        return { kind: GridCellKind.Text, data: "", displayData: "", allowOverlay: false };
      }

      const tagTheme = {
        bgCell: "rgba(23, 62, 140, 0.24)",
        textDark: "#c9ddff",
      };
      const tipoLabel = current.badges?.tipo_label ?? current.tipo_iniciador;
      const domicilio = current.domicilio_texto ?? `${current.domicilio?.calle ?? "-"} ${current.domicilio?.numero ?? ""}`.trim();
      const distritoNombre = current.distrito_nombre ?? current.domicilio?.distrito_nombre ?? null;
      const rubro = current.rubro_nombre ?? current.domicilio?.rubro ?? "-";
      const fechaCompacta = current.fecha_origen ? current.fecha_origen.slice(0, 10) : "-";
      const observaciones = current.observaciones ?? "-";
      const observacionesCompacta =
        observaciones.length > 46 ? `${observaciones.slice(0, 43).trimEnd()}...` : observaciones;

      if (col === 0) {
        const checked = selectedSet.has(current.id);
        return {
          kind: GridCellKind.Boolean,
          data: checked,
          displayData: checked ? "true" : "false",
          allowOverlay: false,
          readonly: true,
          themeOverride: { bgCell: "rgba(255,255,255,0.02)", textDark: checked ? "#8ec5ff" : "#60718f" },
        };
      }
      if (col === 1) return { kind: GridCellKind.Bubble, data: [tipoLabel], allowOverlay: false, themeOverride: tagTheme };
      if (col === 2) return { kind: GridCellKind.Text, data: fechaCompacta, displayData: fechaCompacta, allowOverlay: false };
      if (col === 3) {
        const label = prioridadText(current.prioridad);
        return { kind: GridCellKind.Bubble, data: [label], allowOverlay: false, themeOverride: prioridadTheme(current.prioridad) };
      }
      if (col === 4) return { kind: GridCellKind.Text, data: domicilio || "-", displayData: domicilio || "-", allowOverlay: false };
      if (col === 5) return { kind: GridCellKind.Text, data: distritoNombre ?? "-", displayData: distritoNombre ?? "-", allowOverlay: false };
      if (col === 6) return { kind: GridCellKind.Text, data: rubro, displayData: rubro, allowOverlay: false };
      return {
        kind: GridCellKind.Text,
        data: observacionesCompacta,
        displayData: observacionesCompacta,
        copyData: observaciones,
        allowOverlay: false,
      };
    },
    [prioridadText, prioridadTheme, rows, selectedSet]
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center" justifyContent="space-between">
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <TextField
            size="small"
            label="Buscar"
            value={filters.q}
            onChange={(e) => onChangeFilters({ ...filters, q: e.target.value })}
            sx={{ minWidth: 220 }}
          />
          <TextField
            select
            size="small"
            label="Tipo"
            value={filters.tipo}
            onChange={(e) => onChangeFilters({ ...filters, tipo: e.target.value })}
            sx={{ minWidth: 180 }}
          >
            <MenuItem value="">Todos</MenuItem>
            <MenuItem value="RELEVAMIENTO">Relevamiento</MenuItem>
            <MenuItem value="DENUNCIA">Denuncia</MenuItem>
            <MenuItem value="REINSPECCION_OFICIO">Reinspeccion oficio</MenuItem>
            <MenuItem value="REINSPECCION_NOTIFICACION">Reinspeccion notificacion</MenuItem>
          </TextField>
          <TextField
            size="small"
            label="Prioridad"
            value={filters.prioridad}
            onChange={(e) => onChangeFilters({ ...filters, prioridad: e.target.value })}
            sx={{ width: 120 }}
          />
          <TextField
            size="small"
            label="Distrito"
            value={filters.distrito}
            onChange={(e) => onChangeFilters({ ...filters, distrito: e.target.value })}
            sx={{ width: 120 }}
          />
          <TextField
            select
            size="small"
            label="Turno sugerido"
            value={filters.turno_sugerido}
            onChange={(e) => onChangeFilters({ ...filters, turno_sugerido: e.target.value })}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">Todos</MenuItem>
            <MenuItem value="MANIANA">Maniana</MenuItem>
            <MenuItem value="TARDE">Tarde</MenuItem>
          </TextField>
        </Stack>
        <Stack direction="row" spacing={1} alignItems="center">
          <Chip label={`${selectedIds.length} seleccionados`} color="primary" variant="outlined" />
          <Button variant="contained" onClick={onAssignSelected} disabled={selectedIds.length === 0}>
            Asignar seleccionados
          </Button>
        </Stack>
      </Stack>

      <Box
        sx={{
          position: "relative",
          height: 560,
          border: "1px solid rgba(104, 132, 179, 0.24)",
          borderRadius: 2,
          overflow: "hidden",
          background: "linear-gradient(180deg, rgba(16,24,42,0.96), rgba(11,17,32,0.98))",
        }}
      >
        {loading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 2,
              bgcolor: "rgba(0,0,0,0.35)",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <CircularProgress size={24} />
          </Box>
        )}
        <DataEditor
          getCellContent={getCellContent}
          columns={columns}
          rows={rows.length}
          onCellClicked={([col, row]) => {
            if (row < 0 || row >= rows.length) return;
            if (col === 0) toggleRow(rows[row].id);
          }}
          rowMarkers="none"
          smoothScrollX
          smoothScrollY
          rowHeight={40}
          headerHeight={42}
          groupHeaderHeight={34}
          getCellsForSelection
          freezeColumns={1}
          theme={{
            accentColor: "#3f7bff",
            textDark: "#dde7ff",
            textMedium: "#a5b6d6",
            textHeader: "#f2f6ff",
            textGroupHeader: "#8ba3cf",
            bgCell: "#0f1a2f",
            bgCellMedium: "#0b1528",
            bgHeader: "#111f38",
            bgHeaderHovered: "#172b4c",
            bgHeaderHasFocus: "#172b4c",
            borderColor: "rgba(88, 113, 156, 0.3)",
            horizontalBorderColor: "rgba(88, 113, 156, 0.22)",
            linkColor: "#79b2ff",
            fontFamily: '"Tactic Sans", "Segoe UI", sans-serif',
            baseFontStyle: "12px",
            headerFontStyle: "600 12px",
          }}
        />
      </Box>

      <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
        <Typography variant="body2">Total pendientes: {total}</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <Button size="small" variant="outlined" onClick={() => onPageChange(Math.max(1, page - 1))} disabled={page <= 1}>
            Anterior
          </Button>
          <Typography variant="body2">Pagina {page}</Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={() => onPageChange(page + 1)}
            disabled={page * perPage >= total}
          >
            Siguiente
          </Button>
          <TextField
            select
            size="small"
            label="Por pagina"
            value={String(perPage)}
            onChange={(e) => onPerPageChange(Number(e.target.value))}
            sx={{ width: 130 }}
          >
            <MenuItem value="25">25</MenuItem>
            <MenuItem value="50">50</MenuItem>
            <MenuItem value="100">100</MenuItem>
          </TextField>
        </Stack>
      </Stack>
    </Box>
  );
};

export default TablaIniciadoresPendientes;
