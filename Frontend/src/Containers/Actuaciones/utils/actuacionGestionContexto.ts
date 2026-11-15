import type { IActuacionListItem } from "../../../api/actuacionesListApi";

export const GESTION_SIN_DATOS_LABEL = "Sin datos registrados";

function cleanPart(value: string | null | undefined): string {
  return (value ?? "").trim();
}

/** Línea de domicilio para bloque de contexto (detalle autorizado o fallback de grilla). */
export function formatGestionDomicilioLinea(row: IActuacionListItem): string {
  const nested = row.domicilio;
  const calleNormalizadaOk =
    String(row.calle_estado ?? "").trim().toUpperCase() === "OK"
      ? cleanPart(row.calle_normalizada)
      : "";
  const calle =
    cleanPart(row.calle_mostrar) ||
    calleNormalizadaOk ||
    cleanPart(row.calle) ||
    cleanPart(row.calle_cargada) ||
    cleanPart(nested?.calle);
  const numero = cleanPart(row.numero) || cleanPart(nested?.numero);
  const esquina =
    cleanPart(row.esquina_cargada) ||
    cleanPart(row.esquina_normalizada) ||
    cleanPart(row.numero_esquina) ||
    cleanPart(nested?.esquina) ||
    cleanPart(row.esquina_raw);

  const isEsquina = String(row.numero_tipo ?? "").trim().toUpperCase() === "ESQUINA";
  const parts: string[] = [];
  if (calle) parts.push(calle);
  if (isEsquina) {
    if (esquina) parts.push(esquina);
    else if (numero) parts.push(numero);
  } else {
    if (numero) parts.push(numero);
    if (esquina) parts.push(esquina);
  }

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
