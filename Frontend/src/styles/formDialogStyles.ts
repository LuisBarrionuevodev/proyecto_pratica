import type { SxProps, Theme } from "@mui/material";

/**
 * Stack estándar para formularios dentro de `AppDialog` (glass): espaciado uniforme en todo el sistema.
 */
export const formDialogContentStackSx: SxProps<Theme> = {
  display: "flex",
  flexDirection: "column",
  gap: 2,
  pt: 1,
  width: "100%",
};
