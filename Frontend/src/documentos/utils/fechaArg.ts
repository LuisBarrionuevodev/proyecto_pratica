/** Fecha de ruta (YYYY-MM-DD) a texto corto es-AR para PDFs. */
export function fechaRutaLegiblePdf(fecha: string | null | undefined): string {
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
