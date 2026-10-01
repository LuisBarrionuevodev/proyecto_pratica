/**
 * Etiquetas de referencia en header de modales CRUD (OT, actuación).
 * Sin colores hardcodeados: el componente aplica `text.primary` del tema.
 */

export function formatCrudDialogOtReference(ot: string | null | undefined): string | null {
  const oRaw = (ot ?? "").trim();
  if (!oRaw || oRaw === "—") return null;
  return /^ot\b/i.test(oRaw) ? oRaw : `OT ${oRaw}`;
}

export function formatCrudDialogActuacionReference(actuacionId: number | null | undefined): string | null {
  if (actuacionId == null || !Number.isFinite(actuacionId) || actuacionId <= 0) return null;
  return `Actuación #${actuacionId}`;
}

export function resolveCrudDialogHeaderReference(
  ot: string | null | undefined,
  actuacionId?: number | null
): string | null {
  return formatCrudDialogOtReference(ot) ?? formatCrudDialogActuacionReference(actuacionId);
}
