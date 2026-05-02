import { Alert, Stack, Typography } from "@mui/material";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { DocumentalModalFooter, DocumentalModalTitleStack } from "../../../components/documental/DocumentalModalChrome";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { documentalGlassAlertSx } from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog, AppTextField } from "../../../ui";
import {
  BloqueInspeccionBaseComprobacion,
  BloqueReferenciaComprobacionExpediente,
  DOC_MODAL_BLOCK_STACK_SPACING,
  DocumentalBloque,
} from "./comprobacionOperativoBlocks";

function actaComprobacionCabecera(row: IActuacionesPendientesItem): string {
  const n = (row.acta_comprobacion_num ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

export type ComprobacionExpedienteOperativoDialogProps = {
  open: boolean;
  onClose: () => void;
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
  row,
  expNumero,
  onExpNumeroChange,
  expFecha,
  onExpFechaChange,
  modalApiError,
  saving,
  onGuardar,
}: ComprobacionExpedienteOperativoDialogProps) {
  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const titleNode =
    row != null ? (
      <DocumentalModalTitleStack
        dominioChip="Comprobación"
        titulo="Registrar expediente de envío"
        subtitulo={actaComprobacionCabecera(row)}
        actuacionId={row.id}
      />
    ) : (
      "Expediente de comprobación"
    );

  return (
    <AppDialog
      open={open}
      onClose={handleClose}
      onCloseButtonClick={handleClose}
      title={titleNode}
      fullWidth
      maxWidth="md"
      appearance="glass"
      contentDividers
      contentSx={{ ...formDialogContentStackSx, pt: 2, pb: 2 }}
      showCloseButton
      actions={<DocumentalModalFooter onCerrar={handleClose} cerrarDisabled={saving} />}
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <BloqueReferenciaComprobacionExpediente row={row} />
          <BloqueInspeccionBaseComprobacion row={row} />
          <DocumentalBloque overline="Alta de expediente de envío">
            <Stack spacing={2}>
              {modalApiError ? (
                <Alert severity="error" sx={{ mb: 0, ...documentalGlassAlertSx }}>
                  <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                    No se pudo guardar
                  </Typography>
                  <Typography variant="body2">{modalApiError}</Typography>
                </Alert>
              ) : null}
              <AppTextField
                appearance="glass"
                label="Número de expediente"
                value={expNumero}
                onChange={(e) => onExpNumeroChange(e.target.value)}
                fullWidth
                required
              />
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
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ pt: 0.5 }}>
                <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onGuardar()} disabled={saving}>
                  {saving ? "Guardando…" : "Guardar expediente"}
                </AppButton>
              </Stack>
            </Stack>
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
