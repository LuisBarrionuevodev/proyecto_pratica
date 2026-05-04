import type { ReactNode } from "react";
import { Box, Paper, Stack, Typography } from "@mui/material";

import type { MapPointFeature } from "../../../api/mapApi";
import { AppButton } from "../../../ui/AppButton";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
import {
  mapaOperativoGlassPanelSx,
  mapaOperativoInnerCardSx,
} from "./mapaOperativoStyles";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";
import { colorPrioridadBacklog } from "./mapaOperativoMarkers";

function countTipoIniciador(features: MapPointFeature[]): Record<string, number> {
  const byTipo: Record<string, number> = {};
  for (const f of features) {
    const t = String(f.properties?.tipo_iniciador ?? "").trim();
    if (t) byTipo[t] = (byTipo[t] ?? 0) + 1;
  }
  return byTipo;
}

function summarizePendientesOperativo(features: MapPointFeature[]) {
  let backlog = 0;
  let enRuta = 0;
  const byTipo: Record<string, number> = {};
  for (const f of features) {
    const p = f.properties ?? {};
    const layer = String(p.map_layer ?? "");
    if (layer === "iniciador_backlog") backlog += 1;
    else if (layer === "ruta_en_proceso") enRuta += 1;
    const t = String(p.tipo_iniciador ?? "").trim();
    if (t) byTipo[t] = (byTipo[t] ?? 0) + 1;
  }
  return { backlog, enRuta, byTipo, total: features.length };
}

function downloadCsv(features: MapPointFeature[], filename: string) {
  const header =
    "domicilio_id,lat,lng,map_layer,tipo_iniciador,iniciador_id,ruta_item_id,prioridad,prioridad_categoria,fecha_ref," +
    "distrito_nombre,inspectores,contribuyente_o_razon_social,domicilio_texto," +
    "acta_inspeccion,acta_notificacion,acta_comprobacion,acta_clausura,acta_decomiso,actuacion_id\n";
  const rows = features
    .map((f) => {
      const c = f.geometry?.coordinates;
      const lat = c?.[1] ?? "";
      const lng = c?.[0] ?? "";
      const p = f.properties ?? {};
      return [
        p.domicilio_id,
        lat,
        lng,
        p.map_layer ?? "",
        p.tipo_iniciador ?? "",
        p.iniciador_id ?? "",
        p.ruta_item_id ?? "",
        p.prioridad ?? "",
        p.prioridad_categoria ?? "",
        p.fecha_ref ?? "",
        p.distrito_nombre ?? "",
        p.inspectores ?? "",
        p.contribuyente_o_razon_social ?? "",
        p.domicilio_texto ?? "",
        p.acta_inspeccion ?? "",
        p.acta_notificacion ?? "",
        p.acta_comprobacion ?? "",
        p.acta_clausura ?? "",
        p.acta_decomiso ?? "",
        p.actuacion_id ?? "",
      ].join(",");
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

type MapLegendShape = "triangle" | "square" | "pin";

function MapLegendSample({
  shape,
  color,
  label,
  squareGlyph = "!",
}: {
  shape: MapLegendShape;
  color: string;
  label: string;
  /** Contenido del cuadrado leyenda (solo `shape === "square"`). */
  squareGlyph?: string;
}) {
  let inner: ReactNode;
  if (shape === "triangle") {
    inner = (
      <Box
        sx={{
          width: 0,
          height: 0,
          borderLeft: "7px solid transparent",
          borderRight: "7px solid transparent",
          borderBottom: `12px solid ${color}`,
          flexShrink: 0,
          filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.35))",
        }}
      />
    );
  } else if (shape === "square") {
    inner = (
      <Box
        sx={{
          width: 16,
          height: 16,
          borderRadius: "4px",
          backgroundColor: color,
          border: `2px solid ${COLORS.white}`,
          flexShrink: 0,
          boxShadow: "0 1px 4px rgba(0,0,0,0.35)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: COLORS.white,
          fontSize: 12,
          fontWeight: 900,
          lineHeight: 1,
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {squareGlyph}
      </Box>
    );
  } else {
    inner = (
      <Box
        component="svg"
        width={18}
        height={22}
        viewBox="0 0 28 34"
        sx={{ flexShrink: 0, filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.35))" }}
      >
        <path
          d="M14 2C8 2 3 6.8 3 12.8c0 6.5 9.2 17.4 10.6 19 .2.3.5.5.9.5.4 0 .7-.2.9-.5 1.4-1.6 10.6-12.5 10.6-19C26 6.8 21 2 14 2z"
          fill={color}
          stroke={COLORS.white}
          strokeWidth={2}
        />
        <circle cx="14" cy="12" r="3.5" fill={COLORS.white} fillOpacity={0.95} />
      </Box>
    );
  }

  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ py: 0.15 }}>
      <Box sx={{ width: 22, display: "flex", justifyContent: "center", alignItems: "center" }}>{inner}</Box>
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
  const byTipoReal = modo === "realizados" ? countTipoIniciador(features) : {};
  const statsPend = summarizePendientesOperativo(features);

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
                {statsPend.total}
              </Typography>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Origen en circuito
              </Typography>
              <Stack spacing={0.5}>
                {distRow("En cola", statsPend.backlog)}
                {distRow("En ruta del día", statsPend.enRuta)}
              </Stack>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Por tipo de iniciador
              </Typography>
              <Stack spacing={0.5}>
                {Object.keys(statsPend.byTipo).length === 0 ? (
                  <Typography variant="body2" sx={{ color: COLORS.grayLight }}>
                    —
                  </Typography>
                ) : (
                  Object.entries(statsPend.byTipo)
                    .sort(([a], [b]) => a.localeCompare(b, "es"))
                    .map(([k, v]) => distRow(k.replace(/_/g, " "), v))
                )}
              </Stack>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Leyenda del mapa
              </Typography>
              <MapLegendSample shape="triangle" color={colorPrioridadBacklog("ALTA")} label="Prioridad alta" />
              <MapLegendSample shape="triangle" color={colorPrioridadBacklog("MEDIA")} label="Prioridad media" />
              <MapLegendSample shape="triangle" color={colorPrioridadBacklog("BAJA")} label="Prioridad baja" />
              <MapLegendSample
                shape="square"
                color={COLORS.primary}
                squareGlyph="!"
                label="Pendientes de completar"
              />
            </Paper>
          </>
        )}

        {modo === "realizados" && (
          <>
            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Visitas realizadas
              </Typography>
              <Typography variant="h3" sx={{ color: COLORS.primary, fontWeight: 800, fontFamily: '"Tactic Sans", sans-serif' }}>
                {features.length}
              </Typography>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Por tipo de iniciador
              </Typography>
              <Stack spacing={0.5}>
                {Object.keys(byTipoReal).length === 0 ? (
                  <Typography variant="body2" sx={{ color: COLORS.grayLight }}>
                    —
                  </Typography>
                ) : (
                  Object.entries(byTipoReal)
                    .sort(([a], [b]) => a.localeCompare(b, "es"))
                    .map(([k, v]) => distRow(k.replace(/_/g, " "), v))
                )}
              </Stack>
            </Paper>

            <Paper elevation={0} sx={mapaOperativoInnerCardSx}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: COLORS.white, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
                Leyenda del mapa
              </Typography>
              <MapLegendSample shape="pin" color={COLORS.success} label="Visita realizada" />
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
