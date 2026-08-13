/** Labels read-only de estado operativo pool/ruta (OPER-RUTA.3). */

export type NotificacionEstadoOperativoPool =
  | "pendiente"
  | "en_pool"
  | "en_ruta_borrador"
  | "en_ruta_publicada"
  | "resuelto"
  | "no_elegible";

const LABELS: Record<NotificacionEstadoOperativoPool, string> = {
  pendiente: "Pendiente",
  en_pool: "En pool",
  en_ruta_borrador: "En ruta borrador",
  en_ruta_publicada: "En ruta publicada",
  resuelto: "Resuelto",
  no_elegible: "No elegible",
};

export function notificacionEstadoOperativoLabel(
  value: string | null | undefined
): string {
  const key = (value ?? "").trim().toLowerCase() as NotificacionEstadoOperativoPool;
  return LABELS[key] ?? "—";
}

export function notificacionEstadoOperativoChipColor(
  value: string | null | undefined
): "default" | "info" | "warning" | "success" | "error" {
  const key = (value ?? "").trim().toLowerCase();
  if (key === "pendiente") return "info";
  if (key === "en_pool") return "warning";
  if (key === "en_ruta_borrador") return "warning";
  if (key === "en_ruta_publicada") return "error";
  if (key === "resuelto") return "success";
  if (key === "no_elegible") return "default";
  return "default";
}
