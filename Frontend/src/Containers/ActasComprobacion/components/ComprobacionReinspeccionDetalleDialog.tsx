import { Box, Chip, Stack, Typography } from "@mui/material";

import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  docModalChipSx,
  docModalFooterButtonsSx,
  docModalFooterHintSx,
  docModalFooterRowSx,
  docModalHeaderStackSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog } from "../../../ui";
import {
  BloqueInspeccionBaseComprobacion,
  BloqueReferenciaYTramitesReinspeccion,
  DOC_MODAL_BLOCK_STACK_SPACING,
  type ReinspeccionOperativoDetalleRow,
  DocumentalBloque,
  DocumentalFila,
  textoValor,
} from "./comprobacionOperativoBlocks";

function actaCabecera(row: ReinspeccionOperativoDetalleRow): string {
  const n = (row.acta_comprobacion_num ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

export type ComprobacionReinspeccionDetalleDialogProps = {
  open: boolean;
  onClose: () => void;
  row: ReinspeccionOperativoDetalleRow | null;
};

/**
 * Vista consultiva de pendiente de reinspección por oficio: mismas cards que operativo + iniciador.
 */
export function ComprobacionReinspeccionDetalleDialog({ open, onClose, row }: ComprobacionReinspeccionDetalleDialogProps) {
  const titleNode =
    row != null ? (
      <Box sx={docModalHeaderStackSx}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Detalle — reinspección por oficio
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaCabecera(row)}
        </Typography>
      </Box>
    ) : (
      "Reinspección"
    );

  return (
    <AppDialog
      open={open}
      onClose={onClose}
      onCloseButtonClick={onClose}
      title={titleNode}
      fullWidth
      maxWidth="md"
      appearance="glass"
      contentDividers
      contentSx={{ ...formDialogContentStackSx, pt: 2, pb: 2 }}
      showCloseButton
      actions={
        <Box sx={docModalFooterRowSx}>
          <Typography variant="caption" component="div" sx={docModalFooterHintSx}>
            Vista solo consulta. Los valores de expediente/oficio completos dependen del DTO de la bandeja.
          </Typography>
          <Box sx={docModalFooterButtonsSx}>
            <AppButton dsVariant="primary" dsSize="sm" onClick={onClose}>
              Cerrar
            </AppButton>
          </Box>
        </Box>
      }
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <BloqueReferenciaYTramitesReinspeccion row={row} />
          <BloqueInspeccionBaseComprobacion
            row={{
              acta_inspeccion_num: row.acta_inspeccion_num ?? null,
              inspectores_texto: row.inspectores_texto ?? null,
              inspector1: row.inspector1 ?? null,
              inspector2: row.inspector2 ?? null,
              inspector3: row.inspector3 ?? null,
              orden_trabajo_numero: row.orden_trabajo_numero ?? null,
              tipo_actuacion: row.tipo_actuacion ?? null,
            }}
          />
          <DocumentalBloque
            overline="Iniciador (reinspección)"
            resumen="Estado operativo del iniciador de reinspección por oficio."
          >
            <DocumentalFila etiqueta="Estado del iniciador" valor={textoValor(row.estado_iniciador)} />
            <DocumentalFila etiqueta="Tipo de iniciador" valor={textoValor(row.tipo_iniciador)} />
            <DocumentalFila etiqueta="Fecha de origen" valor={textoValor(row.fecha_origen_iniciador)} />
            <DocumentalFila etiqueta="Iniciador (id)" valor={row.iniciador_id != null ? `#${row.iniciador_id}` : "—"} />
            <DocumentalFila etiqueta="Documento / estado" valor={textoValor(row.documento_pendiente)} />
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
