import { contribuyenteBandejaLabel } from "../../../utils/contribuyenteBandejaText";
import type { ComprobacionExportRow } from "./comprobacionExportTypes";

const MOTIVO_PENDIENTE_PLACEHOLDER = "PENDIENTE";

export function normalizeMotivoKey(val: unknown): string {
  const key = String(val ?? "")
    .trim()
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ");
  if (!key || key === MOTIVO_PENDIENTE_PLACEHOLDER) return "";
  return key;
}

export function parseAnioMes(fecha: string | null | undefined): { anio: string; mes: string } {
  const f = (fecha ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}/.test(f)) return { anio: "", mes: "" };
  const [y, m] = f.slice(0, 10).split("-");
  return { anio: y, mes: m };
}

export function cellStr(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

export function domicilioFromParts(calle: unknown, numero: unknown): string {
  return [cellStr(calle), cellStr(numero)].filter(Boolean).join(" ");
}

export function contribuyenteFromParts(
  apellido: unknown,
  nombre: unknown,
  razonSocial?: unknown
): string {
  return contribuyenteBandejaLabel(
    cellStr(apellido) || null,
    cellStr(nombre) || null,
    cellStr(razonSocial) || null
  );
}

export function inspectoresFromParts(row: {
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
}): string {
  const texto = cellStr(row.inspectores_texto);
  if (texto) return texto;
  return [row.inspector1, row.inspector2, row.inspector3]
    .map((s) => cellStr(s))
    .filter(Boolean)
    .join(", ");
}

export function tieneExpedienteEnvio(row: ComprobacionExportRow): boolean {
  return Boolean(row.expedienteEnvioNumero || row.expedienteEnvioAnio);
}

export function tieneOficio(row: ComprobacionExportRow): boolean {
  return Boolean(row.oficioNumero || row.oficioAnio);
}

export function tieneExpedienteRespuesta(row: ComprobacionExportRow): boolean {
  return Boolean(row.expedienteRespuestaNumero || row.expedienteRespuestaAnio);
}

export function esCumplida(row: ComprobacionExportRow): boolean {
  return row.resultadoCumplimiento.toUpperCase() === "CUMPLE";
}

export function motivoExport(row: ComprobacionExportRow): string {
  const m = cellStr(row.comprobacionMotivo);
  if (!m || normalizeMotivoKey(m) === "") return "";
  return m;
}
