import { Box, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import type { IndicadoresContraproducenciaPorTipo } from "../../../api/indicadoresApi";
import { dashboardEmptyStateSx, dashboardGlassTableSx } from "../../../styles/DashboardStyles";

type Props = {
  items: IndicadoresContraproducenciaPorTipo[];
};

/**
 * Distribución completa por contraproducencia (tabla compacta; evita barra duplicada del top).
 */
export function DashboardContraproducenciasPorTipoTable({ items }: Props) {
  if (!items.length) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">Sin actuaciones en el periodo.</Typography>
      </Box>
    );
  }

  const sorted = [...items].sort((a, b) => b.count - a.count);

  return (
    <Table size="small" sx={dashboardGlassTableSx}>
      <TableHead>
        <TableRow>
          <TableCell>Valor</TableCell>
          <TableCell align="right" sx={{ width: 88 }}>
            Cant.
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {sorted.map((row) => (
          <TableRow key={`${row.valor}-${row.count}`}>
            <TableCell sx={{ maxWidth: 320 }}>{row.valor}</TableCell>
            <TableCell align="right">{row.count}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
