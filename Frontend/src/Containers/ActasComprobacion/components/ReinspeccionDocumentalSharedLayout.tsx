import type { ReactNode } from "react";
import { Stack, Typography } from "@mui/material";

import type {
  IComprobacionRecorridoDetalle,
  IComprobacionRecorridoRow,
} from "../../../api/actuacionesComprobacionActasApi";
import { docModalEmptyStateSx } from "../../../styles/documentalModalTokens";
import { humanizarCumplimientoOficio, humanizarTipoVisitaRecorrido } from "../utils/documentalLabelFormat";
import {
  BloqueExpedienteEnvioReinspeccionDetalle,
  BloqueInspeccionBaseComprobacion,
  BloqueOficioYExpedienteRespuestaDetalle,
  BloqueReferenciaReinspeccionDetalle,
  DOC_MODAL_BLOCK_STACK_SPACING,
  DocumentalBloque,
  DocumentalFila,
  textoValor,
  type ReinspeccionOperativoDetalleRow,
} from "./comprobacionOperativoBlocks";

function campoUtil(val: unknown): boolean {
  return val != null && String(val).trim() !== "";
}

/**
 * Arma la fila tipo pendiente para los bloques documentales de reinspección, mezclando
 * la fila de recorrido (o snapshot), los expedientes/oficio del detalle GET y el trámite en ruta.
 */
export function reinspeccionCircuitoRowFromRecorrido(
  ctx: IComprobacionRecorridoRow,
  detalle: IComprobacionRecorridoDetalle,
  reins: Record<string, unknown> | null | undefined
): ReinspeccionOperativoDetalleRow {
  const id = typeof ctx.id === "number" ? ctx.id : Number(ctx.id);
  const expEnv = detalle.expediente_comprobacion_envio as Record<string, unknown> | null | undefined;
  const expResp = detalle.expediente_respuesta_oficio as Record<string, unknown> | null | undefined;
  const ofi = detalle.oficio;

  const base = {
    ...ctx,
    id,
    expediente_envio_numero: expEnv?.numero != null ? String(expEnv.numero) : ctx.expediente_numero ?? null,
    expediente_envio_anio: (expEnv?.anio as string | number | null | undefined) ?? ctx.expediente_anio ?? null,
    fecha_expediente_envio: (expEnv?.fecha as string | null | undefined) ?? null,
    expediente_respuesta_numero: expResp?.numero != null ? String(expResp.numero) : null,
    expediente_respuesta_anio: (expResp?.anio as string | number | null | undefined) ?? null,
    fecha_expediente_respuesta: (expResp?.fecha as string | null | undefined) ?? null,
    oficio_numero: ofi?.numero_oficio ?? ctx.oficio_numero ?? null,
    oficio_anio: ofi?.anio ?? ctx.oficio_anio ?? null,
    fecha_oficio: ofi?.fecha_oficio ?? null,
    oficio_causa: ofi?.causa ?? null,
    juzgado_nombre: ofi?.juzgado_nombre ?? null,
  } as ReinspeccionOperativoDetalleRow;

  if (!reins) {
    return {
      ...base,
      iniciador_id: 0,
      estado_iniciador: "",
      tipo_iniciador: "",
      fecha_origen_iniciador: null,
      documento_pendiente: "—",
    } as ReinspeccionOperativoDetalleRow;
  }

  return {
    ...base,
    iniciador_id: Number(reins.iniciador_id ?? 0),
    estado_iniciador: String(reins.estado_iniciador ?? ""),
    tipo_iniciador: String(reins.tipo_iniciador ?? ""),
    fecha_origen_iniciador: (reins.fecha_origen as string | null) ?? null,
    documento_pendiente: String(reins.documento_pendiente ?? "Reinspección por oficio"),
  } as ReinspeccionOperativoDetalleRow;
}

function inspectoresLineaEjecucion(data: Record<string, unknown>): string {
  const t = (data.inspectores_texto ?? "").toString().trim();
  if (t) return t;
  const parts = [data.inspector1, data.inspector2, data.inspector3]
    .map((s) => (s ?? "").toString().trim())
    .filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
}

function tipoInspeccionEjecucionLabel(raw: unknown): string {
  if (!campoUtil(raw)) return "—";
  const h = humanizarTipoVisitaRecorrido(raw);
  return h === "—" ? String(raw).trim() : h;
}

export type ReinspeccionDocumentalSharedLayoutProps = {
  row: ReinspeccionOperativoDetalleRow;
  variant: "pendiente" | "recorrido";
  /** Solo recorrido y solo si el backend envía objeto (p. ej. trámite de reinspección CUMPLIDO). */
  ejecucionReinspeccion?: Record<string, unknown> | null;
  notaReferencia?: ReactNode;
  /**
   * Si es true, no se renderiza «Oficio y expediente de respuesta» en solo lectura.
   * Modal Pendiente de reinspección: la edición va en `OperativoOficioYRespuestaEditable`.
   * Recorrido/historial: debe ser false (o omitir) para conservar el bloque consultivo.
   */
  ocultarOficioYRespuestaLectura?: boolean;
};

/**
 * Circuito documental: referencia, visita, trámites.
 * En recorrido, opcional bloque final con datos de la visita ya ejecutada.
 */
export function ReinspeccionDocumentalSharedLayout({
  row,
  variant,
  ejecucionReinspeccion,
  notaReferencia,
  ocultarOficioYRespuestaLectura = false,
}: ReinspeccionDocumentalSharedLayoutProps) {
  const ej = ejecucionReinspeccion;
  const muestraEjecucion =
    variant === "recorrido" && ej != null && typeof ej === "object" && Object.keys(ej).length > 0;

  return (
    <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
      <BloqueReferenciaReinspeccionDetalle row={row} />
      {notaReferencia ? (
        <Typography variant="caption" sx={{ ...docModalEmptyStateSx, display: "block", mt: -1, opacity: 0.85 }}>
          {notaReferencia}
        </Typography>
      ) : null}
      <BloqueInspeccionBaseComprobacion
        row={{
          fecha_actuacion: row.fecha_actuacion,
          acta_inspeccion_num: row.acta_inspeccion_num ?? null,
          inspectores_texto: row.inspectores_texto ?? null,
          inspector1: row.inspector1 ?? null,
          inspector2: row.inspector2 ?? null,
          inspector3: row.inspector3 ?? null,
          orden_trabajo_numero: row.orden_trabajo_numero ?? null,
          tipo_actuacion: row.tipo_actuacion ?? null,
        }}
      />
      <BloqueExpedienteEnvioReinspeccionDetalle row={row} />
      {!ocultarOficioYRespuestaLectura ? <BloqueOficioYExpedienteRespuestaDetalle row={row} /> : null}
      {muestraEjecucion ? (
        <DocumentalBloque overline="Resultado de la visita de reinspección">
          <DocumentalFila etiqueta="Orden de trabajo" valor={textoValor(ej.orden_trabajo_numero)} />
          <DocumentalFila etiqueta="Fecha de actuación" valor={textoValor(ej.fecha_actuacion)} />
          <DocumentalFila etiqueta="Inspectores" valor={inspectoresLineaEjecucion(ej)} />
          <DocumentalFila etiqueta="Tipo de inspección labrada" valor={tipoInspeccionEjecucionLabel(ej.tipo_inspeccion_labrada)} />
          {(() => {
            const cumpl = humanizarCumplimientoOficio(ej.resultado_cumplimiento_oficio);
            return cumpl !== "—" ? (
              <DocumentalFila etiqueta="Cumplimiento del oficio" valor={cumpl} />
            ) : null;
          })()}
        </DocumentalBloque>
      ) : null}
    </Stack>
  );
}
