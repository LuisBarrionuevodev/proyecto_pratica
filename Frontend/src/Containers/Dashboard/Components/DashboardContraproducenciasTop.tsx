import { Box, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import type { IndicadoresContraproducenciaTopItem } from "../../../api/indicadoresApi";

interface Props {
  items: IndicadoresContraproducenciaTopItem[];
}

/**
 * Tabla compacta de contraproducencias más frecuentes en el conjunto filtrado.
 */
const DashboardContraproducenciasTop = ({ items }: Props) => {
  if (!items.length) {
    return (
      <Box sx={{ py: 4, textAlign: "center" }}>
        <Typography variant="body2" color="rgba(255,255,255,0.6)">
          Sin contraproducencias en el periodo seleccionado.
        </Typography>
      </Box>
    );
  }

  return (
    <Table size="small" sx={{ "& .MuiTableCell-root": { borderColor: "rgba(255,255,255,0.08)", color: "#fff" } }}>
      <TableHead>
        <TableRow>
          <TableCell sx={{ fontWeight: 700 }}>Contraproducencia</TableCell>
          <TableCell align="right" sx={{ fontWeight: 700, width: 100 }}>
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
