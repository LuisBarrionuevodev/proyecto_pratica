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
import { COLORS } from "../../Actuaciones/styles/filtroStyles";
import {
  humanizarCumplimientoOficio,
  humanizarEstadoIniciador,
  humanizarTipoActuacion,
  humanizarTipoExpediente,
  humanizarTipoVisitaRecorrido,
} from "../utils/documentalLabelFormat";

type DocumentalCardShell = "glass" | "actuacion";

function textoValor(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  return String(val);
}

function campoUtil(val: unknown): boolean {
  return val != null && String(val).trim() !== "";
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
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioLinea(row: IComprobacionRecorridoRow): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
  return t || "—";
}

function inspectoresLinea(row: IComprobacionRecorridoRow): string {
  const t = (row.inspectores_texto ?? "").trim();
  if (t) return t;
  const parts = [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
}

function actaComprobacionCabecera(listRow: IComprobacionRecorridoRow | null, detalle: IComprobacionRecorridoDetalle): string {
  const n =
    (listRow?.acta_comprobacion_num ?? "").trim() ||
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
  return campoUtil(data.estado_iniciador) || campoUtil(data.fecha_origen);
}

function reinspeccionPorOficioFilas(data: Record<string, unknown>): ReactNode {
  return (
    <>
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

export type RecorridoDetalleDocumentalDialogProps = {
  open: boolean;
  onClose: () => void;
  actuacionId: number | null;
  /** Fila del listado (misma actuación); opcional pero recomendada para domicilio e inspectores. */
  listRow: IComprobacionRecorridoRow | null;
  detalle: IComprobacionRecorridoDetalle | null;
  loading: boolean;
};

/**
 * Modal de detalle consultivo del recorrido documental (comprobación → oficio → reinspección).
 * Combina `GET .../comprobacion/recorrido/:id` con la fila del listado para domicilio, titular e inspectores.
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

  const titleNode =
    actuacionId != null && detalle ? (
      <Box sx={{ ...docModalHeaderStackSx, width: "100%" }}>
        <Chip label="Comprobación" size="small" sx={docModalChipSx} variant="outlined" />
        <Typography component="span" variant="h6" sx={docModalTitleSx}>
          Recorrido de la comprobación
        </Typography>
        <Typography variant="body2" sx={docModalSubtitleSx}>
          {actaComprobacionCabecera(listRow, detalle)}
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
          {listRow ? (
            <DocumentalBloque overline="Referencia">
              <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribTitular(listRow)} />
              <DocumentalFila etiqueta="Documento" valor={textoValor(listRow.doc_nro)} />
              <DocumentalFila etiqueta="Rubro" valor={textoValor(listRow.rubro_nombre)} />
              <DocumentalFila etiqueta="Domicilio" valor={domicilioLinea(listRow)} />
            </DocumentalBloque>
          ) : (
            <DocumentalBloque overline="Referencia">
              <Typography variant="body2" sx={docModalEmptyStateSx}>
                Sin datos de listado.
              </Typography>
            </DocumentalBloque>
          )}

          <DocumentalBloque overline="La visita">
            <DocumentalFila
              etiqueta="Fecha de actuación"
              valor={textoValor(listRow?.fecha_actuacion ?? o?.fecha_actuacion)}
            />
            <DocumentalFila
              etiqueta="Orden de trabajo"
              valor={textoValor(o?.orden_trabajo_numero ?? listRow?.orden_trabajo_numero)}
            />
            <DocumentalFila etiqueta="Acta de inspección Nº" valor={textoValor(listRow?.acta_inspeccion_num)} />
            <DocumentalFila etiqueta="Inspectores" valor={listRow ? inspectoresLinea(listRow) : "—"} />
            <DocumentalFila etiqueta="Tipo de actuación" valor={humanizarTipoActuacion(listRow?.tipo_actuacion)} />
            {o?.iniciador ? (
              <>
                <DocumentalFila etiqueta="Estado del trámite" valor={humanizarEstadoIniciador(o.iniciador.estado_iniciador)} />
                <DocumentalFila etiqueta="Fecha de origen del trámite" valor={textoValor(o.iniciador.fecha_origen)} />
              </>
            ) : null}
          </DocumentalBloque>

          <DocumentalBloque overline="Acta de comprobación">
            <DocumentalFila etiqueta="Número" valor={textoValor(detalle.acta_comprobacion?.numero)} />
            <DocumentalFila etiqueta="Motivo" valor={textoValor(detalle.acta_comprobacion?.motivo)} />
          </DocumentalBloque>

          {muestraExpedienteEnvio && expEnvio ? (
            <DocumentalBloque overline="Expediente de envío">
              {expedienteFilas(expEnvio)}
            </DocumentalBloque>
          ) : null}

          {muestraExpedienteRespuesta && expResp ? (
            <DocumentalBloque overline="Expediente de respuesta">
              {expedienteFilas(expResp, { numeroEtiqueta: "Número de expediente" })}
            </DocumentalBloque>
          ) : null}

          {muestraOficio && detalle.oficio ? (
            <DocumentalBloque overline="Oficio">{oficioAdministrativoFilas(detalle.oficio)}</DocumentalBloque>
          ) : null}

          {muestraReinspeccion && reinsData ? (
            <DocumentalBloque overline="Reinspección por oficio">
              {reinspeccionPorOficioFilas(reinsData)}
            </DocumentalBloque>
          ) : null}

          <DocumentalBloque overline="Resultado final">
            <DocumentalFila
              etiqueta="Estado del recorrido"
              valor={textoValor(detalle.resultado_final?.estado_recorrido)}
            />
            {(() => {
              const cumpl = humanizarCumplimientoOficio(detalle.resultado_final?.resultado_cumplimiento_oficio);
              return cumpl !== "—" ? <DocumentalFila etiqueta="Cumplimiento del oficio" valor={cumpl} /> : null;
            })()}
            <DocumentalFila etiqueta="Tipo de actuación" valor={valorTipoActuacionResultadoFinal(detalle)} />
          </DocumentalBloque>
        </Stack>
      )}
    </AppDialog>
  );
}
