import { memo } from "react";
import { Box, ToggleButton, ToggleButtonGroup, Typography, useTheme } from "@mui/material";

import type { ChecklistUxValue } from "../utils/inspeccionChecklistSubmit";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";

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

function isValidActaInspeccionNum(value: string | null | undefined): boolean {
  const t = String(value ?? "").trim();
  return t.length > 0 && /^\d+$/.test(t);
}

export const InspeccionChecklistFields = memo(function InspeccionChecklistFields({
  catalog,
  estados,
  onEstadosChange,
  disabled = false,
  readOnly = false,
  errors,
}: InspeccionChecklistFieldsProps) {
  const theme = useTheme();
  const white = theme.palette.common.white;
  const interactionDisabled = disabled || readOnly;
  const dimmed = disabled && !readOnly;

  const setEstado = (itemId: number, value: ChecklistUxValue | null) => {
    if (interactionDisabled) return;
    const next = { ...estados, [itemId]: value ?? "NONE" };
    onEstadosChange(next);
  };

  const toggleSx = {
    color: white,
    borderColor: "rgba(255,255,255,0.35)",
    fontSize: "0.75rem",
    fontWeight: 500,
    letterSpacing: 0.2,
    px: 1.25,
    py: 0.5,
    minWidth: 52,
    whiteSpace: "nowrap",
    "&.Mui-selected": {
      color: white,
      backgroundColor: "rgba(255,255,255,0.18)",
      borderColor: "rgba(255,255,255,0.5)",
    },
    "&.Mui-selected:hover": {
      backgroundColor: "rgba(255,255,255,0.22)",
    },
    "&.Mui-disabled": {
      color: white,
      opacity: readOnly ? 1 : 0.55,
      borderColor: readOnly ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.2)",
    },
  } as const;

  const observadoToggleSx = {
    ...toggleSx,
    minWidth: 88,
  } as const;

  const siNoToggleSx = {
    ...toggleSx,
    minWidth: 44,
  } as const;

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
          color: white,
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

          return (
            <Box
              key={item.id}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 2,
                width: "100%",
                flexWrap: { xs: "wrap", sm: "nowrap" },
              }}
            >
              <Typography
                sx={{
                  color: white,
                  fontSize: "0.9rem",
                  fontWeight: 400,
                  flex: { xs: "1 1 100%", sm: "0 0 auto" },
                  minWidth: { sm: 150 },
                  maxWidth: { sm: 180 },
                }}
              >
                {displayItemNombre(item)}
              </Typography>
              {isSiNo ? (
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  disabled={interactionDisabled}
                  value={current}
                  onChange={(_, value: ChecklistUxValue | null) => {
                    if (value) setEstado(item.id, value);
                  }}
                  sx={{
                    flexShrink: 0,
                    flex: { xs: "1 1 100%", sm: "0 1 auto" },
                    justifyContent: { xs: "flex-start", sm: "flex-end" },
                    "& .MuiToggleButtonGroup-grouped": {
                      height: 32,
                    },
                  }}
                >
                  <ToggleButton value="NONE" sx={toggleSx} aria-label="Ninguno">
                    —
                  </ToggleButton>
                  <ToggleButton value="SI" sx={siNoToggleSx} aria-label="Sí">
                    SÍ
                  </ToggleButton>
                  <ToggleButton value="NO" sx={siNoToggleSx} aria-label="No">
                    NO
                  </ToggleButton>
                </ToggleButtonGroup>
              ) : (
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  disabled={interactionDisabled}
                  value={current}
                  onChange={(_, value: ChecklistUxValue | null) => {
                    if (value) setEstado(item.id, value);
                  }}
                  sx={{
                    flexShrink: 0,
                    flex: { xs: "1 1 100%", sm: "0 1 auto" },
                    justifyContent: { xs: "flex-start", sm: "flex-end" },
                    "& .MuiToggleButtonGroup-grouped": {
                      height: 32,
                    },
                  }}
                >
                  <ToggleButton value="NONE" sx={toggleSx} aria-label="Ninguno">
                    —
                  </ToggleButton>
                  <ToggleButton value="BIEN" sx={toggleSx} aria-label="Bien">
                    BIEN
                  </ToggleButton>
                  <ToggleButton value="OBSERVADO" sx={observadoToggleSx} aria-label="Observado">
                    OBSERVADO
                  </ToggleButton>
                </ToggleButtonGroup>
              )}
            </Box>
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
