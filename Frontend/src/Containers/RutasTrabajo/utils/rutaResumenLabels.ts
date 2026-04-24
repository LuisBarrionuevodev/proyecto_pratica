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
