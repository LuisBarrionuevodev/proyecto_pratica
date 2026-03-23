import { useMemo } from "react";
import { Box, CircularProgress, IconButton, Tooltip, Typography } from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import type { TrabajoDelDiaRow } from "../types/completarTrabajos.types";
import {
  COLORS,
  DARK_TABLE_CONFIG,
} from "../../Actuaciones/styles/actuacionesTableStyles";

export type CompletarTrabajosMRTProps = {
  rows: TrabajoDelDiaRow[];
  onRowsChange: (rows: TrabajoDelDiaRow[]) => void;
  loading?: boolean;
};

function dashIfEmpty(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function parseNullableText(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s === "" ? null : s;
}

function parseKilos(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const n = parseFloat(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

/**
 * Tabla MRT de trabajos del día: edición por fila (row), una fila a la vez.
 * Columnas precargadas readonly; resultado y motivos editables con Guardar/Cancelar por fila.
 */
export function CompletarTrabajosMRT({ rows, onRowsChange, loading = false }: CompletarTrabajosMRTProps) {
  const columns = useMemo<MRT_ColumnDef<TrabajoDelDiaRow>[]>(
    () => [
      {
        header: "Base",
        columns: [
          {
            accessorKey: "fecha",
            header: "Fecha",
            enableEditing: false,
            size: 104,
            Cell: ({ cell }) => (
              <span style={{ opacity: 0.95 }}>{dashIfEmpty(cell.getValue())}</span>
            ),
          },
          {
            accessorKey: "tipoIniciador",
            header: "Tipo iniciador",
            enableEditing: false,
            size: 168,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
          {
            accessorKey: "ordenTrabajo",
            header: "OT",
            enableEditing: false,
            size: 112,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
          {
            accessorKey: "inspectores",
            header: "Inspectores",
            enableEditing: false,
            size: 160,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
          {
            accessorKey: "calle",
            header: "Calle",
            enableEditing: false,
            size: 180,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
          {
            accessorKey: "interseccion",
            header: "Intersección",
            enableEditing: false,
            size: 140,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
        ],
      },
      {
        header: "Identificación",
        columns: [
          {
            accessorKey: "nombre",
            header: "Nombre",
            enableEditing: false,
            size: 120,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
          {
            accessorKey: "apellido",
            header: "Apellido",
            enableEditing: false,
            size: 120,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
          {
            accessorKey: "dni",
            header: "DNI",
            enableEditing: false,
            size: 100,
            Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
          },
        ],
      },
      {
        header: "Resultado",
        columns: [
          {
            accessorKey: "contraproducencia",
            header: "Contraproducencia",
            size: 140,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "actaInspeccion",
            header: "Acta inspección",
            size: 120,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "notificacion",
            header: "Notificación",
            size: 120,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "actaComprobacion",
            header: "Acta comprobación",
            size: 140,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "motivo",
            header: "Motivo",
            size: 120,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "actaClausura",
            header: "Acta clausura",
            size: 120,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "actaDecomiso",
            header: "Acta decomiso",
            size: 120,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "kilosDecomisados",
            header: "Kg decomisados",
            size: 120,
            muiEditTextFieldProps: {
              type: "number",
              placeholder: "—",
              inputProps: { step: "any", min: 0 },
            },
            Cell: ({ cell }) => {
              const v = cell.getValue() as number | null | undefined;
              if (v === null || v === undefined) return <span style={{ opacity: 0.5 }}>—</span>;
              return <span>{String(v)}</span>;
            },
          },
        ],
      },
      {
        header: "Motivos",
        columns: [
          {
            accessorKey: "motivo1",
            header: "Motivo 1",
            size: 130,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "motivo2",
            header: "Motivo 2",
            size: 130,
            muiEditTextFieldProps: { placeholder: "—" },
          },
          {
            accessorKey: "motivo3",
            header: "Motivo 3",
            size: 130,
            muiEditTextFieldProps: { placeholder: "—" },
          },
        ],
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    muiTablePaperProps: {
      sx: {
        backgroundColor: "transparent",
        boxShadow: "none",
        border: "none",
        borderRadius: 0,
        overflow: "visible",
      },
    },
    muiTableContainerProps: {
      sx: {
        ...((DARK_TABLE_CONFIG.muiTableContainerProps as { sx?: object })?.sx ?? {}),
        maxHeight: "calc(100vh - 260px)",
      },
    },
    columns,
    data: rows,
    getRowId: (row) => String(row.id),
    enableEditing: true,
    editDisplayMode: "row",
    enableRowSelection: false,
    enableRowActions: true,
    positionActionsColumn: "first",
    localization: {
      save: "Guardar",
      cancel: "Cancelar",
    },
    initialState: {
      density: "compact",
      pagination: { pageSize: 25, pageIndex: 0 },
    },
    state: {
      isLoading: loading,
    },
    muiEditTextFieldProps: {
      variant: "outlined",
      size: "small",
      sx: {
        "& .MuiOutlinedInput-root": {
          backgroundColor: COLORS.rowOdd,
          color: COLORS.white,
        },
        "& .MuiOutlinedInput-notchedOutline": { borderColor: COLORS.border },
        "& input": { color: COLORS.white },
      },
    },
    onEditingRowSave: ({ row, values, exitEditingMode }) => {
      const rid = row.original.id;
      const merged: TrabajoDelDiaRow = {
        ...row.original,
        contraproducencia: parseNullableText(values.contraproducencia),
        actaInspeccion: parseNullableText(values.actaInspeccion),
        notificacion: parseNullableText(values.notificacion),
        actaComprobacion: parseNullableText(values.actaComprobacion),
        motivo: parseNullableText(values.motivo),
        actaClausura: parseNullableText(values.actaClausura),
        actaDecomiso: parseNullableText(values.actaDecomiso),
        kilosDecomisados: parseKilos(values.kilosDecomisados),
        motivo1: parseNullableText(values.motivo1),
        motivo2: parseNullableText(values.motivo2),
        motivo3: parseNullableText(values.motivo3),
      };
      onRowsChange(rows.map((r) => (r.id === rid ? merged : r)));
      exitEditingMode();
    },
    renderRowActions: ({ row, table }) => {
      const editing = table.getState().editingRow;
      const editingId = editing?.id;
      const otherRowEditing = editingId != null && String(editingId) !== String(row.id);
      return (
        <Box sx={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
          <Tooltip title={otherRowEditing ? "Terminá o cancelá la edición de la otra fila" : "Editar"}>
            <span>
              <IconButton
                size="small"
                disabled={otherRowEditing}
                sx={{
                  color: COLORS.white,
                  "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
                  "&.Mui-disabled": { color: "#555" },
                }}
                onClick={() => table.setEditingRow(row)}
                aria-label="Editar fila"
              >
                <EditIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      );
    },
  });

  return (
    <Box sx={{ position: "relative", display: "flex", flexDirection: "column", gap: 1 }}>
      <Box sx={{ position: "relative" }}>
        {loading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 2,
              bgcolor: "rgba(0, 0, 0, 0.45)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              gap: 1,
              borderRadius: "8px",
            }}
          >
            <CircularProgress size={28} sx={{ color: COLORS.primary }} />
            <Typography
              variant="body2"
              sx={{ fontFamily: '"Tactic Sans", sans-serif', color: "rgba(255,255,255,0.75)" }}
            >
              Cargando trabajos…
            </Typography>
          </Box>
        )}
        <MaterialReactTable table={table} />
      </Box>
      <Typography
        variant="caption"
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          color: "rgba(255,255,255,0.55)",
          display: "block",
        }}
      >
        Los cambios son solo en pantalla; aún no se guardan en el servidor.
      </Typography>
    </Box>
  );
}
