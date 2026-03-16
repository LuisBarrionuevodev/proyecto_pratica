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
  const columns = useMemo<GridColumn[]>(
    () => [
      { id: "select", title: "", width: 44 },
      { id: "id", title: "ID", width: 72, group: "Control" },
      { id: "tipo", title: "Tipo", width: 190, group: "Iniciador" },
      { id: "estado", title: "Estado", width: 140, group: "Iniciador" },
      { id: "origen", title: "Origen", width: 170, group: "Iniciador" },
      { id: "prioridad", title: "Prioridad", width: 120, group: "Iniciador" },
      { id: "turno", title: "Turno", width: 130, group: "Iniciador" },
      { id: "fecha", title: "Fecha origen", width: 140, group: "Iniciador" },
      { id: "calle", title: "Calle", width: 220, group: "Domicilio" },
      { id: "numero", title: "Numero", width: 110, group: "Domicilio" },
      { id: "distrito", title: "Distrito", width: 110, group: "Domicilio" },
      { id: "observaciones", title: "Observaciones", width: 320, group: "Detalle" },
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
      const stateTheme = {
        bgCell: "rgba(9, 121, 105, 0.22)",
        textDark: "#93f7d1",
      };

      const priorityLabel = current.badges?.prioridad_label ?? (current.prioridad ? `P${current.prioridad}` : "S/P");
      const origenLabel = current.badges?.origen_label ?? current.origen?.tipo ?? "-";
      const tipoLabel = current.badges?.tipo_label ?? current.tipo_iniciador;
      const estadoLabel = current.badges?.estado_label ?? current.estado_iniciador;

      if (col === 0) {
        const checked = selectedSet.has(current.id);
        return {
          kind: GridCellKind.Text,
          data: checked ? "✓" : "",
          displayData: checked ? "✓" : "",
          allowOverlay: false,
          readonly: true,
          themeOverride: { bgCell: "rgba(255,255,255,0.02)", textDark: checked ? "#8ec5ff" : "#60718f" },
        };
      }
      if (col === 1) return { kind: GridCellKind.Number, data: current.id, displayData: String(current.id), allowOverlay: false };
      if (col === 2) return { kind: GridCellKind.Bubble, data: [tipoLabel], allowOverlay: false, themeOverride: tagTheme };
      if (col === 3) return { kind: GridCellKind.Bubble, data: [estadoLabel], allowOverlay: false, themeOverride: stateTheme };
      if (col === 4) return { kind: GridCellKind.Bubble, data: [origenLabel], allowOverlay: false, themeOverride: tagTheme };
      if (col === 5) return { kind: GridCellKind.Bubble, data: [priorityLabel], allowOverlay: false, themeOverride: tagTheme };
      if (col === 6) return { kind: GridCellKind.Text, data: current.turno_sugerido ?? "-", displayData: current.turno_sugerido ?? "-", allowOverlay: false };
      if (col === 7) return { kind: GridCellKind.Text, data: current.fecha_origen ?? "-", displayData: current.fecha_origen ?? "-", allowOverlay: false };
      if (col === 8) return { kind: GridCellKind.Text, data: current.domicilio?.calle ?? "-", displayData: current.domicilio?.calle ?? "-", allowOverlay: false };
      if (col === 9) return { kind: GridCellKind.Text, data: current.domicilio?.numero ?? "-", displayData: current.domicilio?.numero ?? "-", allowOverlay: false };
      if (col === 10) {
        const district = current.domicilio?.distrito_id ? String(current.domicilio.distrito_id) : "-";
        return { kind: GridCellKind.Text, data: district, displayData: district, allowOverlay: false };
      }
      return {
        kind: GridCellKind.Text,
        data: current.observaciones ?? "-",
        displayData: current.observaciones ?? "-",
        allowOverlay: false,
      };
    },
    [rows, selectedSet]
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
            if (col === 0 || col > 0) toggleRow(rows[row].id);
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
