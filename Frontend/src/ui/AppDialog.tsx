import type { DialogProps } from "@mui/material/Dialog";
import Dialog from "@mui/material/Dialog";
import type { PaperProps } from "@mui/material/Paper";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import type { SxProps, Theme } from "@mui/material/styles";
import { useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";
import type { ReactNode, MouseEvent } from "react";

export type AppDialogTone = "default" | "danger";

export type AppDialogProps = Omit<DialogProps, "title"> & {
  title?: ReactNode;
  actions?: ReactNode;
  showCloseButton?: boolean;
  tone?: AppDialogTone;
  contentSx?: SxProps<Theme>;
  /** Activa bordes entre título / contenido / acciones (paridad con `DialogContent dividers` de MUI). */
  contentDividers?: boolean;
  paperSx?: SxProps<Theme>;
  /**
   * Cerrar desde el botón X. Si `showCloseButton` es true y esta prop falta, no se muestra la X
   * (evita usar `onClose` con razones que no aplican al click del botón).
   */
  onCloseButtonClick?: (event: MouseEvent<HTMLButtonElement>) => void;
};

/**
 * Diálogo del design system DIGITALIZA.
 *
 * Qué hace: Dialog + título + contenido + acciones. `onClose` sigue siendo el de MUI (backdrop/Escape).
 * El botón cerrar solo aparece si `showCloseButton` y `onCloseButtonClick` están definidos.
 */
export function AppDialog({
  title,
  children,
  actions,
  open,
  onClose,
  showCloseButton = true,
  tone = "default",
  maxWidth = "sm",
  fullWidth = true,
  scroll = "paper",
  contentSx,
  contentDividers,
  paperSx,
  onCloseButtonClick,
  slotProps,
  ...rest
}: AppDialogProps) {
  const theme = useTheme();

  const showHeaderClose = Boolean(showCloseButton && onCloseButtonClick);
  const showTitleRow = title != null || showHeaderClose;

  const userPaper = slotProps?.paper as PaperProps | undefined;
  const mergedPaperSlotProps: PaperProps = {
    ...userPaper,
    sx: [
      paperSx,
      ...(Array.isArray(userPaper?.sx) ? userPaper.sx : userPaper?.sx ? [userPaper.sx] : []),
    ],
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={maxWidth}
      fullWidth={fullWidth}
      scroll={scroll}
      slotProps={{
        ...slotProps,
        paper: mergedPaperSlotProps,
      }}
      {...rest}
    >
      {showTitleRow && (
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            pr: showHeaderClose ? 1 : 2,
            ...(tone === "danger" ? { color: theme.palette.error.main } : {}),
          }}
        >
          <span style={{ flex: 1 }}>{title ?? null}</span>
          {showHeaderClose && (
            <IconButton
              aria-label="Cerrar"
              onClick={onCloseButtonClick}
              edge="end"
              size="small"
            >
              <CloseIcon />
            </IconButton>
          )}
        </DialogTitle>
      )}
      <DialogContent dividers={Boolean(contentDividers)} sx={contentSx}>
        {children}
      </DialogContent>
      {actions != null && <DialogActions>{actions}</DialogActions>}
    </Dialog>
  );
}
