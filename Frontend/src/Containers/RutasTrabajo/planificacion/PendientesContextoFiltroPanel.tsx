import { useState } from "react";
import { Stack, TextField } from "@mui/material";

import { AppButton } from "../../../ui";
import {
  filterCompactActionsSx,
  filterCompactPrimaryButtonSx,
  filterCompactSecondaryButtonSx,
} from "../../Actuaciones/styles/filtroStyles";
import { planificacionTextFieldSx } from "../styles/institutionalVisual";
import { PlanificacionRubroSelect } from "./components/PlanificacionRubroSelect";
import type { PlanificacionFiltrosLista } from "./types/planificacion.types";

export type PendientesContextoFiltroPanelProps = {
  onFiltrar: (filtros: PlanificacionFiltrosLista) => void;
  onLimpiar: () => void;
  loading?: boolean;
};

const FILTROS_VACIOS: PlanificacionFiltrosLista = {
  q: "",
  rubro_id: null,
};

/**
 * Filtro compacto para pendientes del contexto: rubro catálogo + domicilio.
 * Mismo layout/estilos que UrgentesFiltroPanel (STAB-10d).
 */
export function PendientesContextoFiltroPanel({
  onFiltrar,
  onLimpiar,
  loading,
}: PendientesContextoFiltroPanelProps) {
  const [q, setQ] = useState("");
  const [rubroId, setRubroId] = useState<number | null>(null);

  const handleFiltrar = () => {
    onFiltrar({
      q: q.trim(),
      rubro_id: rubroId,
    });
  };

  const handleLimpiar = () => {
    setQ("");
    setRubroId(null);
    onLimpiar();
  };

  return (
    <Stack spacing={1} sx={{ flexShrink: 0 }}>
      <PlanificacionRubroSelect value={rubroId} onChange={setRubroId} disabled={loading} />

      <TextField
        size="small"
        fullWidth
        label="Domicilio"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleFiltrar()}
        sx={planificacionTextFieldSx}
      />

      <Stack direction="row" spacing={1} alignItems="center" sx={filterCompactActionsSx}>
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

export { FILTROS_VACIOS as PENDIENTES_CONTEXTO_FILTROS_VACIOS };
