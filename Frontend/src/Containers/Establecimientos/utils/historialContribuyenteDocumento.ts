/**
 * Validación mínima de DNI/CUIT para búsqueda de historial (normalización en backend).
 */
export function documentoHistorialInputValid(raw: string): boolean {
  const trimmed = raw.trim();
  if (!trimmed) return false;
  return /\d/.test(trimmed);
}

export const MSG_DOCUMENTO_HISTORIAL_VACIO = "Ingresá un DNI/CUIT para consultar el historial.";
