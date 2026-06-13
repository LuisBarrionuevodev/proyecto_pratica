import { useState } from "react";
import { Stack, TextField } from "@mui/material";

import { AppButton, AppSelect } from "../../../ui";
import {
  filterCompactActionsSx,
  filterCompactPrimaryButtonSx,
  filterCompactSecondaryButtonSx,
} from "../../Actuaciones/styles/filtroStyles";
import { PlanificacionRubroSelect } from "./components/PlanificacionRubroSelect";
import { planificacionFilterSelectSx, planificacionTextFieldSx } from "../styles/institutionalVisual";
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
 * Filtro compacto para bandeja urgentes (M3): tipo, rubro, identificador único y domicilio.
 * Busca solo por botón o Enter (STAB-10d).
 */
export function UrgentesFiltroPanel({ onFiltrar, onLimpiar, loading }: UrgentesFiltroPanelProps) {
  const [tipoUrgente, setTipoUrgente] = useState<UrgentesFiltrosAplicados["tipo_urgente"]>("");
  const [rubroId, setRubroId] = useState<number | null>(null);
  const [qIdentificador, setQIdentificador] = useState("");
  const [qDomicilio, setQDomicilio] = useState("");

  const handleFiltrar = () => {
    onFiltrar({
      tipo_urgente: tipoUrgente,
      rubro_id: rubroId,
      q_identificador: qIdentificador.trim(),
      q_domicilio: qDomicilio.trim(),
    });
  };

  const handleLimpiar = () => {
    setTipoUrgente("");
    setRubroId(null);
    setQIdentificador("");
    setQDomicilio("");
    onLimpiar();
  };

  return (
    <Stack spacing={1} sx={{ flexShrink: 0 }}>
      <AppSelect
        appearance="dense"
        size="small"
        fullWidth
        label="Tipo urgente"
        value={tipoUrgente}
        onChange={(e) => setTipoUrgente(e.target.value as UrgentesFiltrosAplicados["tipo_urgente"])}
        options={TIPO_URGENTE_OPCIONES.map((o) => ({ value: o.value, label: o.label }))}
        sx={planificacionFilterSelectSx}
      />

      <PlanificacionRubroSelect value={rubroId} onChange={setRubroId} disabled={loading} />

      <TextField
        size="small"
        fullWidth
        label="Nº oficio / comprobación / notificación"
        value={qIdentificador}
        onChange={(e) => setQIdentificador(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleFiltrar()}
        sx={planificacionTextFieldSx}
      />

      <TextField
        size="small"
        fullWidth
        label="Domicilio"
        value={qDomicilio}
        onChange={(e) => setQDomicilio(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleFiltrar()}
        sx={planificacionTextFieldSx}
      />

      <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end" sx={filterCompactActionsSx}>
        <AppButton
          dsVariant="ghost"
          dsSize="sm"
          onClick={handleLimpiar}
          disabled={loading}
          sx={filterCompactSecondaryButtonSx}
        >
          Limpiar
        </AppButton>
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={handleFiltrar}
          disabled={loading}
          sx={filterCompactPrimaryButtonSx}
        >
          Buscar
        </AppButton>
      </Stack>
    </Stack>
  );
}
