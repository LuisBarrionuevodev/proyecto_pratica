import { Box, Typography } from "@mui/material";

import {
  crudFieldSlotLabelSx,
  crudReadonlyFieldShellSx,
  crudReadonlyFieldValueSx,
} from "../../styles/crudDialogTokens";

export const CRUD_FIELD_EMPTY = "—";

/** Normaliza valor de lectura; vacío → «—». */
export function formatCrudFieldValue(value: unknown, emptyFallback = CRUD_FIELD_EMPTY): string {
  if (value === null || value === undefined) return emptyFallback;
  const s = String(value).trim();
  return s === "" ? emptyFallback : s;
}

export type CrudFieldViewProps = {
  label: string;
  value: unknown;
  emptyFallback?: string;
};

/**
 * Campo readonly tipo input glass (label arriba + shell).
 * Preferir `CrudFormSlot` cuando haya par vista/edición en el mismo layout.
 */
export function CrudFieldView({ label, value, emptyFallback = CRUD_FIELD_EMPTY }: CrudFieldViewProps) {
  return (
    <Box sx={{ width: "100%" }}>
      <Typography component="label" sx={crudFieldSlotLabelSx}>
        {label}
      </Typography>
      <Box sx={crudReadonlyFieldShellSx}>
        <Typography variant="body2" sx={crudReadonlyFieldValueSx}>
          {formatCrudFieldValue(value, emptyFallback)}
        </Typography>
      </Box>
    </Box>
  );
}
