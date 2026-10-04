import { Box } from "@mui/material";

import { AppButton } from "../../../ui/AppButton";
import { AppTextField } from "../../../ui/AppTextField";
import {
  filtroButtonPrimaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
} from "../../Actuaciones/styles/filtroStyles";

export type MapaFiltrosRangoFechasProps = {
  fechaDesde: string;
  fechaHasta: string;
  onFechaDesdeChange: (v: string) => void;
  onFechaHastaChange: (v: string) => void;
  onAplicar: () => void;
  onRefrescar: () => void;
  onLimpiar: () => void;
};

/** Filtros de mapa Inspector: solo rango Desde / Hasta. */
export function MapaFiltrosRangoFechas({
  fechaDesde,
  fechaHasta,
  onFechaDesdeChange,
  onFechaHastaChange,
  onAplicar,
  onRefrescar,
  onLimpiar,
}: MapaFiltrosRangoFechasProps) {
  return (
    <Box sx={filtroContainerStyles} data-testid="mapa-inspector-filtros-fechas">
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
      </Box>
      <Box sx={filtroButtonsStyles}>
        <AppButton dsVariant="primary" dsSize="sm" onClick={onAplicar} sx={filtroButtonPrimaryStyles}>
          Aplicar filtros
        </AppButton>
        <AppButton dsVariant="primary" dsSize="sm" onClick={onRefrescar} sx={filtroButtonPrimaryStyles}>
          Refrescar
        </AppButton>
        <AppButton dsVariant="primary" dsSize="sm" onClick={onLimpiar} sx={filtroButtonPrimaryStyles}>
          Limpiar filtros
        </AppButton>
      </Box>
    </Box>
  );
}
