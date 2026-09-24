import type { ReactNode } from "react";

import { Box, Paper, Stack, Typography } from "@mui/material";



import type { MapOperativoMeta, MapPointFeature } from "../../../api/mapApi";

import { AppButton } from "../../../ui/AppButton";

import {

  mapaOperativoCardTitleSx,

  mapaOperativoGlassPanelSx,

  mapaOperativoHeroValueSx,

  mapaOperativoInnerCardSx,

  mapaOperativoLegendLabelSx,

  mapaOperativoMetricRowLabelSx,

  mapaOperativoMetricRowSx,

  mapaOperativoMetricRowValueSx,

  mapaOperativoPanelTitleSx,

} from "./mapaOperativoStyles";

import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";



function countTipoIniciador(features: MapPointFeature[]): Record<string, number> {

  const byTipo: Record<string, number> = {};

  for (const f of features) {

    const t = String(f.properties?.tipo_iniciador ?? "").trim();

    if (t) byTipo[t] = (byTipo[t] ?? 0) + 1;

  }

  return byTipo;

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



type MapLegendShape = "pin";



function MapLegendSample({ color, label }: { shape: MapLegendShape; color: string; label: string }) {

  const inner: ReactNode = (

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



  return (

    <Stack direction="row" spacing={1} alignItems="center" sx={{ py: 0.15 }}>

      <Box sx={{ width: 22, display: "flex", justifyContent: "center", alignItems: "center" }}>{inner}</Box>

      <Typography variant="body2" sx={mapaOperativoLegendLabelSx}>

        {label}

      </Typography>

    </Stack>

  );

}



export type PanelResumenOperativoProps = {

  features: MapPointFeature[];

  meta: MapOperativoMeta | null;

};



/** Columna izquierda del modo operativo en MapPage. */

export function PanelResumenOperativo({ features, meta }: PanelResumenOperativoProps) {

  const byTipoReal = countTipoIniciador(features);



  const metricRow = (label: string, value: number | string) => (

    <Stack

      key={label}

      direction="row"

      justifyContent="space-between"

      alignItems="center"

      sx={mapaOperativoMetricRowSx}

    >

      <Typography variant="body2" sx={mapaOperativoMetricRowLabelSx}>

        {label}

      </Typography>

      <Typography variant="body2" sx={mapaOperativoMetricRowValueSx}>

        {value}

      </Typography>

    </Stack>

  );



  return (

    <Paper

      elevation={0}

      sx={{

        ...mapaOperativoGlassPanelSx,

        height: "100%",

        display: "flex",

        flexDirection: "column",

      }}

    >

      <Typography variant="subtitle1" sx={{ ...mapaOperativoPanelTitleSx, mb: 2 }}>

        Resumen operativo

      </Typography>



      <Stack spacing={2} sx={{ flex: 1 }}>

        <Paper elevation={0} sx={mapaOperativoInnerCardSx}>

          <Typography variant="subtitle2" sx={{ ...mapaOperativoCardTitleSx, display: "block", mb: 1 }}>

            Trabajos operativos

          </Typography>

          <Typography variant="h3" sx={mapaOperativoHeroValueSx}>

            {meta?.total_operativos ?? 0}

          </Typography>

          <Stack spacing={0.35} sx={{ mt: 1 }}>

            {metricRow("Realizados", meta?.realizados ?? 0)}

            {metricRow("No realizados", meta?.no_realizados ?? 0)}

            {metricRow("Con ubicación", meta?.total_dibujables ?? features.length)}

            {metricRow("Sin ubicación", meta?.total_sin_geocode ?? 0)}

          </Stack>

        </Paper>



        <Paper elevation={0} sx={mapaOperativoInnerCardSx}>

          <Typography variant="subtitle2" sx={{ ...mapaOperativoCardTitleSx, display: "block", mb: 1 }}>

            Por tipo de iniciador · con ubicación

            {features.length > 0 ? ` (${features.length})` : ""}

          </Typography>

          <Stack spacing={0.5}>

            {Object.keys(byTipoReal).length === 0 ? (

              <Typography variant="body2" sx={mapaOperativoMetricRowLabelSx}>

                —

              </Typography>

            ) : (

              Object.entries(byTipoReal)

                .sort(([a], [b]) => a.localeCompare(b, "es"))

                .map(([k, v]) => metricRow(k.replace(/_/g, " "), v))

            )}

          </Stack>

        </Paper>



        <Paper elevation={0} sx={mapaOperativoInnerCardSx}>

          <Typography variant="subtitle2" sx={{ ...mapaOperativoCardTitleSx, display: "block", mb: 1 }}>

            Leyenda del mapa

          </Typography>

          <MapLegendSample shape="pin" color={COLORS.success} label="Realizado" />

          <MapLegendSample shape="pin" color={COLORS.warning} label="No realizado" />

        </Paper>

      </Stack>



      <AppButton

        dsVariant="secondary"

        dsSize="md"

        fullWidth

        sx={{ mt: 2 }}

        disabled={features.length === 0}

        onClick={() => downloadCsv(features, "mapa_realizados.csv")}

      >

        Descargar reporte CSV

      </AppButton>

    </Paper>

  );

}


