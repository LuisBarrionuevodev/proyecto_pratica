/** Bloque de acta/trámite del presenter de historial (PR10.4a / establecimientos-operativos). */
export type HistorialActaBlock = {
  numero?: string | null;
  anio?: number | null;
  texto?: string | null;
};

export type HistorialActasPayload = {
  inspeccion?: HistorialActaBlock | null;
  notificacion?: HistorialActaBlock | null;
  comprobacion?: HistorialActaBlock | null;
  clausura?: HistorialActaBlock | null;
  decomiso?: HistorialActaBlock | null;
};

export type HistorialTramitesPayload = {
  expediente?: HistorialActaBlock | null;
  oficio?: HistorialActaBlock | null;
};

function blockTexto(block: HistorialActaBlock | null | undefined): string {
  const t = (block?.texto ?? "").trim();
  return t;
}

/**
 * Etiquetas de chips alineadas a Actuaciones (actuacionActaChipsOnly + trámites básicos).
 * Orden: inspección → notificación → comprobación → clausura → decomiso → expediente → oficio.
 */
export function historialActasTramitesChipLabels(
  actas: HistorialActasPayload | null | undefined,
  tramites: HistorialTramitesPayload | null | undefined
): string[] {
  const out: string[] = [];
  const insp = blockTexto(actas?.inspeccion);
  if (insp) out.push(`Inspección ${insp}`);
  const notif = blockTexto(actas?.notificacion);
  if (notif) out.push(`Notificación ${notif}`);
  const comp = blockTexto(actas?.comprobacion);
  if (comp) out.push(`Comprobación ${comp}`);
  const claus = blockTexto(actas?.clausura);
  if (claus) out.push(`Clausura ${claus}`);
  const decom = blockTexto(actas?.decomiso);
  if (decom) out.push(`Decomiso N.º ${decom}`);
  const exp = blockTexto(tramites?.expediente);
  if (exp) out.push(`Expediente N.º ${exp}`);
  const ofi = blockTexto(tramites?.oficio);
  if (ofi) out.push(`Oficio N.º ${ofi}`);
  return out;
}
