import { useEffect, useMemo, useState } from "react";

import type { IRubroCatalogItem } from "../../../../api/rubrosCatalogApi";
import { AppSelect } from "../../../../ui";
import { fetchRubrosCatalogoCached } from "../../../../utils/rubrosCatalogCache";
import { planificacionFilterSelectSx } from "../../styles/institutionalVisual";

export type PlanificacionRubroSelectProps = {
  value: number | null;
  onChange: (rubroId: number | null) => void;
  label?: string;
  disabled?: boolean;
};

/**
 * Select de rubro desde catálogo STAB-8 (nombre visible, id interno).
 */
export function PlanificacionRubroSelect({
  value,
  onChange,
  label = "Rubro",
  disabled,
}: PlanificacionRubroSelectProps) {
  const [items, setItems] = useState<IRubroCatalogItem[]>([]);

  useEffect(() => {
    let cancel = false;
    void fetchRubrosCatalogoCached()
      .then((list) => {
        if (!cancel) setItems(list);
      })
      .catch(() => {
        if (!cancel) setItems([]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  const options = useMemo(
    () => [
      { value: "", label: "Todos los rubros" },
      ...items
        .filter((r) => (r.nombre ?? "").trim())
        .map((r) => ({ value: String(r.id), label: r.nombre })),
    ],
    [items]
  );

  return (
    <AppSelect
      appearance="dense"
      size="small"
      fullWidth
      label={label}
      disabled={disabled}
      value={value == null ? "" : String(value)}
      onChange={(e) => {
        const raw = String(e.target.value);
        onChange(raw === "" ? null : Number(raw));
      }}
      options={options}
      sx={planificacionFilterSelectSx}
    />
  );
}
