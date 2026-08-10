import { Grid, Paper, Stack } from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
import { AppButton } from "../../../ui/AppButton";
import { AppSelect } from "../../../ui/AppSelect";
import { AppTextField } from "../../../ui/AppTextField";
import { MAPA_DEFINICION_OPTIONS, MAPA_TIPO_INICIADOR_OPTIONS } from "../constants/mapaOperativo";
import { mapaOperativoBarSx, mapaOperativoFieldSx } from "./mapaOperativoStyles";

export type MapaFiltrosUnificadosProps = {
  fechaDesde: string;
  fechaHasta: string;
  onFechaDesdeChange: (v: string) => void;
  onFechaHastaChange: (v: string) => void;
  distritoId: string;
  onDistritoIdChange: (v: string) => void;
  distritoOptions: { value: string; label: string }[];
  realizadoTipoIniciador: string;
  onRealizadoTipoIniciadorChange: (v: string) => void;
  realizadoDefinicion: string;
  onRealizadoDefinicionChange: (v: string) => void;
  inspectorId: string;
  onInspectorIdChange: (v: string) => void;
  inspectores: CatalogItem[];
  onAplicar: () => void;
  onRefrescar: () => void;
};

/** Filtros del modo Realizados en MapPage. */
export function MapaFiltrosUnificados({
  fechaDesde,
  fechaHasta,
  onFechaDesdeChange,
  onFechaHastaChange,
  distritoId,
  onDistritoIdChange,
  distritoOptions,
  realizadoTipoIniciador,
  onRealizadoTipoIniciadorChange,
  realizadoDefinicion,
  onRealizadoDefinicionChange,
  inspectorId,
  onInspectorIdChange,
  inspectores,
  onAplicar,
  onRefrescar,
}: MapaFiltrosUnificadosProps) {
  const tipoOptions = MAPA_TIPO_INICIADOR_OPTIONS.map((o) => ({ value: o.value, label: o.label }));
  const inspectorOptions = [
    { value: "", label: "Todos los inspectores" },
    ...inspectores.map((i) => ({ value: String(i.id), label: i.nombre })),
  ];

  return (
    <Paper elevation={0} sx={mapaOperativoBarSx} data-testid="mapa-realizados-filtros">
      <Stack spacing={2}>
        <Grid container spacing={2} alignItems="flex-end">
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <AppTextField
              appearance="glass"
              label="Fecha desde"
              type="date"
              value={fechaDesde}
              onChange={(e) => onFechaDesdeChange(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={mapaOperativoFieldSx}
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <AppTextField
              appearance="glass"
              label="Fecha hasta"
              type="date"
              value={fechaHasta}
              onChange={(e) => onFechaHastaChange(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={mapaOperativoFieldSx}
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <AppSelect
              appearance="glass"
              label="Distrito / zona"
              value={distritoId}
              onChange={(e) => onDistritoIdChange(String(e.target.value))}
              options={distritoOptions.map((o) => ({ value: o.value, label: o.label }))}
              sx={mapaOperativoFieldSx}
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <AppSelect
              appearance="glass"
              label="Inspector"
              value={inspectorId}
              onChange={(e) => onInspectorIdChange(String(e.target.value))}
              options={inspectorOptions.map((o) => ({ value: o.value, label: o.label }))}
              sx={mapaOperativoFieldSx}
              fullWidth
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <AppSelect
              appearance="glass"
              label="Tipo"
              value={realizadoTipoIniciador}
              onChange={(e) => onRealizadoTipoIniciadorChange(String(e.target.value))}
              options={tipoOptions}
              data-testid="mapa-realizados-filtro-tipo"
              SelectProps={{ displayEmpty: false }}
              sx={mapaOperativoFieldSx}
              fullWidth
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <AppSelect
              appearance="glass"
              label="Definición"
              value={realizadoDefinicion}
              onChange={(e) => onRealizadoDefinicionChange(String(e.target.value))}
              options={MAPA_DEFINICION_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
              data-testid="mapa-realizados-filtro-definicion"
              sx={mapaOperativoFieldSx}
              fullWidth
            />
          </Grid>
          <Grid
            size={{ xs: 12, md: 4 }}
            sx={{ display: "flex", justifyContent: { xs: "stretch", md: "flex-end" } }}
          >
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              flexWrap="wrap"
              useFlexGap
              sx={{ width: { xs: "100%", md: "auto" } }}
            >
              <AppButton dsVariant="primary" dsSize="md" onClick={onAplicar} sx={{ flex: { xs: 1, sm: "none" } }}>
                Aplicar filtros
              </AppButton>
              <AppButton dsVariant="primary" dsSize="md" onClick={onRefrescar} sx={{ flex: { xs: 1, sm: "none" } }}>
                Refrescar
              </AppButton>
            </Stack>
          </Grid>
        </Grid>
      </Stack>
    </Paper>
  );
}
