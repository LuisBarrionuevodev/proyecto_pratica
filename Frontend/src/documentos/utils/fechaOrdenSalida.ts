/**
 * Texto de fecha para la línea derecha del formulario (es-AR).
 * Formato: día numérico, mes en minúsculas, año (p. ej. `30 de marzo de 2026`).
 */
export function fechaOrdenSalidaLegible(fechaIso: string): string {
  if (!fechaIso?.trim()) return "";
  try {
    const d = new Date(fechaIso + "T12:00:00");
    const day = d.getDate();
    const year = d.getFullYear();
    const month = d.toLocaleDateString("es-AR", { month: "long" });
    return `${day} de ${month} de ${year}`;
  } catch {
    return fechaIso;
  }
}
