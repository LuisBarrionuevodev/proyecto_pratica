import { Box } from "@mui/material";

import type { CatalogItem } from "../../../api/gridApi";
import { AppButton } from "../../../ui/AppButton";
import { AppSelect } from "../../../ui/AppSelect";
import { AppTextField } from "../../../ui/AppTextField";
import {
  filtroButtonPrimaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
} from "../../Actuaciones/styles/filtroStyles";
import {
  MAPA_EJECUCION_OPTIONS,
  MAPA_MOTIVO_NO_REALIZADO_OPTIONS,
  MAPA_ORIGEN_OPTIONS,
  MAPA_TIPO_INICIADOR_OPTIONS,
} from "../constants/mapaOperativo";

export type MapaFiltrosUnificadosProps = {
  fechaDesde: string;
  fechaHasta: string;
  onFechaDesdeChange: (v: string) => void;
  onFechaHastaChange: (v: string) => void;
  distritoId: string;
  onDistritoIdChange: (v: string) => void;
  distritoOptions: { value: string; label: string }[];
  ejecucion: string;
  onEjecucionChange: (v: string) => void;
  origen: string;
  onOrigenChange: (v: string) => void;
  motivoNoRealizado: string;
  onMotivoNoRealizadoChange: (v: string) => void;
  realizadoTipoIniciador: string;
  onRealizadoTipoIniciadorChange: (v: string) => void;
  realizadoRubroId: string;
  onRealizadoRubroIdChange: (v: string) => void;
  rubroOptions: { value: string; label: string }[];
  inspectorId: string;
  onInspectorIdChange: (v: string) => void;
  inspectores: CatalogItem[];
  onAplicar: () => void;
  onRefrescar: () => void;
  onLimpiar: () => void;
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
  ejecucion,
  onEjecucionChange,
  origen,
  onOrigenChange,
  motivoNoRealizado,
  onMotivoNoRealizadoChange,
  realizadoTipoIniciador,
  onRealizadoTipoIniciadorChange,
  realizadoRubroId,
  onRealizadoRubroIdChange,
  rubroOptions,
  inspectorId,
  onInspectorIdChange,
  inspectores,
  onAplicar,
  onRefrescar,
  onLimpiar,
}: MapaFiltrosUnificadosProps) {
  const ejecucionOptions = MAPA_EJECUCION_OPTIONS.map((o) => ({ value: o.value, label: o.label }));
  const origenOptions = MAPA_ORIGEN_OPTIONS.map((o) => ({ value: o.value, label: o.label }));
  const motivoOptions = MAPA_MOTIVO_NO_REALIZADO_OPTIONS.map((o) => ({
    value: o.value,
    label: o.label,
  }));
  const tipoOptions = MAPA_TIPO_INICIADOR_OPTIONS.map((o) => ({ value: o.value, label: o.label }));
  const motivoDisabled = ejecucion === "REALIZADO";
  const tipoDisabled = ejecucion !== "REALIZADO";
  const inspectorOptions = [
    { value: "", label: "Todos los inspectores" },
    ...inspectores.map((i) => ({ value: String(i.id), label: i.nombre })),
  ];

  return (
    <Box sx={filtroContainerStyles} data-testid="mapa-realizados-filtros">
      <Box sx={filtroGridStyles}>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            label="Desde"
            type="date"
            value={fechaDesde}
            onChange={(e) => onFechaDesdeChange(e.target.value)}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppTextField
            appearance="dense"
            label="Hasta"
            type="date"
            value={fechaHasta}
            onChange={(e) => onFechaHastaChange(e.target.value)}
            InputLabelProps={{ shrink: true }}
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Ejecución"
            value={ejecucion}
            onChange={(e) => onEjecucionChange(String(e.target.value))}
            options={ejecucionOptions}
            data-testid="mapa-realizados-filtro-ejecucion"
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Origen"
            value={origen}
            onChange={(e) => onOrigenChange(String(e.target.value))}
            options={origenOptions}
            data-testid="mapa-realizados-filtro-origen"
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Motivo no realizado"
            value={motivoNoRealizado}
            onChange={(e) => onMotivoNoRealizadoChange(String(e.target.value))}
            options={motivoOptions}
            disabled={motivoDisabled}
            data-testid="mapa-realizados-filtro-motivo"
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Distrito"
            value={distritoId}
            onChange={(e) => onDistritoIdChange(String(e.target.value))}
            options={distritoOptions.map((o) => ({ value: o.value, label: o.label }))}
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Inspector"
            value={inspectorId}
            onChange={(e) => onInspectorIdChange(String(e.target.value))}
            options={inspectorOptions.map((o) => ({ value: o.value, label: o.label }))}
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Tipo"
            value={realizadoTipoIniciador}
            onChange={(e) => onRealizadoTipoIniciadorChange(String(e.target.value))}
            options={tipoOptions}
            disabled={tipoDisabled}
            data-testid="mapa-realizados-filtro-tipo"
            SelectProps={{ displayEmpty: false }}
            variant="outlined"
            fullWidth
          />
        </Box>
        <Box sx={filtroItemStyles}>
          <AppSelect
            appearance="dense"
            label="Rubro"
            value={realizadoRubroId}
            onChange={(e) => onRealizadoRubroIdChange(String(e.target.value))}
            options={rubroOptions}
            data-testid="mapa-realizados-filtro-rubro"
            variant="outlined"
            fullWidth
          />
        </Box>
      </Box>
      <Box sx={filtroButtonsStyles}>
        <AppButton dsVariant="primary" dsSize="sm" onClick={onAplicar} sx={filtroButtonPrimaryStyles}>
          Aplicar filtros
        </AppButton>
        <AppButton dsVariant="primary" dsSize="sm" onClick={onRefrescar} sx={filtroButtonPrimaryStyles}>
          Refrescar
        </AppButton>
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={onLimpiar}
          sx={filtroButtonPrimaryStyles}
          data-testid="mapa-realizados-limpiar-filtros"
        >
          Limpiar filtros
        </AppButton>
      </Box>
    </Box>
  );
}
