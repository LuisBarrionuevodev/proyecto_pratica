import { useState } from "react";
import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
} from "@mui/material";

import { AppButton } from "../../../ui";
import { planificacionTextFieldSx } from "../styles/institutionalVisual";
import type { UrgentesFiltrosAplicados } from "../types/planificacion.types";

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
 * Filtro compacto para bandeja urgentes (M3): tipo + búsqueda por botón.
 */
export function UrgentesFiltroPanel({ onFiltrar, onLimpiar, loading }: UrgentesFiltroPanelProps) {
  const [tipoUrgente, setTipoUrgente] = useState<UrgentesFiltrosAplicados["tipo_urgente"]>("");
  const [q, setQ] = useState("");

  const handleFiltrar = () => {
    onFiltrar({ tipo_urgente: tipoUrgente, q: q.trim() });
  };

  const handleLimpiar = () => {
    setTipoUrgente("");
    setQ("");
    onLimpiar();
  };

  return (
    <Stack spacing={1} sx={{ flexShrink: 0 }}>
      <FormControl size="small" fullWidth>
        <InputLabel id="urg-tipo-label" sx={{ fontFamily: '"Tactic Sans", sans-serif' }}>
          Tipo urgente
        </InputLabel>
        <Select
          labelId="urg-tipo-label"
          label="Tipo urgente"
          value={tipoUrgente}
          onChange={(e) => setTipoUrgente(e.target.value as UrgentesFiltrosAplicados["tipo_urgente"])}
          sx={{ fontFamily: '"Tactic Sans", sans-serif', borderRadius: "10px" }}
        >
          {TIPO_URGENTE_OPCIONES.map((o) => (
            <MenuItem key={o.value || "all"} value={o.value} sx={{ fontFamily: '"Tactic Sans", sans-serif' }}>
              {o.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <Stack direction="row" spacing={1} alignItems="flex-start">
        <TextField
          size="small"
          fullWidth
          placeholder="Nº acta, oficio, domicilio, rubro…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleFiltrar()}
          sx={planificacionTextFieldSx}
        />
        <AppButton dsVariant="primary" dsSize="sm" onClick={handleFiltrar} disabled={loading}>
          Buscar
        </AppButton>
        <AppButton dsVariant="ghost" dsSize="sm" onClick={handleLimpiar} disabled={loading}>
          Limpiar
        </AppButton>
      </Stack>
    </Stack>
  );
}
