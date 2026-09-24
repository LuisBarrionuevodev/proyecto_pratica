import { Stack, Typography } from "@mui/material";

import type { IComprobacionRecorridoResultadoFinal } from "../../../api/actuacionesComprobacionActasApi";
import { humanizarCumplimientoOficio, humanizarTipoVisitaRecorrido } from "../utils/documentalLabelFormat";
import { DocumentalFila, textoValor } from "./comprobacionOperativoBlocks";

function campoUtil(val: unknown): boolean {
  return val != null && String(val).trim() !== "";
}

function inspectoresLinea(data: Record<string, unknown>): string {
  const t = (data.inspectores_texto ?? "").toString().trim();
  if (t) return t;
  const parts = [data.inspector1, data.inspector2, data.inspector3]
    .map((s) => (s ?? "").toString().trim())
    .filter(Boolean);
  return parts.length ? parts.join(", ") : "—";
}

function tipoInspeccionLabel(raw: unknown): string {
  if (!campoUtil(raw)) return "—";
  const h = humanizarTipoVisitaRecorrido(raw);
  return h === "—" ? String(raw).trim() : h;
}

export type OficioComprobacionReinspeccionEnCardProps = {
  ejecucion: Record<string, unknown>;
  resultadoCircuito?: IComprobacionRecorridoResultadoFinal | null;
};

/**
 * Bloque «Resultado de la reinspección» dentro de la card de un oficio.
 * Solo renderizar cuando el backend asocia ejecución a ese oficio (PR7.16).
 */
export function OficioComprobacionReinspeccionEnCard({
  ejecucion,
  resultadoCircuito,
}: OficioComprobacionReinspeccionEnCardProps) {
  const cumplEj = humanizarCumplimientoOficio(ejecucion.resultado_cumplimiento_oficio);
  const cumplFinal = humanizarCumplimientoOficio(resultadoCircuito?.resultado_cumplimiento_oficio);
  const cumpl = cumplEj !== "—" ? cumplEj : cumplFinal;

  const situacion = textoValor(resultadoCircuito?.estado_recorrido);
  const ot = textoValor(ejecucion.orden_trabajo_numero);
  const fecha = textoValor(ejecucion.fecha_actuacion);
  const insp = inspectoresLinea(ejecucion);
  const tipo = tipoInspeccionLabel(ejecucion.tipo_inspeccion_labrada);

  const hayContenido =
    ot !== "—" ||
    fecha !== "—" ||
    insp !== "—" ||
    tipo !== "—" ||
    cumpl !== "—" ||
    situacion !== "—";

  if (!hayContenido) return null;

  return (
    <Stack spacing={0.75} sx={{ mt: 1.25, pt: 1.25, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
      <Typography
        variant="caption"
        sx={{
          color: "rgba(255,255,255,0.65)",
          fontWeight: 600,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          fontSize: "0.68rem",
        }}
      >
        Resultado de la reinspección
      </Typography>
      {ot !== "—" ? <DocumentalFila etiqueta="OT" valor={ot} /> : null}
      {fecha !== "—" ? <DocumentalFila etiqueta="Fecha" valor={fecha} /> : null}
      {insp !== "—" ? <DocumentalFila etiqueta="Inspectores" valor={insp} /> : null}
      {tipo !== "—" ? <DocumentalFila etiqueta="Tipo" valor={tipo} /> : null}
      {cumpl !== "—" ? <DocumentalFila etiqueta="Cumplimiento" valor={cumpl} /> : null}
      {situacion !== "—" ? <DocumentalFila etiqueta="Situación" valor={situacion} /> : null}
    </Stack>
  );
}
