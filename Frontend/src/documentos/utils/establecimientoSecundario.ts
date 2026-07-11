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
 * Bloque multi-línea para órdenes de salida (domicilio + rubro + discriminadores).
 */
export function buildBloqueDireccionOperativaPdf(item: {
  domicilio_texto?: string | null;
  rubro_nombre?: string | null;
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
}): string {
  const dom = (item.domicilio_texto ?? "").trim() || "—";
  const rubro = (item.rubro_nombre ?? "").trim();
  const sec = buildEstablecimientoSecundarioText(item);
  const lines = [dom];
  if (rubro) lines.push(rubro);
  if (sec) lines.push(sec);
  return lines.join("\n");
}
