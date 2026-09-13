import type { Periodo } from "../../../types/periodos";
import { getOperativoMonthToDateRange, toIsoDateLocal } from "../../../utils/dateRange";

/**
 * Convierte el período UI en rango [desde, hasta] inclusive (referencia: hoy).
 */
export function periodoToDateRange(periodo: Periodo, ref: Date = new Date()): { desde: string; hasta: string } {
  const hasta = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate());
  let desde = new Date(hasta);

  switch (periodo) {
    case "Semanal":
      desde.setDate(desde.getDate() - 6);
      break;
    case "Mensual":
      return getOperativoMonthToDateRange(ref);
    case "Trimestral": {
      const qStart = Math.floor(ref.getMonth() / 3) * 3;
      desde = new Date(ref.getFullYear(), qStart, 1);
      break;
    }
    case "Anual":
      desde = new Date(ref.getFullYear(), 0, 1);
      break;
    default:
      break;
  }

  return { desde: toIsoDateLocal(desde), hasta: toIsoDateLocal(hasta) };
}
