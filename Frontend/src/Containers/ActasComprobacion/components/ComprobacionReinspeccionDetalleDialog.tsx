import { useCallback, useEffect, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

import {
  fetchComprobacionDocumental,
  type IComprobacionDocumentalResponse,
  type IJuzgadoCatalogItem,
} from "../../../api/actuacionesPendientesApi";
import { DocumentalModalFooter, DocumentalModalTitleStack } from "../../../components/documental/DocumentalModalChrome";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { documentalGlassAlertSx } from "../../../styles/documentalModalTokens";
import { AppDialog } from "../../../ui";
import { OperativoOficioYRespuestaEditable } from "./ComprobacionOficioOperativoDialog";
import { DOC_MODAL_BLOCK_STACK_SPACING, type ReinspeccionOperativoDetalleRow } from "./comprobacionOperativoBlocks";
import { ReinspeccionDocumentalSharedLayout } from "./ReinspeccionDocumentalSharedLayout";

function actaCabecera(row: ReinspeccionOperativoDetalleRow): string {
  const n = (row.acta_comprobacion_num ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

export type ComprobacionReinspeccionDetalleDialogProps = {
  open: boolean;
  onClose: () => void;
  row: ReinspeccionOperativoDetalleRow | null;
  juzgados: IJuzgadoCatalogItem[];
  /** Tras guardar o recargar documental: refrescar bandejas (p. ej. `loadRein`). */
  onBandejasActualizadas: () => Promise<void>;
};

/**
 * Pendiente de reinspección por oficio: bloques consultivos + edición de oficio/causa/expediente de respuesta
 * (mismo componente que «Pendientes de oficio» cuando el oficio ya está cargado).
 */
export function ComprobacionReinspeccionDetalleDialog({
  open,
  onClose,
  row,
  juzgados,
  onBandejasActualizadas,
}: ComprobacionReinspeccionDetalleDialogProps) {
  const [documental, setDocumental] = useState<IComprobacionDocumentalResponse | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const recargarDocumental = useCallback(async () => {
    if (!row) return;
    setDocLoading(true);
    setDocError(null);
    try {
      const doc = await fetchComprobacionDocumental(row.id);
      setDocumental(doc);
    } catch (err: unknown) {
      setDocumental(null);
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setDocError(
        (typeof detail === "string" && detail.trim()) ||
          "No se pudo cargar la ficha documental para editar oficio y expediente de respuesta."
      );
    } finally {
      setDocLoading(false);
    }
  }, [row]);

  useEffect(() => {
    if (!open || !row) {
      setDocumental(null);
      setDocError(null);
      setDocLoading(false);
      return;
    }
    void recargarDocumental();
  }, [open, row?.id, recargarDocumental]);

  const onDocumentalUpdated = useCallback(async () => {
    await recargarDocumental();
    await onBandejasActualizadas();
  }, [recargarDocumental, onBandejasActualizadas]);

  const titleNode =
    row != null ? (
      <DocumentalModalTitleStack
        dominioChip="Comprobación"
        titulo="Reinspección por oficio"
        subtitulo={actaCabecera(row)}
        actuacionId={row.id}
      />
    ) : (
      "Reinspección por oficio"
    );

  const puedeEditarBloque =
    documental != null &&
    documental.oficio != null &&
    documental.expediente_respuesta != null &&
    !docLoading;

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
      actions={<DocumentalModalFooter onCerrar={onClose} />}
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <ReinspeccionDocumentalSharedLayout row={row} variant="pendiente" />
          {docError ? (
            <Alert severity="warning" sx={documentalGlassAlertSx}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                No se pudo cargar la ficha documental
              </Typography>
              <Typography variant="body2">{docError}</Typography>
            </Alert>
          ) : null}
          {docLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
              <CircularProgress size={28} />
            </Box>
          ) : puedeEditarBloque ? (
            <OperativoOficioYRespuestaEditable
              open={open}
              actuacionId={row.id}
              documental={documental}
              juzgados={juzgados}
              onDocumentalUpdated={onDocumentalUpdated}
            />
          ) : !docError ? (
            <Alert severity="info" sx={documentalGlassAlertSx}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                Edición no disponible
              </Typography>
              <Typography variant="body2">
                No hay datos completos de oficio y expediente de respuesta para mostrar la edición. Reintentá la carga o
                revisá la actuación en «Pendientes de oficio».
              </Typography>
            </Alert>
          ) : null}
        </Stack>
      )}
    </AppDialog>
  );
}
