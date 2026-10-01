import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";

export type RutasListaTab = "borradores" | "publicadas";

export function rutasLabelTurno(t: IRutaTrabajo["turno"]): string {
  if (t === "MANIANA") return "Mañana";
  if (t === "TARDE") return "Tarde";
  return t;
}

export function rutasLabelEstadoRuta(estado: string): string {
  const e = (estado ?? "").trim();
  if (e === "BORRADOR") return "Borrador";
  if (e === "PUBLICADA") return "Publicada";
  return e || "—";
}

/** Texto compacto para fila desktop (botón ancho). */
export function rutasLabelFilaRutaListado(r: IRutaTrabajo): string {
  const estado = r.estado_ruta === "PUBLICADA" ? "" : ` · ${r.estado_ruta}`;
  return `Ruta ${r.numero} · ${rutasLabelTurno(r.turno)}${estado}`;
}

export function rutasFormatFechaListado(iso: string): string {
  const t = (iso ?? "").trim();
  if (!t) return "—";
  try {
    return new Intl.DateTimeFormat("es-AR", {
      weekday: "short",
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(`${t}T12:00:00`));
  } catch {
    return t;
  }
}
