import { Box, Stack, Typography } from "@mui/material";
import type { IndicadoresRutaItemsEjecucion } from "../../../api/indicadoresApi";

interface Props {
  data: IndicadoresRutaItemsEjecucion;
}

/**
 * Resumen textual de ítems de ruta por fecha de ruta (sin filtro distrito/inspector en backend v1).
 */
const DashboardRutaItemsResumen = ({ data }: Props) => {
  const rows = [
    { label: "Total ítems", value: data.total },
    { label: "Ejecución: realizado", value: data.estado_ejecucion_realizado },
    { label: "Ejecución: no realizado", value: data.estado_ejecucion_no_realizado },
    { label: "Ejecución: sin clasificar", value: data.estado_ejecucion_sin_clasificar },
  ];

  return (
    <Stack spacing={1.5} sx={{ py: 1 }}>
      {rows.map((r) => (
        <Box
          key={r.label}
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            pb: 1,
          }}
        >
          <Typography variant="body2" color="rgba(255,255,255,0.75)">
            {r.label}
          </Typography>
          <Typography variant="h6" color="#fff" fontWeight={600}>
            {r.value}
          </Typography>
        </Box>
      ))}
    </Stack>
  );
};

export default DashboardRutaItemsResumen;
