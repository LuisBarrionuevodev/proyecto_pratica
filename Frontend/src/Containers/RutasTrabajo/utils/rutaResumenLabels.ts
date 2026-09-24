/** Etiquetas legibles para chips y resúmenes de ruta (solo presentación). */

export function turnoLabel(t: string): string {
  return t === "MANIANA" ? "Mañana" : t === "TARDE" ? "Tarde" : t;
}

export function estadoRutaVisible(estado: string | undefined): string | null {
  if (!estado?.trim()) return null;
  const e = estado.trim();
  if (e === "BORRADOR") return "Borrador";
  if (e === "PUBLICADA") return "Publicada";
  return e
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

export function fechaRutaLegible(fecha: string | null | undefined): string {
  if (!fecha?.trim()) return "—";
  try {
    return new Date(fecha + "T12:00:00").toLocaleDateString("es-AR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return fecha;
  }
}

/** Línea «Borrador · 2026-08-19 · Mañana · …» para paneles operativos. */
export function buildRutaContextoLine(
  ruta: { estado_ruta?: string; fecha?: string; turno?: string },
  suffix?: string | null
): string {
  const parts = [
    estadoRutaVisible(ruta.estado_ruta),
    ruta.fecha?.trim() || null,
    ruta.turno ? turnoLabel(ruta.turno) : null,
    suffix?.trim() || null,
  ].filter(Boolean) as string[];
  return parts.length > 0 ? parts.join(" · ") : "—";
}
