import { useCallback, useEffect, useState } from "react";
import { Alert, Stack, Typography } from "@mui/material";

import {
  createOficioDesdeActuacion,
  fetchComprobacionDocumental,
  fetchOficiosByComprobacion,
  type IComprobacionDocumentalResponse,
  type IJuzgadoCatalogItem,
  type OficioComprobacionItem,
} from "../../../api/actuacionesPendientesApi";
import { useAppFeedback } from "../../../components/feedback";
import { DocumentalModalFooter, DocumentalModalTitleStack } from "../../../components/documental/DocumentalModalChrome";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import { documentalGlassAlertSx } from "../../../styles/documentalModalTokens";
import { AppDialog } from "../../../ui";
import { parseApiError } from "../../../utils/parseApiError";
import {
  applyOficioAltaErrorsFromApi,
  validateOficioAltaPayloadClient,
} from "../../../utils/oficioFormErrors";
import { ComprobacionOficiosTribunalSection } from "./ComprobacionOficiosTribunalSection";
import { type ComprobacionOficioAltaPayload } from "./ComprobacionOficioOperativoDialog";
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
  defaultFechaAlta: string;
  /** Tras guardar o recargar documental: refrescar bandejas (p. ej. `loadRein`). */
  onBandejasActualizadas: () => Promise<void>;
};

/**
 * Pendiente de reinspección por oficio: bloques consultivos + oficios del tribunal (lista, alta, edición por oficio).
 */
export function ComprobacionReinspeccionDetalleDialog({
  open,
  onClose,
  row,
  juzgados,
  defaultFechaAlta,
  onBandejasActualizadas,
}: ComprobacionReinspeccionDetalleDialogProps) {
  const feedback = useAppFeedback();
  const [documental, setDocumental] = useState<IComprobacionDocumentalResponse | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const [oficios, setOficios] = useState<OficioComprobacionItem[]>([]);
  const [oficiosLoading, setOficiosLoading] = useState(false);
  const [oficiosError, setOficiosError] = useState<string | null>(null);
  const [modalApiError, setModalApiError] = useState<string | null>(null);
  const [modalFieldErrors, setModalFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const loadOficios = useCallback(async (comprobacionId: number) => {
    setOficiosLoading(true);
    setOficiosError(null);
    try {
      const resp = await fetchOficiosByComprobacion(comprobacionId);
      setOficios(resp.oficios ?? []);
    } catch (err: unknown) {
      setOficios([]);
      setOficiosError(parseApiError(err, "No se pudo cargar el historial de oficios").message);
    } finally {
      setOficiosLoading(false);
    }
  }, []);

  const recargarModalData = useCallback(async () => {
    if (!row) return;
    setDocLoading(true);
    setDocError(null);
    try {
      const doc = await fetchComprobacionDocumental(row.id);
      setDocumental(doc);
      await loadOficios(doc.comprobacion_id);
    } catch (err: unknown) {
      setDocumental(null);
      setDocError(
        parseApiError(err, "No se pudo cargar la ficha documental para editar oficio y expediente de respuesta.").message
      );
    } finally {
      setDocLoading(false);
    }
  }, [row, loadOficios]);

  useEffect(() => {
    if (!open || !row) {
      setDocumental(null);
      setDocError(null);
      setDocLoading(false);
      setOficios([]);
      setOficiosError(null);
      setModalApiError(null);
      setSaving(false);
      return;
    }
    void recargarModalData();
  }, [open, row?.id, recargarModalData]);

  const onDocumentalUpdated = useCallback(async () => {
    await recargarModalData();
    await onBandejasActualizadas();
  }, [recargarModalData, onBandejasActualizadas]);

  const handleGuardarAlta = useCallback(
    async (payload: ComprobacionOficioAltaPayload) => {
      if (!row) return;
      const clientFe = validateOficioAltaPayloadClient(payload);
      setModalFieldErrors(clientFe);
      if (Object.keys(clientFe).length > 0) {
        setModalApiError(null);
        return;
      }
      setSaving(true);
      setModalApiError(null);
      setModalFieldErrors({});
      try {
        await createOficioDesdeActuacion(row.id, {
          numero_oficio: payload.numero_oficio.trim(),
          fecha_oficio: payload.fecha_oficio,
          juzgado_id: Number(payload.juzgado_id),
          causa: payload.causa,
          numero_expediente_oficio: payload.numero_expediente_oficio.trim(),
          fecha_expediente_oficio: payload.fecha_expediente_oficio,
        });
        feedback.success("Oficio registrado correctamente.");
        await onDocumentalUpdated();
      } catch (err: unknown) {
        const parsed = applyOficioAltaErrorsFromApi(err);
        setModalFieldErrors(parsed.fieldErrors);
        setModalApiError(parsed.globalMessage);
      } finally {
        setSaving(false);
      }
    },
    [row, onDocumentalUpdated, feedback]
  );

  const titleNode =
    row != null ? (
      <DocumentalModalTitleStack
        dominioChip="Comprobación"
        titulo={actaCabecera(row)}
        subtitulo="Reinspección por oficio"
        actuacionId={undefined}
      />
    ) : (
      "Reinspección por oficio"
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
      actions={undefined}
    >
      {!row ? null : (
        <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
          <ReinspeccionDocumentalSharedLayout row={row} variant="pendiente" ocultarOficioYRespuestaLectura />
          {docError ? (
            <Alert severity="warning" sx={documentalGlassAlertSx}>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                No se pudo cargar la ficha documental
              </Typography>
              <Typography variant="body2">{docError}</Typography>
            </Alert>
          ) : null}
          <ComprobacionOficiosTribunalSection
            open={open}
            actuacionId={row.id}
            documental={documental}
            documentalLoading={docLoading}
            oficios={oficios}
            oficiosLoading={oficiosLoading}
            oficiosError={oficiosError}
            juzgados={juzgados}
            defaultFechaAlta={defaultFechaAlta}
            modalApiError={modalApiError}
            modalFieldErrors={modalFieldErrors}
            saving={saving}
            onGuardarAlta={handleGuardarAlta}
            onDocumentalUpdated={onDocumentalUpdated}
            initialOficioId={row.oficio_id ?? null}
          />
        </Stack>
      )}
    </AppDialog>
  );
}
