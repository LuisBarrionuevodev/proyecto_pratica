import { Box } from "@mui/material";
import type { ReactNode } from "react";

import { crudDialogActionsRowSx } from "../../styles/crudDialogTokens";
import { AppButton } from "../../ui/AppButton";

export type CrudDialogActionsProps = {
  mode: "view" | "edit" | "create";
  onEdit?: () => void;
  onSave?: () => void;
  onDelete?: () => void;
  loading?: boolean;
  canEdit?: boolean;
  showDelete?: boolean;
  editLabel?: string;
  saveLabel?: string;
  deleteLabel?: string;
  /** Acciones secundarias en la misma fila (p. ej. Imprimir). */
  extraActions?: ReactNode;
  /** @deprecated Cierre solo con la X del header. */
  onClose?: () => void;
  /** @deprecated */
  onCancel?: () => void;
  /** @deprecated */
  closeLabel?: string;
  /** @deprecated */
  cancelLabel?: string;
  /** @deprecated */
  hint?: React.ReactNode;
};

/**
 * Acciones estándar del modal CRUD en una sola fila horizontal.
 * Vista: Editar (+ extra). Edición/alta: Eliminar opcional + Guardar (+ extra). Sin Cancelar/Cerrar.
 */
export function CrudDialogActions({
  mode,
  onEdit,
  onSave,
  onDelete,
  loading = false,
  canEdit = true,
  showDelete = false,
  editLabel = "Editar",
  saveLabel = "Guardar cambios",
  deleteLabel = "Eliminar",
  extraActions,
}: CrudDialogActionsProps) {
  const busy = loading;

  return (
    <Box sx={crudDialogActionsRowSx}>
      {mode === "view" ? (
        canEdit && onEdit ? (
          <AppButton dsVariant="primary" dsSize="sm" onClick={onEdit} disabled={busy}>
            {editLabel}
          </AppButton>
        ) : null
      ) : (
        <>
          {showDelete && onDelete ? (
            <AppButton dsVariant="ghost" dsSize="sm" onClick={onDelete} disabled={busy}>
              {deleteLabel}
            </AppButton>
          ) : null}
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            onClick={() => onSave?.()}
            loading={busy}
            disabled={busy || !onSave}
          >
            {saveLabel}
          </AppButton>
        </>
      )}
      {extraActions}
    </Box>
  );
}
