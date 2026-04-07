import type { ReactNode } from "react";
import type { DialogProps } from "@mui/material/Dialog";
import { Box, Typography } from "@mui/material";

import {
  dialogFormActionsRowSx,
  formDialogShortContentSx,
} from "../styles/formDialogStyles";
import { AppButton } from "./AppButton";
import { AppDialog } from "./AppDialog";

export type ConfirmDialogProps = {
  open: boolean;
  /** Cierra sin confirmar (backdrop, Escape, X, Cancelar). No llamar desde `onConfirm` salvo que el padre controle el cierre. */
  onClose: () => void;
  /** Ejecutado al pulsar la acción principal. El padre puede ser async; `loading` lo controla el padre. */
  onConfirm: () => void | Promise<void>;

  title: ReactNode;
  /** Texto o contenido bajo el título (opcional). */
  children?: ReactNode;

  confirmLabel?: string;
  cancelLabel?: string;

  /** Usa `tone="danger"` en `AppDialog` y botón de confirmación destructivo. */
  destructive?: boolean;

  /** Deshabilita el botón de confirmación (además de cuando `loading` es true). */
  confirmDisabled?: boolean;

  /** Controlado por el padre (p. ej. `saving` durante API). Deshabilita acciones y bloquea cierre por backdrop/Escape/X. */
  loading?: boolean;

  maxWidth?: DialogProps["maxWidth"];
  fullWidth?: DialogProps["fullWidth"];
};

/**
 * Confirmación reutilizable sobre `AppDialog` (Digitaliza glass).
 * No gestiona loading internamente: el padre pasa `loading` mientras `onConfirm` deja trabajo async en curso.
 */
export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  children,
  confirmLabel,
  cancelLabel = "Cancelar",
  destructive = false,
  confirmDisabled = false,
  loading = false,
  maxWidth = "xs",
  fullWidth = true,
}: ConfirmDialogProps) {
  const resolvedConfirmLabel = confirmLabel ?? (destructive ? "Eliminar" : "Confirmar");
  const blockClose = loading;

  const handleDialogClose: DialogProps["onClose"] = (_event, _reason) => {
    if (blockClose) return;
    onClose();
  };

  const handleCloseButton = () => {
    if (blockClose) return;
    onClose();
  };

  const handleConfirm = () => {
    if (loading || confirmDisabled) return;
    void onConfirm();
  };

  return (
    <AppDialog
      open={open}
      onClose={handleDialogClose}
      onCloseButtonClick={handleCloseButton}
      title={title}
      tone={destructive ? "danger" : "default"}
      maxWidth={maxWidth}
      fullWidth={fullWidth}
      contentDividers
      contentSx={formDialogShortContentSx}
      showCloseButton
      disableEscapeKeyDown={blockClose}
      disableBackdropClick={blockClose}
      actions={
        <Box sx={dialogFormActionsRowSx}>
          <AppButton dsVariant="ghost" onClick={handleCloseButton} disabled={loading}>
            {cancelLabel}
          </AppButton>
          <AppButton
            dsVariant={destructive ? "danger" : "primary"}
            onClick={handleConfirm}
            disabled={loading || confirmDisabled}
            loading={loading}
          >
            {resolvedConfirmLabel}
          </AppButton>
        </Box>
      }
    >
      {children != null ? (
        typeof children === "string" ? (
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.85)", fontFamily: '"Tactic Sans", sans-serif' }}>
            {children}
          </Typography>
        ) : (
          children
        )
      ) : null}
    </AppDialog>
  );
}
