import {
  notificacionEstadoOperativoLabel,
  type NotificacionEstadoOperativoPool,
} from "../Containers/GestionNotificacion/utils/notificacionEstadoOperativo";

export type EstadoOperativoPoolRowMeta = {
  estado_operativo_pool?: string | null;
  pool_fecha?: string | null;
  ruta_fecha?: string | null;
  ruta_numero?: number | null;
  ruta_turno?: string | null;
};

function normalizarEstado(value: string | null | undefined): NotificacionEstadoOperativoPool | "" {
  return (value ?? "").trim().toLowerCase() as NotificacionEstadoOperativoPool | "";
}

function formatFechaDisplay(iso: string | null | undefined): string | null {
  if (!iso?.trim()) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim());
  if (!m) return null;
  return `${m[3]}/${m[2]}/${m[1]}`;
}

function turnoDisplay(turno: string | null | undefined): string | null {
  const t = (turno ?? "").trim().toUpperCase();
  if (t === "MANIANA") return "Mañana";
  if (t === "TARDE") return "Tarde";
  return turno?.trim() || null;
}

function formatContextSuffix(row: EstadoOperativoPoolRowMeta): string {
  const fecha = formatFechaDisplay(row.pool_fecha ?? row.ruta_fecha);
  const ruta = row.ruta_numero != null ? `Ruta ${row.ruta_numero}` : null;
  const turno = turnoDisplay(row.ruta_turno);
  const turnoPart = turno ? `Turno ${turno}` : null;
  const parts = [fecha, ruta, turnoPart].filter(Boolean);
  if (!parts.length) return "";
  return ` (${parts.join(" - ")})`;
}

/**
 * Label visible de chip operativo pool/ruta (OPER-RUTA.6C).
 * El estado técnico `en_pool` se muestra como «En ruta (fecha - ruta - turno)».
 */
export function formatEstadoOperativoPoolLabel(row: EstadoOperativoPoolRowMeta): string {
  const estado = normalizarEstado(row.estado_operativo_pool);
  if (!estado) return "—";
  if (estado === "en_pool") {
    const suffix = formatContextSuffix(row);
    return suffix ? `En ruta${suffix}` : "En ruta";
  }
  if (estado === "en_ruta_borrador") {
    const suffix = formatContextSuffix(row);
    return suffix ? `En grupo asignado${suffix}` : "En grupo asignado";
  }
  if (estado === "en_ruta_publicada") {
    const suffix = formatContextSuffix(row);
    return suffix ? `En ruta publicada${suffix}` : "En ruta publicada";
  }
  return notificacionEstadoOperativoLabel(estado);
}
