import { Alert, Box, Chip, Stack, Typography } from "@mui/material";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  docModalChipSx,
  docModalFooterButtonsSx,
  docModalFooterRowSx,
  docModalHeaderStackSx,
  docModalReferenceSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
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
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Registrar expediente de envío
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaComprobacionCabecera(row)}
        </Typography>
        <Typography variant="caption" component="div" sx={{ ...docModalReferenceSx, maxWidth: "100%" }}>
          Actuación #{row.id}
        </Typography>
      </Box>
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
      actions={
        <Box sx={docModalFooterRowSx}>
          <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
          <Box sx={docModalFooterButtonsSx}>
            <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose} disabled={saving}>
              Cerrar
            </AppButton>
          </Box>
        </Box>
      }
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <BloqueReferenciaComprobacionExpediente row={row} />
          <BloqueInspeccionBaseComprobacion row={row} />
          <DocumentalBloque overline="Alta de expediente de envío">
            <Stack spacing={2}>
              {modalApiError ? (
                <Alert severity="error" sx={{ mb: 0 }}>
                  {modalApiError}
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
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", pt: 0.5 }}>
                <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onGuardar()} disabled={saving}>
                  {saving ? "Guardando…" : "Guardar expediente"}
                </AppButton>
              </Box>
            </Stack>
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
