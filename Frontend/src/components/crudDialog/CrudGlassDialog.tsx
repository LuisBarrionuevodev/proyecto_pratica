import { createContext, useContext, useMemo, useRef, type ReactNode, type RefObject } from "react";
import type { DialogProps } from "@mui/material/Dialog";
import Box from "@mui/material/Box";
import type { SxProps, Theme } from "@mui/material/styles";

import { GLASS_COLORS } from "../../styles/GlassStyles";
import {
  crudDialogActionsSx,
  crudDialogContentSx,
  crudDialogFormFieldsSx,
  crudDialogHeaderSx,
  crudDialogPaperSx,
  crudDialogScrollbarSx,
} from "../../styles/crudDialogTokens";
import { AppDialog } from "../../ui/AppDialog";

type CrudDialogScrollContextValue = {
  contentRef: RefObject<HTMLDivElement | null>;
};

const CrudDialogScrollContext = createContext<CrudDialogScrollContextValue | null>(null);

/** Ref al contenedor scrolleable interno del modal CRUD (p. ej. para `CrudFormErrorSummary`). */
export function useCrudDialogScrollContainer(): RefObject<HTMLDivElement | null> | null {
  return useContext(CrudDialogScrollContext)?.contentRef ?? null;
}

export type CrudGlassDialogProps = Omit<DialogProps, "title"> & {
  open: boolean;
  onClose: DialogProps["onClose"];
  /** Cierre explícito desde botón X (requerido si `showCloseButton`). */
  onCloseButtonClick?: () => void;
  title?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  maxWidth?: DialogProps["maxWidth"];
  fullWidth?: boolean;
  contentSx?: SxProps<Theme>;
  showCloseButton?: boolean;
};

/**
 * Wrapper CRUD sobre `AppDialog`: paper glass oscuro, header azul dashboard, contenido scrolleable y pie sticky.
 */
export function CrudGlassDialog({
  open,
  onClose,
  onCloseButtonClick,
  title,
  actions,
  children,
  maxWidth = "md",
  fullWidth = true,
  contentSx,
  showCloseButton = true,
  ...rest
}: CrudGlassDialogProps) {
  const contentRef = useRef<HTMLDivElement | null>(null);
  const scrollCtx = useMemo(() => ({ contentRef }), []);

  const handleCloseButton = onCloseButtonClick ?? (() => onClose?.({}, "escapeKeyDown"));

  return (
    <CrudDialogScrollContext.Provider value={scrollCtx}>
      <AppDialog
        open={open}
        onClose={onClose}
        onCloseButtonClick={showCloseButton ? handleCloseButton : undefined}
        showCloseButton={showCloseButton}
        appearance="glass"
        title={title}
        titleSx={crudDialogHeaderSx}
        closeButtonOnPrimary
        actions={actions}
        actionsSx={crudDialogActionsSx}
        paperSx={crudDialogPaperSx}
        maxWidth={maxWidth}
        fullWidth={fullWidth}
        scroll="paper"
        contentDividers={false}
        contentSx={[
          crudDialogContentSx,
          {
            display: "flex",
            flexDirection: "column",
            p: 0,
            overflow: "hidden",
            backgroundColor: "transparent",
            borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
          },
          contentSx,
        ]}
        {...rest}
      >
        <Box
          ref={contentRef}
          sx={[
            crudDialogFormFieldsSx,
            crudDialogScrollbarSx,
            {
              flex: "1 1 auto",
              minHeight: 0,
              overflowY: "auto",
              px: { xs: 2, sm: 2.5 },
              py: 2,
              display: "flex",
              flexDirection: "column",
              gap: 0.5,
              width: "100%",
              boxSizing: "border-box",
              color: "#FFFFFF",
            },
          ]}
        >
          {children}
        </Box>
      </AppDialog>
    </CrudDialogScrollContext.Provider>
  );
}
