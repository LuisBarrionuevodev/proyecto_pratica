import { Box, Stack, Typography } from "@mui/material";
import type { IndicadoresRutaItemsEjecucion } from "../../../api/indicadoresApi";

interface Props {
  data: IndicadoresRutaItemsEjecucion;
}

/**
 * Resumen textual de ítems de ruta por fecha de ruta en rutas publicadas (sin filtro distrito/inspector).
 *
 * Nota: «Ejecución: realizado» cuenta `estado_ejecucion == REALIZADO` por fecha de ruta; no exige
 * `FINALIZADO` ni fecha de cierre como el mapa operativo. Para cifras alineadas al mapa usar `mapa_operativo` del resumen.
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
      <Typography variant="caption" color="rgba(255,255,255,0.5)" sx={{ display: "block", mb: 0.5 }}>
        Métrica descriptiva global; el KPI «Realizados visita (mapa)» refleja FINALIZADO + REALIZADO + fecha de cierre.
      </Typography>
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
