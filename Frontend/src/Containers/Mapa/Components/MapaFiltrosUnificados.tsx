import { Box, Paper, Stack, Typography } from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
import { AppButton } from "../../../ui/AppButton";
import { AppSelect } from "../../../ui/AppSelect";
import { AppTextField } from "../../../ui/AppTextField";
import { MAPA_DEFINICION_OPTIONS, MAPA_TIPO_INICIADOR_OPTIONS } from "../constants/mapaOperativo";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
import {
  mapaOperativoBarSx,
  mapaOperativoCaptionSx,
  mapaOperativoFieldSx,
} from "./mapaOperativoStyles";

export type MapaFiltrosUnificadosProps = {
  modo: MapaOperativoModo;
  fechaDesde: string;
  fechaHasta: string;
  onFechaDesdeChange: (v: string) => void;
  onFechaHastaChange: (v: string) => void;
  distritoId: string;
  onDistritoIdChange: (v: string) => void;
  distritoOptions: { value: string; label: string }[];
  pendienteTipo: string;
  onPendienteTipoChange: (v: string) => void;
  realizadoTipoIniciador: string;
  onRealizadoTipoIniciadorChange: (v: string) => void;
  realizadoDefinicion: string;
  onRealizadoDefinicionChange: (v: string) => void;
  inspectorId: string;
  onInspectorIdChange: (v: string) => void;
  inspectores: CatalogItem[];
  onAplicar: () => void;
};

/**
 * Una sola caja glass con todos los filtros; el contenido cambía según Pendientes / Realizados.
 */
export function MapaFiltrosUnificados({
  modo,
  fechaDesde,
  fechaHasta,
  onFechaDesdeChange,
  onFechaHastaChange,
  distritoId,
  onDistritoIdChange,
  distritoOptions,
  pendienteTipo,
  onPendienteTipoChange,
  realizadoTipoIniciador,
  onRealizadoTipoIniciadorChange,
  realizadoDefinicion,
  onRealizadoDefinicionChange,
  inspectorId,
  onInspectorIdChange,
  inspectores,
  onAplicar,
}: MapaFiltrosUnificadosProps) {
  const tipoOptions = MAPA_TIPO_INICIADOR_OPTIONS.map((o) => ({ value: o.value, label: o.label }));
  const inspectorOptions = [
    { value: "", label: "Todos los inspectores" },
    ...inspectores.map((i) => ({ value: String(i.id), label: i.nombre })),
  ];

  return (
    <Paper elevation={0} sx={mapaOperativoBarSx}>
      <Stack spacing={2}>
        <Stack
          direction={{ xs: "column", lg: "row" }}
          spacing={2}
          alignItems={{ lg: "flex-end" }}
          flexWrap="wrap"
          useFlexGap
        >
          <AppTextField
            appearance="glass"
            label="Fecha desde"
            type="date"
            value={fechaDesde}
            onChange={(e) => onFechaDesdeChange(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={mapaOperativoFieldSx}
          />
          <AppTextField
            appearance="glass"
            label="Fecha hasta"
            type="date"
            value={fechaHasta}
            onChange={(e) => onFechaHastaChange(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={mapaOperativoFieldSx}
          />
          <AppSelect
            appearance="glass"
            label="Distrito / zona"
            value={distritoId}
            onChange={(e) => onDistritoIdChange(String(e.target.value))}
            options={distritoOptions.map((o) => ({ value: o.value, label: o.label }))}
            sx={{ ...mapaOperativoFieldSx, minWidth: { xs: "100%", lg: 200 } }}
          />
          <AppSelect
            appearance="glass"
            label="Tipo"
            value={modo === "pendientes" ? pendienteTipo : realizadoTipoIniciador}
            onChange={(e) =>
              modo === "pendientes"
                ? onPendienteTipoChange(String(e.target.value))
                : onRealizadoTipoIniciadorChange(String(e.target.value))
            }
            options={tipoOptions}
            sx={{ ...mapaOperativoFieldSx, minWidth: { xs: "100%", lg: 240 } }}
          />
          {modo === "realizados" && (
            <>
              <AppSelect
                appearance="glass"
                label="Definición"
                value={realizadoDefinicion}
                onChange={(e) => onRealizadoDefinicionChange(String(e.target.value))}
                options={MAPA_DEFINICION_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
                sx={{ ...mapaOperativoFieldSx, minWidth: { xs: "100%", lg: 200 } }}
              />
              <AppSelect
                appearance="glass"
                label="Inspector"
                value={inspectorId}
                onChange={(e) => onInspectorIdChange(String(e.target.value))}
                options={inspectorOptions.map((o) => ({ value: o.value, label: o.label }))}
                sx={{ ...mapaOperativoFieldSx, minWidth: { xs: "100%", lg: 220 } }}
              />
            </>
          )}
          <Box sx={{ flex: 1, minWidth: { xs: 0, lg: 8 } }} />
          <AppButton dsVariant="primary" dsSize="md" onClick={onAplicar}>
            Aplicar filtros
          </AppButton>
        </Stack>

        <Typography variant="caption" sx={{ display: "block", ...mapaOperativoCaptionSx }}>
          {modo === "pendientes"
            ? "Los pendientes operativos se conectarán al endpoint municipal. Período, distrito y tipo quedan listos para esa integración."
            : "Definición e inspector se aplicarán con el contrato operativo. La carga actual usa período, distrito y tipo de origen vía /map/points."}
        </Typography>
      </Stack>
    </Paper>
  );
}
