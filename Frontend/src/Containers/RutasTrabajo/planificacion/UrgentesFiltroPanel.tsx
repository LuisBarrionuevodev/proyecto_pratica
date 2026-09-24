import { useState } from "react";
import { Stack, TextField } from "@mui/material";

import { AppButton, AppSelect } from "../../../ui";
import {
  filterCompactPrimaryButtonSx,
  filterCompactSecondaryButtonSx,
} from "../../Actuaciones/styles/filtroStyles";
import {
  planificacionFilterSelectSx,
  planificacionTextFieldSx,
  planificacionUrgentesFiltrosSx,
} from "../styles/institutionalVisual";
import type { UrgentesFiltrosAplicados } from "./types/planificacion.types";

const TIPO_URGENTE_OPCIONES: { value: UrgentesFiltrosAplicados["tipo_urgente"]; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "DENUNCIA", label: "Denuncia" },
  { value: "NOTIFICACION", label: "Notificación" },
  { value: "OFICIO", label: "Oficio" },
];

export type UrgentesFiltroPanelProps = {
  onFiltrar: (filtros: UrgentesFiltrosAplicados) => void;
  onLimpiar: () => void;
  loading?: boolean;
};

/**
 * Filtros compactos M3: tipo + domicilio en una fila. Busca por botón o Enter.
 * Rubro / identificador no se muestran (reservados para futuro “Más filtros”).
 */
export function UrgentesFiltroPanel({ onFiltrar, onLimpiar, loading }: UrgentesFiltroPanelProps) {
  const [tipoUrgente, setTipoUrgente] = useState<UrgentesFiltrosAplicados["tipo_urgente"]>("");
  const [qDomicilio, setQDomicilio] = useState("");

  const handleFiltrar = () => {
    onFiltrar({
      tipo_urgente: tipoUrgente,
      rubro_id: null,
      q_identificador: "",
      q_domicilio: qDomicilio.trim(),
    });
  };

  const handleLimpiar = () => {
    setTipoUrgente("");
    setQDomicilio("");
    onLimpiar();
  };

  return (
    <Stack
      direction="row"
      spacing={0.75}
      alignItems="flex-end"
      flexWrap="wrap"
      useFlexGap
      sx={planificacionUrgentesFiltrosSx}
    >
      <AppSelect
        appearance="dense"
        size="small"
        label="Tipo urgente"
        value={tipoUrgente}
        onChange={(e) => setTipoUrgente(e.target.value as UrgentesFiltrosAplicados["tipo_urgente"])}
        options={TIPO_URGENTE_OPCIONES.map((o) => ({ value: o.value, label: o.label }))}
        sx={{
          ...planificacionFilterSelectSx,
          width: { xs: "100%", sm: 200 },
          minWidth: { sm: 180 },
          maxWidth: { sm: 220 },
        }}
      />

      <TextField
        size="small"
        label="Domicilio"
        placeholder="Calle o número"
        value={qDomicilio}
        onChange={(e) => setQDomicilio(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleFiltrar()}
        disabled={loading}
        sx={{
          ...planificacionTextFieldSx,
          flex: "1 1 8rem",
          minWidth: { xs: "100%", sm: 120 },
        }}
      />

      <Stack direction="row" spacing={0.5} sx={{ flexShrink: 0, ml: { sm: "auto" } }}>
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          onClick={handleLimpiar}
          disabled={loading}
          sx={{ ...filterCompactSecondaryButtonSx, minWidth: 90 }}
        >
          Limpiar
        </AppButton>
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={handleFiltrar}
          disabled={loading}
          sx={{ ...filterCompactPrimaryButtonSx, minWidth: 90 }}
        >
          Buscar
        </AppButton>
      </Stack>
    </Stack>
  );
}
