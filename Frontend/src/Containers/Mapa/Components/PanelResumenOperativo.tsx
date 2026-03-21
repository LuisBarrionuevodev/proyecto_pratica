import { Box, Paper, Stack, Typography } from "@mui/material";

import type { MapPointFeature } from "../../../api/mapApi";
import { AppButton } from "../../../ui/AppButton";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
import {
  mapaOperativoGlassPanelSx,
  mapaOperativoInnerCardSx,
} from "./mapaOperativoStyles";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

function summarize(features: MapPointFeature[]) {
  let soloAct = 0;
  let soloRel = 0;
  let ambos = 0;
  for (const f of features) {
    const p = f.properties ?? {};
    const ha = Boolean(p.has_act);
    const hr = Boolean(p.has_rel);
    if (ha && hr) ambos += 1;
    else if (ha) soloAct += 1;
    else if (hr) soloRel += 1;
  }
  return { soloAct, soloRel, ambos, total: features.length };
}

function downloadCsv(features: MapPointFeature[], filename: string) {
  const header = "domicilio_id,lat,lng,act_count,rel_count\n";
  const rows = features
    .map((f) => {
      const c = f.geometry?.coordinates;
      const lat = c?.[1] ?? "";
      const lng = c?.[0] ?? "";
      const p = f.properties ?? {};
      return [p.domicilio_id, lat, lng, p.act_count ?? "", p.rel_count ?? ""].join(",");
    })
    .join("\n");
  const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function PrioridadDot({ color, label }: { color: string; label: string }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ py: 0.35 }}>
      <Box
        sx={{
          width: 12,
          height: 12,
          borderRadius: "50%",
          backgroundColor: color,
          flexShrink: 0,
          boxShadow: `0 0 0 2px ${COLORS.border}`,
        }}
      />
      <Typography variant="body2" sx={{ color: COLORS.grayLight, fontFamily: '"Tactic Sans", sans-serif' }}>
        {label}
      </Typography>
    </Stack>
  );
}

export type PanelResumenOperativoProps = {
  modo: MapaOperativoModo;
  features: MapPointFeature[];
};

/**
 * Columna izquierda: bloques separados en subcajas según el modo (pendientes / realizados).
 */
export function PanelResumenOperativo({ modo, features }: PanelResumenOperativoProps) {
  const stats = summarize(features);

  const distRow = (label: string, value: number | string) => (
    <Stack key={label} direction="row" justifyContent="space-between" alignItems="center" sx={{ py: 0.35 }}>
      <Typography variant="body2" sx={{ color: COLORS.grayLight, fontFamily: '"Tactic Sans", sans-serif' }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600, color: COLORS.white }}>
        {value}
      </Typography>
    </Stack>
  );

  return (
    <Paper
      elevation={0}
      sx={{
        ...mapaOperativoGlassPanelSx,
        p: 2,
        height: "100%",
        minHeight: 360,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Typography
        variant="subtitle1"
        sx={{ fontWeight: 700, mb: 2, color: COLORS.white, fontFamily: '"Tactic Sans", sans-serif' }}
      >
        Resumen operativo
      </Typography>

      <Stack spacing={2} sx={{ flex: 1 }}>
        {modo === "pendientes" && (
          <>
            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Tareas pendientes
              </Typography>
              <Typography variant="h3" sx={{ color: COLORS.primary, fontWeight: 800, fontFamily: '"Tactic Sans", sans-serif' }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" sx={{ color: COLORS.grayLight, display: "block", mt: 0.5 }}>
                En mapa según filtros (pendiente de datos operativos).
              </Typography>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Distribución por tipo
              </Typography>
              <Stack spacing={0.5}>
                {distRow("Denuncias", 0)}
                {distRow("Relevamientos", 0)}
                {distRow("Reinspecciones", 0)}
                {distRow("Reinspecciones de oficio", 0)}
              </Stack>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Prioridad en mapa
              </Typography>
              <PrioridadDot color={COLORS.primary} label="Alta" />
              <PrioridadDot color={COLORS.warning} label="Media" />
              <PrioridadDot color={COLORS.grayLight} label="Baja" />
            </Paper>
          </>
        )}

        {modo === "realizados" && (
          <>
            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Actuaciones realizadas
              </Typography>
              <Typography variant="h3" sx={{ color: COLORS.primary, fontWeight: 800, fontFamily: '"Tactic Sans", sans-serif' }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" sx={{ color: COLORS.grayLight, display: "block", mt: 0.5 }}>
                Puntos en mapa (domicilios con actividad en el período filtrado).
              </Typography>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Desglose resolutivo
              </Typography>
              <Stack spacing={0.5}>
                {distRow("Clausuras", "—")}
                {distRow("Decomisos", "—")}
                {distRow("Actas de comprobación", "—")}
                {distRow("Notificaciones", "—")}
              </Stack>
              <Typography variant="caption" sx={{ color: COLORS.grayLight, display: "block", mt: 1 }}>
                Valores al conectar endpoint operativo con actas vinculadas.
              </Typography>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Top inspectores
              </Typography>
              <Stack spacing={1}>
                {[1, 2, 3].map((i) => (
                  <Stack key={i} direction="row" justifyContent="space-between">
                    <Typography variant="body2" sx={{ color: COLORS.grayLight }}>
                      —
                    </Typography>
                    <Typography variant="body2" sx={{ color: COLORS.white, fontWeight: 600 }}>
                      —
                    </Typography>
                  </Stack>
                ))}
              </Stack>
              <Typography variant="caption" sx={{ color: COLORS.grayLight, display: "block", mt: 1 }}>
                Ranking según actuaciones en el período (pendiente de API).
              </Typography>
            </Paper>
          </>
        )}
      </Stack>

      <AppButton
        dsVariant="secondary"
        dsSize="md"
        fullWidth
        sx={{ mt: 2 }}
        disabled={features.length === 0}
        onClick={() => downloadCsv(features, `mapa_${modo}.csv`)}
      >
        Descargar reporte CSV
      </AppButton>
    </Paper>
  );
}
