import type { IActuacionListItem } from "../../../api/actuacionesListApi";

export const GESTION_SIN_DATOS_LABEL = "Sin datos registrados";

function cleanPart(value: string | null | undefined): string {
  return (value ?? "").trim();
}

/** Línea de domicilio para bloque de contexto (detalle autorizado o fallback de grilla). */
export function formatGestionDomicilioLinea(row: IActuacionListItem): string {
  const nested = row.domicilio;
  const calle =
    cleanPart(nested?.calle) ||
    cleanPart(row.calle_cargada) ||
    cleanPart(row.calle_mostrar) ||
    cleanPart(row.calle);
  const numero = cleanPart(nested?.numero) || cleanPart(row.numero);
  const esquina =
    cleanPart(nested?.esquina) ||
    cleanPart(row.esquina_cargada) ||
    cleanPart(row.esquina_normalizada) ||
    cleanPart(row.esquina_raw);

  const parts: string[] = [];
  if (calle) parts.push(calle);
  if (numero) parts.push(numero);
  if (esquina) parts.push(esquina);

  return parts.join(" ").trim();
}

export function formatGestionRubroNombre(row: IActuacionListItem): string {
  const nested = cleanPart(row.rubro?.nombre);
  if (nested) return nested;
  return cleanPart(row.rubro_nombre);
}

export function formatGestionContribuyenteNombre(row: IActuacionListItem): string {
  const nestedAp = cleanPart(row.contribuyente?.apellido);
  const nestedNo = cleanPart(row.contribuyente?.nombre);
  if (nestedAp || nestedNo) {
    return [nestedAp, nestedNo].filter(Boolean).join(" ").trim();
  }
  const ap = cleanPart(row.contrib_apellido);
  const no = cleanPart(row.contrib_nombre);
  if (ap || no) return [ap, no].filter(Boolean).join(" ").trim();
  const rs = cleanPart(row.razon_social);
  return rs;
}

export function gestionContextoDisplayValue(text: string): string {
  return text.trim() ? text.trim() : GESTION_SIN_DATOS_LABEL;
}
