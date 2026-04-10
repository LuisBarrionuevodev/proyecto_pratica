import type { Periodo } from "../../../types/periodos";

function toIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

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
      desde = new Date(ref.getFullYear(), ref.getMonth(), 1);
      break;
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

  return { desde: toIsoDate(desde), hasta: toIsoDate(hasta) };
}
