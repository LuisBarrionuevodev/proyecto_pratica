import type { IDetalleOperativoItem, IIniciadorOperativoCampos } from "../../api/rutasTrabajoApi";
import { detalleOperativoTexto } from "../../Containers/RutasTrabajo/utils/iniciadorDetalleOperativo";

const SEGMENTO_SEPARADOR = " · ";

function segmentoDesdeItem(item: IDetalleOperativoItem): string | null {
  const label = item.label?.trim() ?? "";
  const value = item.value?.trim() ?? "";
  if (!label && !value) return null;
  if (!label) return value;
  if (!value) return label.endsWith(":") ? label : `${label}:`;
  if (label.endsWith(":")) return `${label} ${value}`;
  return `${label}: ${value}`;
}

function segmentosDesdeItems(items: IDetalleOperativoItem[] | undefined): string[] {
  if (!items?.length) return [];
  return items.map(segmentoDesdeItem).filter((s): s is string => Boolean(s?.trim()));
}

/** Divide texto plano `label: valor · …` en segmentos atómicos. */
export function splitDetalleOperativoTexto(texto: string): string[] {
  return texto
    .split(SEGMENTO_SEPARADOR)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Segmentos de detalle operativo para PDF: cada entrada es label+valor unido (no separable al wrap).
 * Prioriza `detalle_operativo_items`; si no hay, divide `detalle_operativo_texto` por ` · `.
 */
export function buildDetalleOperativoPdfSegments(row: IIniciadorOperativoCampos): string[] {
  const desdeItems = segmentosDesdeItems(row.detalle_operativo_items);
  if (desdeItems.length) return desdeItems;

  const directo = row.detalle_operativo_texto?.trim();
  if (directo) return splitDetalleOperativoTexto(directo);

  const fallback = detalleOperativoTexto(row);
  if (!fallback) return [];
  return splitDetalleOperativoTexto(fallback);
}
