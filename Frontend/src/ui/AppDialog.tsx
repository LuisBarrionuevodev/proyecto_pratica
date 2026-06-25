import type { DialogProps } from "@mui/material/Dialog";
import Dialog from "@mui/material/Dialog";
import type { PaperProps } from "@mui/material/Paper";
import Box from "@mui/material/Box";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import type { SxProps, Theme } from "@mui/material/styles";
import { useTheme } from "@mui/material/styles";
import CloseIcon from "@mui/icons-material/Close";
import type { ReactNode, MouseEvent } from "react";

import {
  GLASS_COLORS,
  glassDialogActionsSx,
  glassDialogBackdropSx,
  glassDialogContentSx,
  glassDialogPaperSx,
  glassDialogTitleSx,
} from "../styles/GlassStyles";

export type AppDialogTone = "default" | "danger";

/** `glass`: panel institucional (default). `plain`: sin estilos glass extra (Paper MUI por defecto). */
export type AppDialogAppearance = "glass" | "plain";

export type AppDialogProps = Omit<DialogProps, "title"> & {
  title?: ReactNode;
  actions?: ReactNode;
  showCloseButton?: boolean;
  tone?: AppDialogTone;
  appearance?: AppDialogAppearance;
  contentSx?: SxProps<Theme>;
  /** Estilos extra para `DialogTitle` (p. ej. header CRUD azul). */
  titleSx?: SxProps<Theme>;
  /** Estilos extra para `DialogActions`. */
  actionsSx?: SxProps<Theme>;
  /** Botón X claro sobre header de color (p. ej. header CRUD azul). */
  closeButtonOnPrimary?: boolean;
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
  appearance = "glass",
  maxWidth = "sm",
  fullWidth = true,
  scroll = "paper",
  contentSx,
  titleSx: titleSxProp,
  actionsSx: actionsSxProp,
  closeButtonOnPrimary = false,
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
  const userBackdrop = slotProps?.backdrop as { sx?: SxProps<Theme> } | undefined;
  const glassPaperSx = appearance === "glass" ? glassDialogPaperSx : undefined;
  const mergedPaperSlotProps: PaperProps = {
    ...userPaper,
    sx: [
      glassPaperSx,
      paperSx,
      ...(Array.isArray(userPaper?.sx) ? userPaper.sx : userPaper?.sx ? [userPaper.sx] : []),
    ],
  };

  const mergedBackdrop = {
    ...userBackdrop,
    sx: [
      appearance === "glass" ? glassDialogBackdropSx : undefined,
      userBackdrop?.sx,
    ],
  };

  const titleSx: SxProps<Theme> = {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 1,
    pr: showHeaderClose ? 1 : 2,
    ...(appearance === "glass" ? glassDialogTitleSx : {}),
    ...(tone === "danger" ? { color: theme.palette.error.main } : {}),
    ...titleSxProp,
  };

  const dialogContentLayoutSx: SxProps<Theme> = {
    minWidth: 0,
    maxWidth: "100%",
    boxSizing: "border-box",
  };

  const glassDialogContentDividersSx: SxProps<Theme> | undefined =
    appearance === "glass" && contentDividers
      ? {
          borderTopColor: GLASS_COLORS.borderLight,
          borderBottomColor: GLASS_COLORS.borderLight,
        }
      : undefined;

  const mergedContentSx: SxProps<Theme> = [
    appearance === "glass" ? glassDialogContentSx : undefined,
    glassDialogContentDividersSx,
    dialogContentLayoutSx,
    contentSx,
  ];

  const mergedActionsSx: SxProps<Theme> = [
    appearance === "glass" ? glassDialogActionsSx : undefined,
    actionsSxProp,
  ];

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
        backdrop: mergedBackdrop,
      }}
      {...rest}
    >
      {showTitleRow && (
        <DialogTitle sx={titleSx}>
          <Box component="span" sx={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
            {title ?? null}
          </Box>
          {showHeaderClose && (
            <IconButton
              aria-label="Cerrar"
              onClick={onCloseButtonClick}
              edge="end"
              size="small"
              sx={
                appearance === "glass"
                  ? closeButtonOnPrimary
                    ? {
                        color: "rgba(255,255,255,0.85)",
                        "&:hover": { color: "#ffffff", backgroundColor: "rgba(255,255,255,0.12)" },
                      }
                    : { color: "rgba(255,255,255,0.75)", "&:hover": { color: theme.palette.primary.main } }
                  : undefined
              }
            >
              <CloseIcon />
            </IconButton>
          )}
        </DialogTitle>
      )}
      <DialogContent dividers={Boolean(contentDividers)} sx={mergedContentSx}>
        {children}
      </DialogContent>
      {actions != null && <DialogActions sx={mergedActionsSx}>{actions}</DialogActions>}
    </Dialog>
  );
}
