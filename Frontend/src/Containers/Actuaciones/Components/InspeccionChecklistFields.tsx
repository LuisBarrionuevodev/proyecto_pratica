import { memo } from "react";
import { Box, Typography } from "@mui/material";

import type { ChecklistUxValue } from "../utils/inspeccionChecklistSubmit";
import {
  CODIGO_TIENE_BANO,
  CODIGO_TIENE_HABILITACION,
  displayChecklistEstadoBienButtonLabel,
  isValidActaInspeccionNum,
} from "../utils/inspeccionChecklistSubmit";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { InspeccionActaSegmentedRow } from "./InspeccionActaSegmentedRow";

export type InspeccionChecklistFieldsProps = {
  catalog: IItemActaInspeccionCatalogItem[];
  estados: Record<number, ChecklistUxValue>;
  onEstadosChange: (estados: Record<number, ChecklistUxValue>) => void;
  disabled?: boolean;
  /** Vista readonly: controles no editables pero con contraste pleno (sin atenuar). */
  readOnly?: boolean;
  errors?: {
    items?: string;
  };
  appearance?: "glass" | "default";
};

const ITEM_DISPLAY_NAMES: Record<string, string> = {
  TIENE_COCINA_MESA_TRABAJO: "Cocina / cuadra",
};

/** Nombre visible del ítem (override UX sin cambiar código de catálogo). */
export function displayItemNombre(item: IItemActaInspeccionCatalogItem): string {
  return ITEM_DISPLAY_NAMES[item.codigo] ?? item.nombre;
}

export const InspeccionChecklistFields = memo(function InspeccionChecklistFields({
  catalog,
  estados,
  onEstadosChange,
  disabled = false,
  readOnly = false,
  errors,
}: InspeccionChecklistFieldsProps) {
  const interactionDisabled = disabled || readOnly;
  const dimmed = disabled && !readOnly;

  const setEstado = (itemId: number, value: ChecklistUxValue | null) => {
    if (interactionDisabled) return;
    const next = { ...estados, [itemId]: value ?? "NONE" };
    onEstadosChange(next);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1,
        width: "100%",
        mt: 2,
        mb: 2,
        opacity: dimmed ? 0.72 : 1,
        transition: "opacity 0.15s ease",
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: GLASS_COLORS.textMuted,
          fontWeight: 600,
          letterSpacing: 0.4,
          textTransform: "uppercase",
          fontSize: "0.7rem",
        }}
      >
        Condiciones verificadas
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        {catalog.map((item) => {
          const current = estados[item.id] ?? "NONE";
          const isSiNo = item.tipo_respuesta === "SI_NO";
          const bienButtonLabel = displayChecklistEstadoBienButtonLabel(item.codigo);

          return (
            <InspeccionActaSegmentedRow
              key={item.id}
              label={`${displayItemNombre(item)}${item.codigo === CODIGO_TIENE_HABILITACION ? " *" : ""}`}
              value={current}
              onChange={(next) => setEstado(item.id, next as ChecklistUxValue)}
              disabled={disabled}
              readOnly={readOnly}
              options={
                isSiNo
                  ? [
                      { value: "NONE", label: "—", ariaLabel: "Ninguno" },
                      { value: "SI", label: "SÍ", ariaLabel: "Sí", minWidth: 44 },
                      { value: "NO", label: "NO", ariaLabel: "No", minWidth: 44 },
                    ]
                  : [
                      { value: "NONE", label: "—", ariaLabel: "Ninguno" },
                      {
                        value: "BIEN",
                        label: bienButtonLabel,
                        ariaLabel: bienButtonLabel,
                        minWidth: item.codigo === CODIGO_TIENE_BANO ? 118 : 52,
                      },
                      { value: "OBSERVADO", label: "OBSERVADO", ariaLabel: "Observado", minWidth: 88 },
                    ]
              }
            />
          );
        })}
      </Box>
      {errors?.items ? (
        <Typography variant="caption" color="error">
          {errors.items}
        </Typography>
      ) : null}
    </Box>
  );
});

export { isValidActaInspeccionNum };
