/**
 * Texto mostrado en bandejas (notificación / comprobación): persona física o razón social.
 * Orden: apellido+nombre si hay datos; si no, razón social; si no, "—".
 */
export function contribuyenteBandejaLabel(
  apellido?: string | null,
  nombre?: string | null,
  razonSocial?: string | null
): string {
  const a = (apellido ?? "").trim();
  const n = (nombre ?? "").trim();
  const nombreCompleto = [a, n].filter(Boolean).join(", ");
  if (nombreCompleto) return nombreCompleto;
  const rs = (razonSocial ?? "").trim();
  if (rs) return rs;
  return "—";
}
