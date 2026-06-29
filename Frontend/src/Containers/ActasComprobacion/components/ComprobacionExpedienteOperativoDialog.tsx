import { Stack } from "@mui/material";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudFormSlot,
  CrudGlassDialog,
  useNotifyModalApiError,
} from "../../../components/crudDialog";
import { DocumentalCrudSection } from "../../../components/documental/documentalCrudLayout";
import { AppTextField } from "../../../ui";
import {
  BloqueInspeccionBaseComprobacion,
  BloqueReferenciaComprobacionExpediente,
  DOC_MODAL_BLOCK_STACK_SPACING,
} from "./comprobacionOperativoBlocks";

function actaComprobacionSubtitulo(row: IActuacionesPendientesItem): string {
  const n = (row.acta_comprobacion_num ?? "").trim();
  const acta = n ? `Acta N.º ${n}` : null;
  const fecha = (row.fecha_actuacion ?? "").trim();
  const fechaPart = fecha ? `Fecha: ${fecha}` : null;
  const parts = [acta, fechaPart].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Registrar expediente de envío";
}

export type ComprobacionExpedienteOperativoDialogProps = {
  open: boolean;
  onClose: () => void;
  disablePortal?: boolean;
  row: IActuacionesPendientesItem | null;
  expNumero: string;
  onExpNumeroChange: (v: string) => void;
  expFecha: string;
  onExpFechaChange: (v: string) => void;
  modalApiError: string | null;
  saving: boolean;
  onGuardar: () => void | Promise<void>;
};

/**
 * Alta de expediente de envío (comprobación): Referencia, visita y carga en card de acción.
 */
export function ComprobacionExpedienteOperativoDialog({
  open,
  onClose,
  disablePortal,
  row,
  expNumero,
  onExpNumeroChange,
  expFecha,
  onExpFechaChange,
  modalApiError,
  saving,
  onGuardar,
}: ComprobacionExpedienteOperativoDialogProps) {
  useNotifyModalApiError(modalApiError, open);

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      title={
        <CrudDialogHeader
          domainChip="Comprobación"
          titulo="Expediente"
          subtitulo={row != null ? actaComprobacionSubtitulo(row) : "Registrar expediente de envío"}
        />
      }
      actions={
        row != null ? (
          <CrudDialogActions
            mode="edit"
            onSave={() => void onGuardar()}
            loading={saving}
            saveLabel="Guardar expediente"
          />
        ) : undefined
      }
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <BloqueReferenciaComprobacionExpediente row={row} />
          <BloqueInspeccionBaseComprobacion row={row} />
          <DocumentalCrudSection title="Expediente de envío">
            <CrudFormSlot label="Número de expediente" mode="edit" required>
              <AppTextField
                appearance="glass"
                label="Número de expediente"
                value={expNumero}
                onChange={(e) => onExpNumeroChange(e.target.value)}
                fullWidth
                required
              />
            </CrudFormSlot>
            <CrudFormSlot label="Fecha de expediente" mode="edit" required>
              <AppTextField
                appearance="glass"
                label="Fecha de expediente"
                type="date"
                value={expFecha}
                onChange={(e) => onExpFechaChange(e.target.value)}
                InputLabelProps={{ shrink: true }}
                fullWidth
                required
              />
            </CrudFormSlot>
          </DocumentalCrudSection>
        </Stack>
      )}
    </CrudGlassDialog>
  );
}
