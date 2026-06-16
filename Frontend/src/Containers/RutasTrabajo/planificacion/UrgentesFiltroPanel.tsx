import { useState } from "react";
import { Stack, TextField, Typography } from "@mui/material";

import { AppButton, AppSelect } from "../../../ui";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  filterCompactActionsSx,
  filterCompactPrimaryButtonSx,
  filterCompactSecondaryButtonSx,
} from "../../Actuaciones/styles/filtroStyles";
import { PlanificacionRubroSelect } from "./components/PlanificacionRubroSelect";
import { planificacionFilterSelectSx, planificacionTextFieldSx } from "../styles/institutionalVisual";
import type { UrgentesFiltrosAplicados } from "./types/planificacion.types";

const tactic = '"Tactic Sans", sans-serif' as const;

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
      <Typography
        sx={{
          fontFamily: tactic,
          fontSize: "0.6875rem",
          lineHeight: 1.35,
          color: GLASS_COLORS.textMuted,
        }}
      >
        Filtros sobre urgentes globales. Usá Buscar o Enter; Limpiar restaura la bandeja completa.
      </Typography>

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
        placeholder="Ej. 204, 456/2026 o nº notificación"
        value={qIdentificador}
        onChange={(e) => setQIdentificador(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleFiltrar()}
        sx={planificacionTextFieldSx}
      />

      <TextField
        size="small"
        fullWidth
        label="Domicilio"
        placeholder="Calle, número o texto del domicilio"
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
          title="Quitar filtros y volver a urgentes globales"
        >
          Limpiar
        </AppButton>
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={handleFiltrar}
          disabled={loading}
          sx={filterCompactPrimaryButtonSx}
          title="Aplicar filtros (también con Enter en los campos de texto)"
        >
          Buscar
        </AppButton>
      </Stack>
    </Stack>
  );
}
