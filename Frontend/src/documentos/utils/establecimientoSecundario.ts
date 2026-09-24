/**
 * Texto operativo de establecimiento para documentos PDF (sin dependencias de UI).
 */

export type EstablecimientoDiscriminadoresPdf = {
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
};

function trimOrNull(value: string | null | undefined): string | null {
  const t = value?.trim();
  return t || null;
}

/**
 * Línea secundaria opcional: «Nombre fantasía: X · Esquina: NE» o null.
 */
export function buildEstablecimientoSecundarioText(item: EstablecimientoDiscriminadoresPdf): string | null {
  const nf = trimOrNull(item.nombre_fantasia);
  const ang = trimOrNull(item.angulo_esquina);
  const parts: string[] = [];
  if (nf) parts.push(`Nombre fantasía: ${nf}`);
  if (ang) parts.push(`Esquina: ${ang}`);
  return parts.length ? parts.join(" · ") : null;
}

/**
 * Bloque multi-línea para órdenes de salida: solo dirección operativa y ángulo de esquina.
 * No incluye rubro, nombre fantasía ni otros datos de establecimiento (PR8.3).
 */
export function buildBloqueDireccionOperativaPdf(item: {
  domicilio_texto?: string | null;
  rubro_nombre?: string | null;
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
}): string {
  const dom = (item.domicilio_texto ?? "").trim() || "—";
  const ang = trimOrNull(item.angulo_esquina);
  const lines = [dom];
  if (ang) lines.push(`Ángulo: ${ang}`);
  return lines.join("\n");
}
