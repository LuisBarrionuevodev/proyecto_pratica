import { Box, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import type { IndicadoresContraproducenciaTopItem } from "../../../api/indicadoresApi";
import { dashboardEmptyStateSx, dashboardGlassTableSx } from "../../../styles/DashboardStyles";

interface Props {
  items: IndicadoresContraproducenciaTopItem[];
}

/**
 * Tabla compacta de contraproducencias más frecuentes en el conjunto filtrado.
 */
const DashboardContraproducenciasTop = ({ items }: Props) => {
  if (!items.length) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">Sin contraproducencias en el periodo seleccionado.</Typography>
      </Box>
    );
  }

  return (
    <Table size="small" sx={dashboardGlassTableSx}>
      <TableHead>
        <TableRow>
          <TableCell>Contraproducencia</TableCell>
          <TableCell align="right" sx={{ width: 100 }}>
            Cantidad
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {items.map((row) => (
          <TableRow key={`${row.valor}-${row.count}`}>
            <TableCell sx={{ maxWidth: 280 }}>{row.valor}</TableCell>
            <TableCell align="right">{row.count}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default DashboardContraproducenciasTop;
