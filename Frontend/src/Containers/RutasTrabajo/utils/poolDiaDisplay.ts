import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";

/** Etiqueta de origen para badges en pool del día. */
export function poolDiaOrigenLabel(origen: string | null | undefined): string {
  const key = (origen ?? "").trim().toUpperCase();
  if (key === "ACTUACION_NOTIF") return "Notificación";
  if (key === "ACTUACION_COMP") return "Comprobación";
  if (key === "INICIADOR") return "Iniciador";
  if (key === "RELEVAMIENTO") return "Relevamiento";
  if (key === "DENUNCIA") return "Denuncia";
  if (key === "MANUAL") return "Manual";
  return origen?.trim() || "—";
}

/**
 * Adapta fila de pool backend a formato de iniciador pendiente (Asignación / filtros).
 * Usa `tipo_iniciador` real del iniciador, no `origen_tipo` del pool.
 */
export function poolDiaRowToIniciadorPendiente(row: IRutaPoolDiaRow): IRutaIniciadorPendienteRow {
  const iniId = Number(row.iniciador_id ?? row.iniciador_ruta_id);
  const tipoIniciador = row.tipo_iniciador ?? "INICIADOR";
  return {
    id: iniId,
    tipo_iniciador: tipoIniciador,
    tipo_iniciador_label: row.tipo_iniciador_label ?? null,
    estado_iniciador: "PENDIENTE",
    fecha_origen: row.fecha,
    prioridad: row.prioridad ?? null,
    prioridad_categoria: row.prioridad_categoria,
    prioridad_label: row.prioridad_label ?? null,
    turno_sugerido: null,
    domicilio_texto: row.domicilio_texto ?? null,
    distrito_id: row.distrito_id ?? null,
    distrito_nombre: row.distrito_nombre ?? null,
    rubro_nombre: row.rubro_nombre ?? null,
    nombre_fantasia: row.nombre_fantasia ?? null,
    angulo_esquina: row.angulo_esquina ?? null,
    detalle_operativo_items: row.detalle_operativo_items,
    detalle_operativo_texto: row.detalle_operativo_texto ?? null,
    motivo_denuncia: row.motivo_denuncia ?? null,
    causa: row.causa ?? null,
    prorroga_texto: row.prorroga_texto ?? null,
    badges: row.badges,
    identificadores: row.identificadores,
    domicilio: {
      id: row.domicilio_id ?? null,
      calle: null,
      numero: null,
      distrito_id: row.distrito_id ?? null,
      distrito_nombre: row.distrito_nombre ?? null,
      barrio_id: null,
      rubro: row.rubro_nombre ?? null,
    },
    origen: {
      tipo: row.origen_tipo ?? null,
      denuncia_id: null,
      relevamiento_id: null,
      notificacion_id: null,
      oficio_id: null,
      actuacion_id: row.actuacion_id ?? null,
    },
    observaciones: null,
  };
}

export function buildPoolControlMaps(items: IRutaPoolDiaRow[]) {
  const poolIniciadorIds: number[] = [];
  const poolRowsById: Record<number, IRutaIniciadorPendienteRow> = {};
  const poolIdByIniciadorId: Record<number, number> = {};

  for (const row of items) {
    const iniId = Number(row.iniciador_id ?? row.iniciador_ruta_id);
    if (!iniId || Number.isNaN(iniId)) continue;
    poolIniciadorIds.push(iniId);
    poolRowsById[iniId] = poolDiaRowToIniciadorPendiente(row);
    poolIdByIniciadorId[iniId] = row.pool_id;
  }

  return { poolIniciadorIds, poolRowsById, poolIdByIniciadorId };
}
