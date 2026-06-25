import { Box, FormHelperText, Typography } from "@mui/material";
import type { ReactNode } from "react";
import type { SxProps, Theme } from "@mui/material/styles";

import {
  CRUD_FIELD_HELPER_MIN_HEIGHT_PX,
  crudDialogFormFieldsSx,
  crudFieldSlotLabelSx,
  crudReadonlyFieldShellSx,
  crudReadonlyFieldValueSx,
} from "../../styles/crudDialogTokens";
import { formatCrudFieldValue, CRUD_FIELD_EMPTY } from "./CrudFieldView";

export type CrudFormSlotProps = {
  label: string;
  mode: "view" | "edit";
  value?: unknown;
  required?: boolean;
  error?: boolean;
  helperText?: string;
  emptyFallback?: string;
  fullWidth?: boolean;
  sx?: SxProps<Theme>;
  children?: ReactNode;
};

const crudFormSlotRootSx: SxProps<Theme> = {
  width: "100%",
  boxSizing: "border-box",
};

/** Helper reservado (invisible en vista sin error) para igualar alto con edición. */
const crudFormSlotHelperReserveSx: SxProps<Theme> = {
  mx: 0,
  mt: "4px",
  minHeight: CRUD_FIELD_HELPER_MIN_HEIGHT_PX,
  lineHeight: 1.25,
};

/**
 * Celda de formulario CRUD: vista = label + shell readonly tipo input glass;
 * edición = control hijo (input/select) en el mismo lugar del layout.
 */
export function CrudFormSlot({
  label,
  mode,
  value,
  required = false,
  error = false,
  helperText,
  emptyFallback = CRUD_FIELD_EMPTY,
  fullWidth = true,
  sx,
  children,
}: CrudFormSlotProps) {
  const widthSx = fullWidth ? { width: "100%" } : undefined;

  if (mode === "edit" && children != null) {
    return (
      <Box sx={[crudFormSlotRootSx, widthSx, crudDialogFormFieldsSx, sx]}>{children}</Box>
    );
  }

  return (
    <Box sx={[crudFormSlotRootSx, widthSx, crudDialogFormFieldsSx, sx]}>
      <Typography component="label" sx={crudFieldSlotLabelSx}>
        {label}
        {required ? " *" : ""}
      </Typography>
      <Box sx={crudReadonlyFieldShellSx}>
        <Typography variant="body2" sx={crudReadonlyFieldValueSx}>
          {formatCrudFieldValue(value, emptyFallback)}
        </Typography>
      </Box>
      {helperText && error ? (
        <FormHelperText error sx={crudFormSlotHelperReserveSx}>
          {helperText}
        </FormHelperText>
      ) : (
        <FormHelperText aria-hidden sx={{ ...crudFormSlotHelperReserveSx, visibility: "hidden" }}>
          {" "}
        </FormHelperText>
      )}
    </Box>
  );
}

