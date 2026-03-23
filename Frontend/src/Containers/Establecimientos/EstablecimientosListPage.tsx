import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import { Box, Grid, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";

import { AppButton, AppSelect, AppTextField } from "../../ui";
import { COLORS } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import {
  filtroContainerStyles,
  filtroTitleStyles,
} from "../Actuaciones/styles/filtroStyles";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import { getMockEstablecimientosList } from "./mocks/establecimientosMock";
import type { IEstablecimientoListRow } from "./types/establecimientos.types";
import { RubroChip } from "./components/RubroChip";

const DISTRITOS = ["Todos los distritos", "Centro", "Norte", "Sur", "Oeste"];

/**
 * Listado de establecimientos (mock): filtros tipo referencia UX + MRT.
 */
export default function EstablecimientosListPage() {
  const navigate = useNavigate();
  const allRows = useMemo(() => getMockEstablecimientosList(), []);

  const [desde, setDesde] = useState("2023-01-01");
  const [hasta, setHasta] = useState("2024-12-31");
  const [contribuyente, setContribuyente] = useState("");
  const [calle, setCalle] = useState("");
  const [distrito, setDistrito] = useState("Todos los distritos");

  const [applied, setApplied] = useState({
    desde: "2023-01-01",
    hasta: "2024-12-31",
    contribuyente: "",
    calle: "",
    distrito: "Todos los distritos",
  });

  const filtered = useMemo(() => {
    const c = applied.contribuyente.trim().toLowerCase();
    const cal = applied.calle.trim().toLowerCase();
    return allRows.filter((row) => {
      if (applied.distrito !== "Todos los distritos" && row.distrito !== applied.distrito) {
        return false;
      }
      if (cal && !row.calle.toLowerCase().includes(cal)) return false;
      if (c) {
        const blob = `${row.nombre} ${row.apellido} ${row.razonSocial}`.toLowerCase();
        if (!blob.includes(c)) return false;
      }
      const f = row.fechaUltimaInspeccion;
      if (f < applied.desde || f > applied.hasta) return false;
      return true;
    });
  }, [allRows, applied]);

  const onFiltrar = useCallback(() => {
    setApplied({
      desde,
      hasta,
      contribuyente,
      calle,
      distrito,
    });
  }, [desde, hasta, contribuyente, calle, distrito]);

  const columns = useMemo<MRT_ColumnDef<IEstablecimientoListRow>[]>(
    () => [
      { accessorKey: "calle", header: "CALLE", size: 200 },
      { accessorKey: "interseccion", header: "INTERSECCIÓN", size: 140 },
      {
        accessorKey: "rubro",
        header: "RUBRO",
        size: 160,
        enableSorting: false,
        Cell: ({ row }) => (
          <RubroChip rubro={row.original.rubro} slug={row.original.rubroSlug} />
        ),
      },
      { accessorKey: "nombre", header: "NOMBRE", size: 120 },
      { accessorKey: "apellido", header: "APELLIDO", size: 120 },
      { accessorKey: "dni", header: "DNI", size: 110 },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: filtered,
    getRowId: (row) => row.id,
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enablePagination: true,
    initialState: {
      density: "compact",
      pagination: { pageSize: 10, pageIndex: 0 },
    },
    muiTableBodyRowProps: () => ({
      sx: { cursor: "default" },
    }),
    displayColumnDefOptions: {
      "mrt-row-actions": { header: "ACCIONES", size: 140 },
    },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <AppButton
        dsVariant="secondary"
        dsSize="sm"
        onClick={() => navigate(`/establecimientos/${row.original.id}`)}
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          textTransform: "uppercase",
          fontSize: "10px",
          fontWeight: 600,
          letterSpacing: "0.06em",
          borderColor: COLORS.border,
          color: COLORS.white,
        }}
      >
        Ver ficha
      </AppButton>
    ),
  });

  return (
    <Stack spacing={2} sx={{ width: "100%", maxWidth: "100%" }}>
      <Box sx={filtroContainerStyles}>
        <Typography sx={filtroTitleStyles}>Filtros</Typography>
        <Grid container spacing={1.5} alignItems="flex-end">
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              type="date"
              label="Inspección desde"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              type="date"
              label="Inspección hasta"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              label="Contribuyente / razón social"
              placeholder="Nombre o fantasía"
              value={contribuyente}
              onChange={(e) => setContribuyente(e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              label="Calle / ubicación"
              value={calle}
              onChange={(e) => setCalle(e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppSelect
              appearance="glass"
              fullWidth
              size="small"
              label="Distrito"
              value={distrito}
              onChange={(e) => setDistrito(String(e.target.value))}
              options={DISTRITOS.map((d) => ({ value: d, label: d }))}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppButton
              dsVariant="primary"
              startIcon={<FilterAltIcon sx={{ fontSize: 18 }} />}
              onClick={onFiltrar}
              sx={{ fontFamily: '"Tactic Sans", sans-serif', fontWeight: 600 }}
            >
              Filtrar
            </AppButton>
          </Grid>
        </Grid>
      </Box>

      <Box sx={{ width: "100%", minWidth: 0, overflow: "hidden" }}>
        <MaterialReactTable table={table} />
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 1,
            fontFamily: '"Tactic Sans", sans-serif',
            color: "rgba(255,255,255,0.45)",
          }}
        >
          Mostrando {filtered.length} establecimiento{filtered.length === 1 ? "" : "s"} (mock)
        </Typography>
      </Box>
    </Stack>
  );
}
