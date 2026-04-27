import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

import type { IActuacionesPendientesItem, IPendientesOficioItem } from "../../../api/actuacionesPendientesApi";
import type { IReinspeccionOficioPendienteRow } from "../../../api/actuacionesComprobacionActasApi";
import {
  DOC_MODAL_BLOCK_STACK_SPACING,
  docModalActuacionScrollCardShellSx,
  docModalBlockOverlineSx,
  docModalBlockResumenSx,
  docModalFilaEtiquetaSx,
  docModalFilaValorSx,
  docModalGlassCardShellSx,
  docModalSubheadingInCardSx,
} from "../../../styles/documentalModalTokens";
import { COLORS } from "../../Actuaciones/styles/filtroStyles";
import { humanizarTipoActuacion } from "../utils/documentalLabelFormat";

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
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
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
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
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
export function BloqueReferenciaComprobacionOficio({ row }: { row: ComprobacionOficioReferenciaRow }) {
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
}

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
      <DocumentalFila etiqueta="Fecha de actuación" valor={textoValor(row.fecha_actuacion)} />
      <DocumentalFila etiqueta="Orden de trabajo" valor={textoValor(row.orden_trabajo_numero)} />
      <DocumentalFila etiqueta="Acta de inspección Nº" valor={textoValor(row.acta_inspeccion_num)} />
      <DocumentalFila etiqueta="Inspectores" valor={insp} />
      <DocumentalFila etiqueta="Tipo de actuación" valor={humanizarTipoActuacion(row.tipo_actuacion)} />
    </DocumentalBloque>
  );
}

/** Inspección base desde fila oficio (sin acta inspección en tipo API → opcional desde índice). */
export function BloqueInspeccionBaseFromOficioRow({
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
}

/** Fila reinspección + campos opcionales del grid / futuros sin cambiar contrato mínimo de API. */
export type ReinspeccionOperativoDetalleRow = IReinspeccionOficioPendienteRow & {
  doc_nro?: string | null;
  razon_social?: string | null;
  acta_inspeccion_num?: string | null;
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  tipo_actuacion?: string | null;
  oficio_causa?: string | null;
  fecha_oficio?: string | null;
  juzgado_nombre?: string | null;
  expediente_numero?: string | null;
  expediente_anio?: number | null;
  expediente_envio_numero?: string | null;
  expediente_envio_anio?: string | number | null;
  expediente_respuesta_numero?: string | null;
  expediente_respuesta_anio?: string | number | null;
  fecha_expediente_respuesta?: string | null;
  fecha_expediente_envio?: string | null;
};

function contribReinspeccion(row: ReinspeccionOperativoDetalleRow): string {
  const rs = (row.razon_social ?? "").trim();
  if (rs) return rs;
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioReinspeccion(row: ReinspeccionOperativoDetalleRow): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
  return t || "—";
}

function parNumAnio(num: string | null | undefined, anio: string | number | null | undefined): string {
  if (!num && (anio === null || anio === undefined || anio === "")) return "—";
  if (anio !== null && anio !== undefined && String(anio).length) return `${num ?? "—"} / ${anio}`;
  return String(num ?? "—");
}

/** Referencia (solo lectura) para detalle de reinspección por oficio. */
export function BloqueReferenciaReinspeccionDetalle({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  return (
    <DocumentalBloque overline="Referencia de la comprobación">
      <DocumentalFila etiqueta="Domicilio" valor={domicilioReinspeccion(row)} />
      <DocumentalFila etiqueta="Contribuyente / razón social" valor={contribReinspeccion(row)} />
      <DocumentalFila etiqueta="Documento" valor={textoValor(row.doc_nro)} />
      <DocumentalFila etiqueta="Rubro" valor={textoValor(row.rubro_nombre)} />
      <DocumentalFila etiqueta="Motivo de la comprobación" valor={textoValor(row.comprobacion_motivo)} />
      <DocumentalFila etiqueta="Acta de comprobación Nº" valor={textoValor(row.acta_comprobacion_num)} />
    </DocumentalBloque>
  );
}

/** Expediente / oficio asociados (solo lectura) en detalle de reinspección. */
export function BloqueTramitesReinspeccionDetalle({ row }: { row: ReinspeccionOperativoDetalleRow }) {
  return (
    <DocumentalBloque overline="Trámites administrativos">
      <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 0.25, mb: 0.5 }}>
        Expediente de envío
      </Typography>
      <DocumentalFila etiqueta="N.º y año" valor={parNumAnio(row.expediente_envio_numero ?? null, row.expediente_envio_anio)} />
      <DocumentalFila etiqueta="Fecha" valor={textoValor(row.fecha_expediente_envio)} />
      <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1, mb: 0.5 }}>
        Expediente de respuesta
      </Typography>
      <DocumentalFila etiqueta="N.º y año" valor={parNumAnio(row.expediente_respuesta_numero ?? null, row.expediente_respuesta_anio)} />
      <DocumentalFila etiqueta="Fecha" valor={textoValor(row.fecha_expediente_respuesta)} />
      <Typography component="div" sx={{ ...docModalSubheadingInCardSx, mt: 1, mb: 0.5 }}>
        Oficio
      </Typography>
      <DocumentalFila etiqueta="N.º y año" valor={parNumAnio(row.oficio_numero ?? null, row.oficio_anio)} />
      <DocumentalFila etiqueta="Fecha de oficio" valor={textoValor(row.fecha_oficio)} />
      <DocumentalFila etiqueta="Causa" valor={textoValor(row.oficio_causa)} />
      <DocumentalFila etiqueta="Juzgado" valor={textoValor(row.juzgado_nombre)} />
    </DocumentalBloque>
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
