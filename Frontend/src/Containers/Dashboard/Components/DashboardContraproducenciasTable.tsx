import { Box, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import type { ContraproducenciaResumenRow } from "../utils/noRealizadasContraproducencias";
import { formatPorcentajeNoRealizadas } from "../utils/noRealizadasContraproducencias";
import { dashboardEmptyStateCompactSx, dashboardGlassTableSx } from "../../../styles/DashboardStyles";

type Props = {
  rows: ContraproducenciaResumenRow[];
  emptyMessage?: string;
  showZeroRows?: boolean;
};

/**
 * Tabla compacta de contraproducencias (cantidad + % del total).
 */
export function DashboardContraproducenciasTable({
  rows,
  emptyMessage = "Sin motivos registrados en el período.",
  showZeroRows = false,
}: Props) {
  const visibleRows = showZeroRows ? rows : rows.filter((r) => r.cantidad > 0);

  if (!visibleRows.length) {
    return <Box sx={dashboardEmptyStateCompactSx}>{emptyMessage}</Box>;
  }

  return (
    <Box sx={{ overflowX: "auto" }}>
      <Table size="small" sx={dashboardGlassTableSx}>
        <TableHead>
          <TableRow>
            <TableCell>Contraproducencia</TableCell>
            <TableCell align="right">Cantidad</TableCell>
            <TableCell align="right">%</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {visibleRows.map((row) => (
            <TableRow key={row.contraproducencia}>
              <TableCell sx={{ maxWidth: 220 }}>
                <Typography
                  component="span"
                  variant="body2"
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    display: "block",
                  }}
                  title={row.contraproducencia}
                >
                  {row.contraproducencia}
                </Typography>
              </TableCell>
              <TableCell align="right">{row.cantidad}</TableCell>
              <TableCell align="right">{formatPorcentajeNoRealizadas(row.porcentaje)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
