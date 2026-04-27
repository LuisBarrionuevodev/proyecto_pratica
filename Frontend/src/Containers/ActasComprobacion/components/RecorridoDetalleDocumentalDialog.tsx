import type { ReactNode } from "react";
import { Box, Chip, CircularProgress, Stack, Typography } from "@mui/material";

import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoOficio,
  IComprobacionRecorridoRow,
} from "../../../api/actuacionesComprobacionActasApi";
import { formDialogContentStackSx } from "../../../styles/formDialogStyles";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  docModalActuacionScrollCardShellSx,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalChipSx,
  docModalEmptyStateSx,
  docModalFilaEtiquetaSx,
  docModalFilaValorSx,
  docModalFooterButtonsSx,
  docModalFooterRowSx,
  docModalGlassCardShellSx,
  docModalHeaderStackSx,
  docModalSubtitleSx,
  docModalTitleSx,
} from "../../../styles/documentalModalTokens";
import { AppButton, AppDialog } from "../../../ui";
import { contribuyenteBandejaLabel } from "../../../utils/contribuyenteBandejaText";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";
import {
  humanizarCumplimientoOficio,
  humanizarEstadoIniciador,
  humanizarTipoActuacion,
  humanizarTipoExpediente,
  humanizarTipoVisitaRecorrido,
  humanizarTokenBackend,
} from "../utils/documentalLabelFormat";

type DocumentalCardShell = "glass" | "actuacion";

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

function DocumentalFila({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: { xs: 0.25, sm: 1 },
        justifyContent: "space-between",
        alignItems: "baseline",
        py: 0.65,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        "&:last-of-type": { borderBottom: "none", pb: 0 },
      }}
    >
      <Typography component="span" variant="body2" sx={docModalFilaEtiquetaSx}>
        {etiqueta}
      </Typography>
      <Typography component="span" variant="body2" sx={docModalFilaValorSx}>
        {valor}
      </Typography>
    </Box>
  );
}

function DocumentalBloque({
  overline,
  resumen,
  children,
  shell = "actuacion",
}: {
  overline: string;
  resumen?: string;
  children: ReactNode;
  shell?: DocumentalCardShell;
}) {
  const shellSx =
    shell === "actuacion" ? docModalActuacionScrollCardShellSx(COLORS.primary) : docModalGlassCardShellSx(COLORS.primary);
  return (
    <Box sx={shellSx}>
      <Typography component="div" sx={docModalBlockOverlineSx}>
        {overline}
      </Typography>
      {resumen ? (
        <Typography component="div" sx={docModalBlockResumenSx}>
          {resumen}
        </Typography>
      ) : null}
      {children}
    </Box>
  );
}

function contribTitular(row: IComprobacionRecorridoRow): string {
  return contribuyenteBandejaLabel(row.contrib_apellido, row.contrib_nombre, row.razon_social);
}

function domicilioLinea(row: IComprobacionRecorridoRow): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
  return t || "—";
}

function inspectoresEtiqueta(row: IComprobacionRecorridoRow): string {
  const t = (row.inspectores_texto ?? "").trim();
  if (t) return t;
  const parts = [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  if (parts.length) return parts.join(" · ");
  return "Sin inspectores asignados en esta actuación.";
}

function tipoActuacionEtiqueta(val: unknown): string {
  const h = humanizarTipoActuacion(val);
  return h === "—" ? "Sin tipo de actuación en el registro." : h;
}

function actaComprobacionCabecera(ctx: IComprobacionRecorridoRow, detalle: IComprobacionRecorridoDetalle): string {
  const n =
    (ctx.acta_comprobacion_num ?? "").trim() ||
    String(detalle.acta_comprobacion?.numero ?? "").trim();
  return n ? `Acta de comprobación Nº ${n}` : "Acta de comprobación";
}

function expedienteRecordUtil(exp: Record<string, unknown> | null | undefined): boolean {
  if (!exp || Object.keys(exp).length === 0) return false;
  return campoUtil(exp.fecha) || campoUtil(exp.anio) || campoUtil(exp.numero) || campoUtil(exp.tipo);
}

function expedienteFilas(
  exp: Record<string, unknown>,
  opts?: { numeroEtiqueta?: string }
): ReactNode {
  const numLbl = opts?.numeroEtiqueta ?? "Número";
  return (
    <>
      <DocumentalFila etiqueta="Fecha" valor={textoValor(exp.fecha)} />
      <DocumentalFila etiqueta="Año" valor={textoValor(exp.anio)} />
      <DocumentalFila etiqueta={numLbl} valor={textoValor(exp.numero)} />
      <DocumentalFila etiqueta="Tipo" valor={humanizarTipoExpediente(exp.tipo)} />
    </>
  );
}

function oficioTieneContenido(ofi: IComprobacionRecorridoOficio | null | undefined): boolean {
  if (!ofi) return false;
  return !!(
    campoUtil(ofi.numero_oficio) ||
    ofi.anio != null ||
    campoUtil(ofi.fecha_oficio) ||
    campoUtil(ofi.causa) ||
    ofi.juzgado_id != null ||
    campoUtil(ofi.juzgado_nombre)
  );
}

function oficioAdministrativoFilas(ofi: IComprobacionRecorridoOficio): ReactNode {
  const juz = (ofi.juzgado_nombre ?? "").trim();
  return (
    <>
      <DocumentalFila etiqueta="Número de oficio" valor={textoValor(ofi.numero_oficio)} />
      <DocumentalFila etiqueta="Año" valor={textoValor(ofi.anio)} />
      <DocumentalFila etiqueta="Fecha de oficio" valor={textoValor(ofi.fecha_oficio)} />
      <DocumentalFila etiqueta="Causa" valor={textoValor(ofi.causa)} />
      <DocumentalFila etiqueta="Juzgado" valor={juz || "—"} />
    </>
  );
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

function reinspeccionPorOficioFilas(data: Record<string, unknown>): ReactNode {
  return (
    <>
      <DocumentalFila etiqueta="Iniciador (tipo)" valor={humanizarTokenBackend(data.tipo_iniciador)} />
      <DocumentalFila etiqueta="Trámite / documento pendiente" valor={textoValor(data.documento_pendiente)} />
      <DocumentalFila etiqueta="Estado del trámite" valor={humanizarEstadoIniciador(data.estado_iniciador)} />
      <DocumentalFila etiqueta="Fecha de origen del trámite" valor={textoValor(data.fecha_origen)} />
    </>
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

function docNroEtiqueta(row: IComprobacionRecorridoRow): string {
  return campoUtil(row.doc_nro) ? String(row.doc_nro).trim() : "Sin documento en el contribuyente vinculado.";
}

function rubroEtiqueta(row: IComprobacionRecorridoRow): string {
  return campoUtil(row.rubro_nombre) ? String(row.rubro_nombre).trim() : "Sin rubro en el domicilio.";
}

function domicilioEtiqueta(row: IComprobacionRecorridoRow): string {
  const d = domicilioLinea(row);
  return d === "—" ? "Sin domicilio cargado en la actuación." : d;
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
    actuacionId != null && detalle ? (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Recorrido de la comprobación
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaComprobacionCabecera(ctx, detalle)}
        </Typography>
      </Box>
    ) : actuacionId != null ? (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Recorrido de la comprobación
        </Typography>
      </Box>
    ) : (
      "Recorrido"
    );

  const o = detalle?.origen;
  const expEnvio = detalle?.expediente_comprobacion_envio as Record<string, unknown> | null | undefined;
  const expResp = detalle?.expediente_respuesta_oficio as Record<string, unknown> | null | undefined;
  const reinsData = detalle?.reinspeccion_por_oficio as Record<string, unknown> | null | undefined;

  const muestraExpedienteEnvio = expedienteRecordUtil(expEnvio);
  const muestraExpedienteRespuesta = expedienteRecordUtil(expResp);
  const muestraOficio = oficioTieneContenido(detalle?.oficio ?? null);
  const muestraReinspeccion = reinspeccionTieneContenido(reinsData);

  const refApi = detalle?.referencia_actuacion;
  const notaFuenteReferencia =
    refApi != null ? (
      <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", pt: 0.5, opacity: 0.85 }}>
        Datos de referencia y visita: respuesta de detalle (alineados al listado). La fila de tabla es opcional.
      </Typography>
    ) : listRow ? (
      <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", pt: 0.5, opacity: 0.85 }}>
        Referencia tomada principalmente de la fila del listado (API sin snapshot extendido).
      </Typography>
    ) : (
      <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", pt: 0.5, opacity: 0.85 }}>
        Sin fila de listado ni snapshot en detalle: algunos campos pueden faltar hasta recargar el servidor.
      </Typography>
    );

  const actaInspeccionValor = campoUtil(refAct?.acta_inspeccion_num)
    ? String(refAct?.acta_inspeccion_num).trim()
    : campoUtil(ctx.acta_inspeccion_num)
      ? String(ctx.acta_inspeccion_num).trim()
      : "Sin acta de inspección vinculada a esta actuación.";

  const motivoComprobacionValor = (() => {
    const ac = detalle?.acta_comprobacion as { motivo?: unknown } | undefined;
    const m = ac?.motivo ?? refAct?.comprobacion_motivo;
    return campoUtil(m) ? String(m).trim() : "Sin motivo registrado en la comprobación.";
  })();

  const actaComprobacionNumReferencia = (() => {
    const ac = detalle?.acta_comprobacion as { numero?: unknown } | undefined;
    const n = ac?.numero ?? refAct?.acta_comprobacion_num ?? ctx.acta_comprobacion_num;
    return campoUtil(n) ? String(n).trim() : "Sin número de acta en el registro.";
  })();

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
      actions={
        <Box sx={docModalFooterRowSx}>
          <Box sx={{ flex: "1 1 120px", minWidth: 0 }} />
          <Box sx={docModalFooterButtonsSx}>
            <AppButton dsVariant="primary" dsSize="sm" onClick={handleClose}>
              Cerrar
            </AppButton>
          </Box>
        </Box>
      }
    >
      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress sx={{ color: COLORS.primary }} />
        </Box>
      )}
      {!loading && detalle && (
        <Stack
          component="section"
          spacing={DOC_MODAL_BLOCK_STACK_SPACING}
          aria-label="Detalle del recorrido por etapas"
        >
          <DocumentalBloque overline="Referencia (titular y domicilio)">
            {notaFuenteReferencia}
            <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribTitular(ctx)} />
            <DocumentalFila etiqueta="Documento" valor={docNroEtiqueta(ctx)} />
            <DocumentalFila etiqueta="Rubro" valor={rubroEtiqueta(ctx)} />
            <DocumentalFila etiqueta="Domicilio" valor={domicilioEtiqueta(ctx)} />
            <DocumentalFila etiqueta="Motivo de la comprobación" valor={motivoComprobacionValor} />
            <DocumentalFila etiqueta="Acta de comprobación Nº" valor={actaComprobacionNumReferencia} />
          </DocumentalBloque>

          <DocumentalBloque overline="La visita">
            <DocumentalFila
              etiqueta="Fecha de actuación"
              valor={textoValor(ctx.fecha_actuacion ?? o?.fecha_actuacion)}
            />
            <DocumentalFila
              etiqueta="Orden de trabajo"
              valor={textoValor(o?.orden_trabajo_numero ?? ctx.orden_trabajo_numero)}
            />
            <DocumentalFila etiqueta="Acta de inspección Nº" valor={actaInspeccionValor} />
            <DocumentalFila etiqueta="Inspectores" valor={inspectoresEtiqueta(ctx)} />
            <DocumentalFila
              etiqueta="Tipo de actuación"
              valor={tipoActuacionEtiqueta((refAct?.tipo_actuacion ?? ctx.tipo_actuacion) as string | null | undefined)}
            />
            {o?.iniciador ? (
              <>
                <DocumentalFila
                  etiqueta="Iniciador (origen del circuito)"
                  valor={humanizarTokenBackend(o.iniciador.tipo_iniciador)}
                />
                <DocumentalFila
                  etiqueta="Estado del trámite (origen)"
                  valor={humanizarEstadoIniciador(o.iniciador.estado_iniciador)}
                />
                <DocumentalFila
                  etiqueta="Fecha de origen (origen)"
                  valor={textoValor(o.iniciador.fecha_origen)}
                />
              </>
            ) : (
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin iniciador de origen vinculado (p. ej. actuación sin cola de ruta o solo reinspección por oficio).
              </Typography>
            )}
          </DocumentalBloque>

          <DocumentalBloque overline="Acta de comprobación">
            <DocumentalFila
              etiqueta="Número"
              valor={
                campoUtil(detalle.acta_comprobacion?.numero)
                  ? String(detalle.acta_comprobacion?.numero).trim()
                  : "Sin número de acta en el registro."
              }
            />
            <DocumentalFila
              etiqueta="Motivo"
              valor={
                campoUtil(detalle.acta_comprobacion?.motivo)
                  ? String(detalle.acta_comprobacion?.motivo).trim()
                  : "Sin motivo registrado en la comprobación."
              }
            />
          </DocumentalBloque>

          <DocumentalBloque overline="Expediente de envío">
            {muestraExpedienteEnvio && expEnvio ? (
              <>{expedienteFilas(expEnvio)}</>
            ) : (
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin expediente de envío registrado para esta comprobación.
              </Typography>
            )}
          </DocumentalBloque>

          <DocumentalBloque overline="Expediente de respuesta">
            {muestraExpedienteRespuesta && expResp ? (
              <>{expedienteFilas(expResp, { numeroEtiqueta: "Número de expediente" })}</>
            ) : (
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin expediente de respuesta de oficio (o aún no consta en el circuito).
              </Typography>
            )}
          </DocumentalBloque>

          <DocumentalBloque overline="Oficio">
            {muestraOficio && detalle.oficio ? (
              <>{oficioAdministrativoFilas(detalle.oficio)}</>
            ) : (
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin oficio administrativo cargado para esta comprobación.
              </Typography>
            )}
          </DocumentalBloque>

          <DocumentalBloque overline="Reinspección por oficio">
            {muestraReinspeccion && reinsData ? (
              reinspeccionPorOficioFilas(reinsData)
            ) : (
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin iniciador de reinspección por oficio (no programada o pendiente de creación en ruta).
              </Typography>
            )}
          </DocumentalBloque>

          <DocumentalBloque overline="Resultado final">
            <DocumentalFila
              etiqueta="Estado del recorrido"
              valor={textoValor(detalle.resultado_final?.estado_recorrido)}
            />
            {(() => {
              const cumpl = humanizarCumplimientoOficio(detalle.resultado_final?.resultado_cumplimiento_oficio);
              return cumpl !== "—" ? <DocumentalFila etiqueta="Cumplimiento del oficio" valor={cumpl} /> : null;
            })()}
            <DocumentalFila etiqueta="Tipo de actuación (resultado)" valor={valorTipoActuacionResultadoFinal(detalle)} />
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
