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

/** Fila de acciones alineada a la derecha (Cancelar / Primario / secundarios). */
export const dialogFormActionsRowSx: SxProps<Theme> = {
  display: "flex",
  gap: 1.5,
  justifyContent: "flex-end",
  alignItems: "center",
  flexWrap: "wrap",
  width: "100%",
};

/** Grid responsive habitual en modales de formulario (1 / 2 / 3 columnas). */
export const dialogFormGridSx: SxProps<Theme> = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
  gap: 2,
  width: "100%",
};

/**
 * Contenido de diálogo “corto”: evita que `DialogContent` crezca con flex (scroll=paper)
 * y muestre barra de scroll innecesaria cuando el formulario cabe en pantalla.
 */
export const formDialogShortContentSx: SxProps<Theme> = {
  ...formDialogContentStackSx,
  flex: "0 1 auto",
  overflowY: "visible",
};
