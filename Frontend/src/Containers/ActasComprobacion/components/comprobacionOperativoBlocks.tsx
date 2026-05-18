import type { ReactNode } from "react";
import { memo } from "react";
import { Box, Stack, Typography } from "@mui/material";

import type { IActuacionesPendientesItem, IPendientesOficioItem } from "../../../api/actuacionesPendientesApi";
import type { IReinspeccionOficioPendienteRow } from "../../../api/actuacionesComprobacionActasApi";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  docModalActuacionScrollCardShellSx,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalEmptyStateSx,
  docModalFilaEtiquetaSx,
  docModalFilaValorSx,
  docModalGlassCardShellSx,
  docModalSubheadingInCardSx,
} from "../../../styles/documentalModalTokens";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";
import { humanizarTipoActuacion } from "../utils/documentalLabelFormat";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";

type DocumentalCardShell = "glass" | "actuacion";

export function textoValor(val: unknown): string {
  if (val === null || val === undefined || val === "") return "—";
  return String(val);
}

export function DocumentalFila({ etiqueta, valor }: { etiqueta: string; valor: string }) {
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

export function DocumentalBloque({
  overline,
  resumen,
  children,
  shell = "actuacion",
}: {
  overline: string;
  resumen?: string;
  children: ReactNode;
  /** Mismo shell liviano que Actuaciones / Notificación (operativa). */
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

function contribuyenteLineaPendiente(row: IActuacionesPendientesItem): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioLineaPendiente(row: IActuacionesPendientesItem): string {
  const t = formatActuacionListDomicilioLinea(row).trim();
  return t || "—";
}

function inspectoresLinea(row: IActuacionesPendientesItem): string {
  const t = (row.inspectores_texto ?? "").trim();
  if (t) return t;
  const parts = [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => (s ?? "").trim())
    .filter(Boolean);
  return parts.length ? parts.join(" · ") : "—";
}

/** Referencia para bandeja expediente (misma fila que `IActuacionesPendientesItem`). */
export function BloqueReferenciaComprobacionExpediente({ row }: { row: IActuacionesPendientesItem }) {
  return (
    <DocumentalBloque overline="Referencia de la comprobación">
      <DocumentalFila etiqueta="Domicilio" valor={domicilioLineaPendiente(row)} />
      <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribuyenteLineaPendiente(row)} />
      <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
      <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
      <DocumentalFila etiqueta="Motivo de la comprobación" valor={textoValor(row.comprobacion_motivo)} />
      <DocumentalFila etiqueta="Acta de comprobación Nº" valor={textoValor(row.acta_comprobacion_num)} />
    </DocumentalBloque>
  );
}

/** Fila oficio API + opcionales que el backend pueda enviar en el futuro (mismo patrón que grid). */
export type ComprobacionOficioReferenciaRow = IPendientesOficioItem & {
  doc_nro?: string | null;
  razon_social?: string | null;
};

function contribOficio(row: ComprobacionOficioReferenciaRow): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioOficio(row: IPendientesOficioItem): string {
  const t = formatActuacionListDomicilioLinea(row).trim();
  return t || "—";
}

function expedienteEnvioNumeroLinea(row: IPendientesOficioItem): string {
  const num = row.expediente_original_numero;
  const anio = row.expediente_original_anio;
  if (!num && anio == null) return "—";
  if (anio != null && String(anio).length) return `${num ?? "—"} / ${anio}`;
  return String(num ?? "—");
}

/**
 * Referencia bandeja oficio: mismas filas base + expediente de envío (número/año).
 * La fecha de expediente de envío no viene en el DTO actual de la API → "—".
 */
export const BloqueReferenciaComprobacionOficio = memo(function BloqueReferenciaComprobacionOficio({
  row,
}: {
  row: ComprobacionOficioReferenciaRow;
}) {
  return (
    <DocumentalBloque overline="Referencia de la comprobación">
      <DocumentalFila etiqueta="Domicilio" valor={domicilioOficio(row)} />
      <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribOficio(row)} />
      <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
      <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
      <DocumentalFila etiqueta="Motivo de la comprobación" valor={textoValor(row.comprobacion_motivo)} />
      <DocumentalFila etiqueta="Acta de comprobación Nº" valor={textoValor(row.acta_comprobacion_num)} />
      <DocumentalFila etiqueta="Expediente de envío" valor={expedienteEnvioNumeroLinea(row)} />
      <DocumentalFila
        etiqueta="Fecha del expediente de envío"
        valor={textoValor(row.expediente_original_fecha)}
      />
    </DocumentalBloque>
  );
});

export function BloqueInspeccionBaseComprobacion({
  row,
}: {
  row: Pick<
    IActuacionesPendientesItem,
    | "fecha_actuacion"
    | "acta_inspeccion_num"
    | "inspectores_texto"
    | "inspector1"
    | "inspector2"
    | "inspector3"
    | "orden_trabajo_numero"
    | "tipo_actuacion"
  >;
}) {
  const insp = inspectoresLinea(row as IActuacionesPendientesItem);
  return (
    <DocumentalBloque overline="La visita">
      <DocumentalFila etiqueta="Orden de trabajo" valor={textoValor(row.orden_trabajo_numero)} />
      <DocumentalFila etiqueta="Fecha de actuación" valor={textoValor(row.fecha_actuacion)} />
      <DocumentalFila etiqueta="Inspectores" valor={insp} />
      <DocumentalFila etiqueta="Tipo de actuación" valor={humanizarTipoActuacion(row.tipo_actuacion)} />
      <DocumentalFila etiqueta="Acta de inspección Nº" valor={textoValor(row.acta_inspeccion_num)} />
    </DocumentalBloque>
  );
}

/** Inspección base desde fila oficio (sin acta inspección en tipo API → opcional desde índice). */
export const BloqueInspeccionBaseFromOficioRow = memo(function BloqueInspeccionBaseFromOficioRow({
  row,
}: {
  row: IPendientesOficioItem & {
    acta_inspeccion_num?: string | null;
    inspectores_texto?: string | null;
    inspector1?: string | null;
    inspector2?: string | null;
    inspector3?: string | null;
    tipo_actuacion?: string | null;
  };
}) {
  const pseudo = {
    fecha_actuacion: row.fecha_actuacion,
    acta_inspeccion_num: row.acta_inspeccion_num ?? null,
    inspectores_texto: row.inspectores_texto ?? null,
    inspector1: row.inspector1 ?? null,
    inspector2: row.inspector2 ?? null,
    inspector3: row.inspector3 ?? null,
    orden_trabajo_numero: row.orden_trabajo_numero,
    tipo_actuacion: row.tipo_actuacion ?? null,
  } as Pick<
    IActuacionesPendientesItem,
    | "fecha_actuacion"
    | "acta_inspeccion_num"
    | "inspectores_texto"
    | "inspector1"
    | "inspector2"
    | "inspector3"
    | "orden_trabajo_numero"
    | "tipo_actuacion"
  >;
  return <BloqueInspeccionBaseComprobacion row={pseudo} />;
});

/** Fila pendiente reinspección: contrato API alineado al grid + detalle documental. */
export type ReinspeccionOperativoDetalleRow = IReinspeccionOficioPendienteRow;

function contribReinspeccion(row: ReinspeccionOperativoDetalleRow): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioReinspeccion(row: ReinspeccionOperativoDetalleRow): string {
  const t = formatActuacionListDomicilioLinea(row).trim();
  return t || "—";
}

export function parNumAnio(num: string | null | undefined, anio: string | number | null | undefined): string {
  if (!num && (anio === null || anio === undefined || anio === "")) return "—";
  if (anio !== null && anio !== undefined && String(anio).length) return `${num ?? "—"} / ${anio}`;
  return String(num ?? "—");
}

/** Referencia (solo lectura) para detalle de reinspección / recorrido: alineado a cabecera de acta + circuito documental. */
export function BloqueReferenciaReinspeccionDetalle({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  return (
    <DocumentalBloque overline="Referencia de la comprobación">
      <DocumentalFila etiqueta="Domicilio" valor={domicilioReinspeccion(row)} />
      <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribReinspeccion(row)} />
      <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
      <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
      <DocumentalFila etiqueta="Motivo de comprobación" valor={textoValor(row.comprobacion_motivo)} />
    </DocumentalBloque>
  );
}

/** Motivo en bloque aparte (solo si se necesita texto largo sin fila de referencia). Preferir fila en `BloqueReferenciaReinspeccionDetalle`. */
export function BloqueMotivoComprobacionDocumental({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  const m = (row.comprobacion_motivo ?? "").trim();
  if (!m) return null;
  return (
    <DocumentalBloque overline="Motivo de comprobación">
      <Typography variant="body2" sx={{ ...docModalFilaValorSx, py: 0.5 }}>
        {m}
      </Typography>
    </DocumentalBloque>
  );
}

/** Expediente de envío de acta (solo lectura). */
export function BloqueExpedienteEnvioReinspeccionDetalle({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  const envioNum = parNumAnio(row.expediente_envio_numero ?? null, row.expediente_envio_anio);
  const envioFecha = textoValor(row.fecha_expediente_envio);
  const tieneEnvio = envioNum !== "—" || envioFecha !== "—";

  return (
    <DocumentalBloque overline="Expediente de envío">
      {!tieneEnvio ? (
        <Typography variant="body2" sx={{ ...docModalEmptyStateSx, py: 0.5 }}>
          Sin datos de expediente de envío registrados.
        </Typography>
      ) : (
        <>
          {envioNum !== "—" ? <DocumentalFila etiqueta="N.º y año" valor={envioNum} /> : null}
          {envioFecha !== "—" ? <DocumentalFila etiqueta="Fecha" valor={envioFecha} /> : null}
        </>
      )}
    </DocumentalBloque>
  );
}

/**
 * Oficio y expediente de respuesta (solo lectura): primero respuesta, luego oficio.
 * Nota evolutiva: un único par respuesta/oficio por fila; sin múltiples oficios en esta vista.
 */
export function BloqueOficioYExpedienteRespuestaDetalle({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  const ofiNum = parNumAnio(row.oficio_numero ?? null, row.oficio_anio);
  const ofiFecha = textoValor(row.fecha_oficio);
  const causa = textoValor(row.oficio_causa);
  const juzgado = textoValor(row.juzgado_nombre);
  const tieneOficio = ofiNum !== "—" || ofiFecha !== "—" || causa !== "—" || juzgado !== "—";

  const respNum = parNumAnio(row.expediente_respuesta_numero ?? null, row.expediente_respuesta_anio);
  const respFecha = textoValor(row.fecha_expediente_respuesta);
  const tieneRespuesta = respNum !== "—" || respFecha !== "—";

  const hayAlguno = tieneOficio || tieneRespuesta;

  return (
    <DocumentalBloque overline="Oficio y expediente de respuesta">
      {!hayAlguno ? (
        <Typography variant="body2" sx={{ ...docModalEmptyStateSx, py: 0.5 }}>
          Sin datos de oficio ni expediente de respuesta registrados.
        </Typography>
      ) : (
        <>
          {tieneRespuesta ? (
            <>
              <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 0.25, mb: 0.5 }}>
                Expediente de respuesta
              </Typography>
              {respNum !== "—" ? <DocumentalFila etiqueta="N.º y año" valor={respNum} /> : null}
              {respFecha !== "—" ? <DocumentalFila etiqueta="Fecha" valor={respFecha} /> : null}
            </>
          ) : null}
          {tieneOficio ? (
            <>
              <Typography
                component="div"
                sx={{ ...docModalSubheadingInCardSx, mt: tieneRespuesta ? 1.25 : 0.25, mb: 0.5 }}
              >
                Oficio
              </Typography>
              {ofiNum !== "—" ? <DocumentalFila etiqueta="N.º y año" valor={ofiNum} /> : null}
              {ofiFecha !== "—" ? <DocumentalFila etiqueta="Fecha de oficio" valor={ofiFecha} /> : null}
              {causa !== "—" ? <DocumentalFila etiqueta="Causa" valor={causa} /> : null}
              {juzgado !== "—" ? <DocumentalFila etiqueta="Juzgado" valor={juzgado} /> : null}
            </>
          ) : null}
        </>
      )}
    </DocumentalBloque>
  );
}

/**
 * Compatibilidad: dos tarjetas («Expediente de envío» y «Oficio y expediente de respuesta»).
 * Preferir usar los bloques exportados por separado en el layout para espaciado homogéneo.
 */
export function BloqueTramitesReinspeccionDetalle({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  return (
    <>
      <BloqueExpedienteEnvioReinspeccionDetalle row={row} />
      <BloqueOficioYExpedienteRespuestaDetalle row={row} />
    </>
  );
}

/**
 * @deprecated Preferir `BloqueReferenciaReinspeccionDetalle` + `BloqueTramitesReinspeccionDetalle` para controlar el orden en el diálogo.
 */
export function BloqueReferenciaYTramitesReinspeccion({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  return (
    <Stack spacing={DOC_MODAL_BLOCK_STACK_SPACING}>
      <BloqueReferenciaReinspeccionDetalle row={row} />
      <BloqueTramitesReinspeccionDetalle row={row} />
    </Stack>
  );
}

export { DOC_MODAL_BLOCK_STACK_SPACING };
