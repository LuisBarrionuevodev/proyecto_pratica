import { Box, CircularProgress } from "@mui/material";

import { COLORS } from "../../Containers/Actuaciones/styles/actuacionesTableStyles";

/**
 * Spinner centrado para bandejas/tablas (misma referencia que Actuaciones).
 */
export function BandejaTableSpinner({ minHeight = 320 }: { minHeight?: number }) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight,
        width: "100%",
        py: 5,
      }}
    >
      <CircularProgress sx={{ color: COLORS.primary }} />
    </Box>
  );
}

/** Evita skeleton/progress bar de MRT; el spinner lo maneja `BandejaTableSpinner` a nivel vista. */
export const BANDEJA_MRT_SPINNER_LOADING_STATE = {
  isLoading: false,
  showProgressBars: false,
} as const;
