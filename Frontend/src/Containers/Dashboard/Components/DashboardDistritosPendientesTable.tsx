import { Box, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

import type { IndicadoresDistritoPendientesItem } from "../../../api/indicadoresApi";
import { dashboardEmptyStateCompactSx, dashboardGlassTableSx } from "../../../styles/DashboardStyles";

type Props = {
  rows: IndicadoresDistritoPendientesItem[];
  loading?: boolean;
};

const EMPTY_MSG =
  "Sin pendientes agrupados por distrito para el período seleccionado.";

/**
 * Tabla compacta de pendientes por distrito (cola planificable).
 */
export function DashboardDistritosPendientesTable({ rows, loading }: Props) {
  if (loading) {
    return <Box sx={dashboardEmptyStateCompactSx}>Cargando distritos…</Box>;
  }

  if (!rows.length) {
    return <Box sx={dashboardEmptyStateCompactSx}>{EMPTY_MSG}</Box>;
  }

  return (
    <Box sx={{ overflowX: "auto" }}>
      <Table size="small" sx={dashboardGlassTableSx}>
        <TableHead>
          <TableRow>
            <TableCell>Distrito</TableCell>
            <TableCell align="right">Relev.</TableCell>
            <TableCell align="right">Denunc.</TableCell>
            <TableCell align="right">Reins. of.</TableCell>
            <TableCell align="right">Reins. not.</TableCell>
            <TableCell align="right">Sin geo</TableCell>
            <TableCell align="right">Total</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.distrito_id}>
              <TableCell sx={{ maxWidth: 200 }}>
                {row.distrito_nombre}
                {row.distrito_codigo ? ` (${row.distrito_codigo})` : ""}
              </TableCell>
              <TableCell align="right">{row.relevamientos}</TableCell>
              <TableCell align="right">{row.denuncias}</TableCell>
              <TableCell align="right">{row.reinspecciones_oficio}</TableCell>
              <TableCell align="right">{row.reinspecciones_notificacion}</TableCell>
              <TableCell align="right">{row.sin_geolocalizacion}</TableCell>
              <TableCell align="right">{row.total}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
