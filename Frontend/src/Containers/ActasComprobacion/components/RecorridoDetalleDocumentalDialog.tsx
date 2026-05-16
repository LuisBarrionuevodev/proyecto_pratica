import { Box, CircularProgress, Stack, Typography } from "@mui/material";

import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoRow,
} from "../../../api/actuacionesComprobacionActasApi";
import { DocumentalModalFooter, DocumentalModalTitleStack } from "../../../components/documental/DocumentalModalChrome";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  DocumentalBloque,
  DocumentalFila,
} from "./comprobacionOperativoBlocks";
import { docModalEmptyStateSx } from "../../../styles/documentalModalTokens";
import { AppDialog } from "../../../ui";
import { humanizarCumplimientoOficio, humanizarTipoVisitaRecorrido } from "../utils/documentalLabelFormat";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";
import {
  reinspeccionCircuitoRowFromRecorrido,
  ReinspeccionDocumentalSharedLayout,
} from "./ReinspeccionDocumentalSharedLayout";

function textoValor(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  return String(val);
}

function campoUtil(val: unknown): boolean {
  return val != null && String(val).trim() !== "";
}

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

function actaComprobacionCabecera(
  ctx: IComprobacionRecorridoRow,
  detalle: IComprobacionRecorridoDetalle | null
): string {
  const n =
    (ctx.acta_comprobacion_num ?? "").trim() ||
    (detalle ? String(detalle.acta_comprobacion?.numero ?? "").trim() : "");
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

function reinspeccionTieneContenido(data: Record<string, unknown> | null | undefined): boolean {
  if (!data || Object.keys(data).length === 0) return false;
  return (
    campoUtil(data.estado_iniciador) ||
    campoUtil(data.fecha_origen) ||
    campoUtil(data.tipo_iniciador) ||
    campoUtil(data.documento_pendiente)
  );
}

/**
 * Circuito en espera de la visita posterior (reinspección por oficio): el `tipo_actuacion` del
 * grid sigue siendo el de la actuación ya labrada (p. ej. reinspección), pero en resultado final
 * debe leerse como trabajo pendiente, no como “tipo final” del circuito.
 */
function esRecorridoPendienteReinspeccionPorOficio(estadoRecorrido: unknown): boolean {
  const s = String(estadoRecorrido ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\u0300-\u036f/g, "");
  return s.includes("pendiente reinspeccion por oficio");
}

/** ``REINSPECCION`` genérico = paso del circuito, no la actuación hija (ratificación / verificar e informar). */
function esReinspeccionGenericaResultado(val: unknown): boolean {
  const n = String(val ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/\u0300-\u036f/g, "")
    .replace(/_/g, " ");
  return n.replace(/\s+/g, " ") === "reinspeccion";
}

function valorTipoActuacionResultadoFinal(detalle: IComprobacionRecorridoDetalle): string {
  if (esRecorridoPendienteReinspeccionPorOficio(detalle.resultado_final?.estado_recorrido)) {
    return "Pendiente";
  }
  const preferido = detalle.resultado_final?.tipo_visita ?? detalle.resultado_final?.tipo_actuacion;
  if (preferido == null || String(preferido).trim() === "") {
    return "Pendiente";
  }
  if (esReinspeccionGenericaResultado(preferido)) {
    return "Pendiente";
  }
  const humanizado = humanizarTipoVisitaRecorrido(preferido);
  if (humanizado === "Reinspeccion") {
    return "Pendiente";
  }
  return humanizado;
}

function ejecucionReinspeccionUtil(detalle: IComprobacionRecorridoDetalle): boolean {
  const r = detalle.reinspeccion_por_oficio as Record<string, unknown> | null | undefined;
  const ej = r?.ejecucion_reinspeccion;
  return ej != null && typeof ej === "object" && Object.keys(ej as object).length > 0;
}

export type RecorridoDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  actuacionId: number | null;
  /** Fila del listado; opcional. El detalle incluye ``referencia_actuacion`` (API actual). */
  listRow: IComprobacionRecorridoRow | null;
  detalle: IComprobacionRecorridoDetalle | null;
  loading: boolean;
};

/**
 * Modal de detalle consultivo del recorrido documental (comprobación → oficio → reinspección).
 * Los datos de visita y titular se leen de ``GET .../recorrido/:id`` (``referencia_actuacion`` + ``origen``);
 * ``listRow`` solo complementa si el servidor es antiguo o hay campos extra en la tabla.
 * Solo lectura: la edición documental vive en el flujo operativo (p. ej. bandeja Oficio).
 */
export function RecorridoDetalleDocumentalDialog({
  open,
  onClose,
  actuacionId,
  listRow,
  detalle,
  loading,
}: RecorridoDetalleDocumentalDialogProps) {
  const handleClose = () => {
    onClose();
  };

  const ctx = detalle ? mergeRecorridoDisplayRow(listRow, detalle) : ((listRow ?? {}) as IComprobacionRecorridoRow);
  const refAct = detalle?.referencia_actuacion;

  const titleNode =
    actuacionId != null ? (
      <DocumentalModalTitleStack
        dominioChip="Comprobación"
        titulo={actaComprobacionCabecera(ctx, detalle)}
        subtitulo={undefined}
        actuacionId={undefined}
      />
    ) : (
      "Recorrido"
    );

  const reinsData = detalle?.reinspeccion_por_oficio as Record<string, unknown> | null | undefined;
  const muestraReinspeccion = reinspeccionTieneContenido(reinsData);
  const muestraEjecucion = detalle != null && ejecucionReinspeccionUtil(detalle);
  const ocultarCumplYTipoEnResultadoFinal =
    (detalle != null && esRecorridoPendienteReinspeccionPorOficio(detalle.resultado_final?.estado_recorrido)) ||
    muestraEjecucion;

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
    muestraReinspeccion && reinsData?.ejecucion_reinspeccion != null
      ? (reinsData.ejecucion_reinspeccion as Record<string, unknown>)
      : null;

  return (
    <AppDialog
      open={open}
      onClose={() => handleClose()}
      onCloseButtonClick={handleClose}
      title={titleNode}
      fullWidth
      maxWidth="md"
      appearance="glass"
      contentDividers
      contentSx={{ ...formDialogContentStackSx, pt: 2, pb: 2 }}
      actions={<DocumentalModalFooter onCerrar={handleClose} />}
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
          <ReinspeccionDocumentalSharedLayout
            row={circuitRow}
            variant="recorrido"
            ejecucionReinspeccion={ejecPayload}
            notaReferencia={notaReferencia}
          />

          <DocumentalBloque overline="Resultado del circuito">
            <DocumentalFila etiqueta="Situación" valor={textoValor(detalle.resultado_final?.estado_recorrido)} />
            {!ocultarCumplYTipoEnResultadoFinal ? (
              <>
                {(() => {
                  const cumpl = humanizarCumplimientoOficio(detalle.resultado_final?.resultado_cumplimiento_oficio);
                  return cumpl !== "—" ? <DocumentalFila etiqueta="Cumplimiento del oficio" valor={cumpl} /> : null;
                })()}
                <DocumentalFila etiqueta="Tipo de visita final" valor={valorTipoActuacionResultadoFinal(detalle)} />
              </>
            ) : null}
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
