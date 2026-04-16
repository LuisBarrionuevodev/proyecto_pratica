import { Alert, Box, Chip, Stack, Typography } from "@mui/material";

import type { IJuzgadoCatalogItem } from "../../../api/actuacionesPendientesApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  docModalChipSx,
  docModalFooterButtonsSx,
  docModalFooterRowSx,
  docModalHeaderStackSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../../ui";
import {
  BloqueInspeccionBaseFromOficioRow,
  BloqueReferenciaComprobacionOficio,
  DOC_MODAL_BLOCK_STACK_SPACING,
  type ComprobacionOficioReferenciaRow,
} from "./comprobacionOperativoBlocks";

/** Fila oficio + campos opcionales de inspección si el backend los envía. */
export type OficioOperativoRow = ComprobacionOficioReferenciaRow & {
  acta_inspeccion_num?: string | null;
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  tipo_actuacion?: string | null;
};

function actaCabecera(row: OficioOperativoRow): string {
  const n = (row.acta_comprobacion_num ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

export type ComprobacionOficioOperativoDialogProps = {
  open: boolean;
  onClose: () => void;
  row: OficioOperativoRow | null;
  juzgados: IJuzgadoCatalogItem[];
  numeroOficio: string;
  onNumeroOficioChange: (v: string) => void;
  fechaOficio: string;
  onFechaOficioChange: (v: string) => void;
  juzgadoId: number | "";
  onJuzgadoIdChange: (v: number | "") => void;
  causa: string;
  onCausaChange: (v: string) => void;
  expNumero: string;
  onExpNumeroChange: (v: string) => void;
  expFecha: string;
  onExpFechaChange: (v: string) => void;
  modalApiError: string | null;
  saving: boolean;
  onGuardar: () => void | Promise<void>;
};

/**
 * Alta de oficio + expediente de respuesta: mismas cards que expediente + filas de envío en Referencia; formulario debajo.
 */
export function ComprobacionOficioOperativoDialog({
  open,
  onClose,
  row,
  juzgados,
  numeroOficio,
  onNumeroOficioChange,
  fechaOficio,
  onFechaOficioChange,
  juzgadoId,
  onJuzgadoIdChange,
  causa,
  onCausaChange,
  expNumero,
  onExpNumeroChange,
  expFecha,
  onExpFechaChange,
  modalApiError,
  saving,
  onGuardar,
}: ComprobacionOficioOperativoDialogProps) {
  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const titleNode =
    row != null ? (
      <Box sx={docModalHeaderStackSx}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Registrar oficio y expediente de respuesta
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaCabecera(row)}
        </Typography>
      </Box>
    ) : (
      "Oficio"
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
            <AppButton dsVariant="ghost" dsSize="sm" onClick={handleClose} disabled={saving}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" dsSize="sm" onClick={() => void onGuardar()} disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </AppButton>
          </Box>
        </Box>
      }
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <BloqueReferenciaComprobacionOficio row={row} />
          <BloqueInspeccionBaseFromOficioRow row={row} />
          {modalApiError ? (
            <Alert severity="error" sx={{ mb: 0 }}>
              {modalApiError}
            </Alert>
          ) : null}
          <AppTextField
            appearance="glass"
            label="Número de oficio"
            value={numeroOficio}
            onChange={(e) => onNumeroOficioChange(e.target.value)}
            fullWidth
            required
          />
          <AppTextField
            appearance="glass"
            label="Fecha de oficio"
            type="date"
            value={fechaOficio}
            onChange={(e) => onFechaOficioChange(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
            required
          />
          <AppSelect
            appearance="glass"
            label="Juzgado"
            value={juzgadoId === "" ? "" : String(juzgadoId)}
            onChange={(e) => onJuzgadoIdChange(e.target.value === "" ? "" : Number(e.target.value))}
            fullWidth
            required
            variant="outlined"
            options={[{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))]}
          />
          <AppTextField appearance="glass" label="Causa" value={causa} onChange={(e) => onCausaChange(e.target.value)} fullWidth />
          <AppTextField
            appearance="glass"
            label="Número expediente oficio (respuesta)"
            value={expNumero}
            onChange={(e) => onExpNumeroChange(e.target.value)}
            fullWidth
            required
          />
          <AppTextField
            appearance="glass"
            label="Fecha expediente oficio"
            type="date"
            value={expFecha}
            onChange={(e) => onExpFechaChange(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
            required
          />
        </Stack>
      )}
    </AppDialog>
  );
}
