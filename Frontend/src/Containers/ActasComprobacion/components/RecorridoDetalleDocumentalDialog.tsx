import { useCallback, useEffect, useState } from "react";
import { Alert, Box, CircularProgress, Stack, Typography } from "@mui/material";

import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoRow,
} from "../../../api/actuacionesComprobacionActasApi";
import {
  createOficioDesdeActuacion,
  fetchComprobacionDocumental,
  fetchOficiosByComprobacion,
  type IComprobacionDocumentalResponse,
  type IJuzgadoCatalogItem,
  type OficioComprobacionItem,
} from "../../../api/actuacionesPendientesApi";
import { useAppFeedback } from "../../../components/feedback";
import {
  CrudDialogHeader,
  CrudGlassDialog,
  useNotifyModalApiError,
} from "../../../components/crudDialog";
import {
  BloqueExpedienteEnvioReinspeccionDetalle,
  BloqueReferenciaReinspeccionDetalle,
  DOC_MODAL_BLOCK_STACK_SPACING,
} from "./comprobacionOperativoBlocks";
import { docModalEmptyStateSx, documentalGlassAlertSx } from "../../../styles/documentalModalTokens";
import { parseApiError } from "../../../utils/parseApiError";
import {
  applyOficioAltaErrorsFromApi,
  validateOficioAltaPayloadClient,
} from "../../../utils/oficioFormErrors";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";
import {
  reinspeccionCircuitoRowFromRecorrido,
} from "./ReinspeccionDocumentalSharedLayout";
import { ComprobacionOficiosTribunalSection } from "./ComprobacionOficiosTribunalSection";
import { type ComprobacionOficioAltaPayload } from "./ComprobacionOficioOperativoDialog";

/**
 * Combina fila del listado con ``referencia_actuacion`` del detalle.
 * No pisar valores útiles del listado con null/vacío del snapshot (evita perder inspectores / tipo).
 */
function mergeRecorridoDisplayRow(
  listRow: IComprobacionRecorridoRow | null,
  detalle: IComprobacionRecorridoDetalle
): IComprobacionRecorridoRow {
  const base = { ...(listRow ?? {}) } as Record<string, unknown>;
  const snap = detalle.referencia_actuacion;
  if (!snap || typeof snap !== "object") {
    return base as IComprobacionRecorridoRow;
  }
  const isUseful = (v: unknown): boolean => v != null && String(v).trim() !== "";
  const out: Record<string, unknown> = { ...base };
  for (const [k, v] of Object.entries(snap as Record<string, unknown>)) {
    if (isUseful(v)) {
      out[k] = v;
    }
  }
  return out as IComprobacionRecorridoRow;
}

function recorridoSubtitulo(
  ctx: IComprobacionRecorridoRow,
  detalle: IComprobacionRecorridoDetalle | null
): string {
  const n =
    (ctx.acta_comprobacion_num ?? "").trim() ||
    (detalle ? String(detalle.acta_comprobacion?.numero ?? "").trim() : "");
  const acta = n ? `Acta N.º ${n}` : null;
  const fecha = (ctx.fecha_actuacion ?? "").trim();
  const fechaPart = fecha ? `Fecha: ${fecha}` : null;
  const parts = [acta, fechaPart].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Historial documental";
}

function ejecucionReinspeccionUtil(detalle: IComprobacionRecorridoDetalle): boolean {
  const r = detalle.reinspeccion_por_oficio as Record<string, unknown> | null | undefined;
  const ej = r?.ejecucion_reinspeccion;
  return ej != null && typeof ej === "object" && Object.keys(ej as object).length > 0;
}

export type RecorridoDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  disablePortal?: boolean;
  actuacionId: number | null;
  /** Fila del listado; opcional. El detalle incluye ``referencia_actuacion`` (API actual). */
  listRow: IComprobacionRecorridoRow | null;
  detalle: IComprobacionRecorridoDetalle | null;
  loading: boolean;
  juzgados: IJuzgadoCatalogItem[];
  defaultFechaAlta: string;
  /** Tras alta/edición de oficio: refrescar bandejas y recorrido. */
  onBandejasActualizadas?: () => Promise<void>;
};

/**
 * Modal de detalle consultivo del recorrido documental (comprobación → oficio → reinspección).
 * Incluye gestión de oficios (alta múltiple) reutilizando el flujo operativo existente.
 */
export function RecorridoDetalleDocumentalDialog({
  open,
  onClose,
  disablePortal,
  actuacionId,
  listRow,
  detalle,
  loading,
  juzgados,
  defaultFechaAlta,
  onBandejasActualizadas,
}: RecorridoDetalleDocumentalDialogProps) {
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
  useNotifyModalApiError(modalApiError, open);

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

  const recargarOficiosDocumental = useCallback(async () => {
    if (actuacionId == null) return;
    setDocLoading(true);
    setDocError(null);
    try {
      const doc = await fetchComprobacionDocumental(actuacionId);
      setDocumental(doc);
      await loadOficios(doc.comprobacion_id);
    } catch (err: unknown) {
      setDocumental(null);
      setDocError(
        parseApiError(err, "No se pudo cargar la ficha documental para gestionar oficios.").message
      );
    } finally {
      setDocLoading(false);
    }
  }, [actuacionId, loadOficios]);

  useEffect(() => {
    if (!open || actuacionId == null) {
      setDocumental(null);
      setDocError(null);
      setDocLoading(false);
      setOficios([]);
      setOficiosError(null);
      setModalApiError(null);
      setModalFieldErrors({});
      setSaving(false);
      return;
    }
    void recargarOficiosDocumental();
  }, [open, actuacionId, recargarOficiosDocumental]);

  const onDocumentalUpdated = useCallback(async () => {
    await recargarOficiosDocumental();
    if (onBandejasActualizadas) {
      await onBandejasActualizadas();
    }
  }, [recargarOficiosDocumental, onBandejasActualizadas]);

  const handleGuardarAlta = useCallback(
    async (payload: ComprobacionOficioAltaPayload) => {
      if (actuacionId == null) return;
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
        await createOficioDesdeActuacion(actuacionId, {
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
    [actuacionId, onDocumentalUpdated, feedback]
  );

  const handleClose = () => {
    onClose();
  };

  const ctx = detalle ? mergeRecorridoDisplayRow(listRow, detalle) : ((listRow ?? {}) as IComprobacionRecorridoRow);
  const refAct = detalle?.referencia_actuacion;
  const reinsData = detalle?.reinspeccion_por_oficio as Record<string, unknown> | null | undefined;
  const muestraEjecucion = detalle != null && ejecucionReinspeccionUtil(detalle);

  const notaReferencia =
    refAct != null ? null : listRow ? (
      <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", mt: -1, opacity: 0.88 }}>
        Referencia y visita pueden ampliarse con la fila del listado hasta que el detalle esté completo.
      </Typography>
    ) : (
      <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", mt: -1, opacity: 0.88 }}>
        Abrí este detalle desde el listado de recorrido para ver la información con mayor consistencia.
      </Typography>
    );

  const circuitRow =
    detalle != null ? reinspeccionCircuitoRowFromRecorrido(ctx, detalle, reinsData ?? null) : null;

  const ejecPayload =
    muestraEjecucion && reinsData?.ejecucion_reinspeccion != null
      ? (reinsData.ejecucion_reinspeccion as Record<string, unknown>)
      : null;

  const ejecucionCtx = {
    oficioId: detalle?.oficio?.id ?? null,
    iniciadorId:
      reinsData?.iniciador_id != null && !Number.isNaN(Number(reinsData.iniciador_id))
        ? Number(reinsData.iniciador_id)
        : null,
  };

  const puedeGestionarOficios = actuacionId != null && documental?.expediente_envio != null;

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={() => handleClose()}
      onCloseButtonClick={handleClose}
      maxWidth="md"
      title={
        <CrudDialogHeader
          domainChip="Comprobación"
          titulo="Historial documental"
          subtitulo={actuacionId != null ? recorridoSubtitulo(ctx, detalle) : null}
        />
      }
    >
      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress sx={{ color: COLORS.primary }} />
        </Box>
      )}
      {!loading && detalle && circuitRow != null && (
        <Stack
          component="section"
          spacing={DOC_MODAL_BLOCK_STACK_SPACING}
          aria-label="Detalle del recorrido por etapas"
        >
          <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
            <BloqueReferenciaReinspeccionDetalle row={circuitRow} />
            {notaReferencia}
            <BloqueExpedienteEnvioReinspeccionDetalle row={circuitRow} />
          </Stack>

          {actuacionId != null ? (
            docError ? (
              <Alert severity="warning" sx={documentalGlassAlertSx}>
                <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                  No se pudo cargar la ficha documental
                </Typography>
                <Typography variant="body2">{docError}</Typography>
              </Alert>
            ) : puedeGestionarOficios ? (
              <ComprobacionOficiosTribunalSection
                open={open}
                actuacionId={actuacionId}
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
                initialOficioId={detalle.oficio?.id ?? null}
                ejecucionReinspeccion={ejecPayload}
                ejecucionReinspeccionCtx={ejecucionCtx}
                resultadoCircuito={detalle.resultado_final}
              />
            ) : !docLoading ? (
              <Alert severity="info" sx={documentalGlassAlertSx}>
                <Typography variant="body2">
                  Para agregar un oficio primero debe existir el expediente de envío de la comprobación.
                </Typography>
              </Alert>
            ) : null
          ) : null}
        </Stack>
      )}
    </CrudGlassDialog>
  );
}
