import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import type { IEstablecimientoOperativoListItem } from "../../../api/establecimientosOperativosApi";

type DomicilioDetalleInput = Pick<
  IEstablecimientoOperativoListItem,
  "domicilio_texto" | "calle" | "calle_normalizada" | "numero"
>;

/**
 * Línea de domicilio visible en Establecimientos > Detalle (API normalizada o fallback local).
 */
export function establecimientoDomicilioLineaVisible(detalle: DomicilioDetalleInput): string {
  const fromApi = detalle.domicilio_texto?.trim();
  if (fromApi) return fromApi;
  const fallback = formatDomicilioLineaVisible({
    calle_normalizada: detalle.calle_normalizada,
    calle: detalle.calle,
    numero: detalle.numero,
  }).trim();
  return fallback || "—";
}
