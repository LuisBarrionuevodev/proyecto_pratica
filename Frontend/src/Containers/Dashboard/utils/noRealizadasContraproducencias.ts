import type {
  IndicadoresContraproducenciaResumenItem,
  IndicadoresNoRealizadasResponse,
} from "../../../api/indicadoresApi";

export type ContraproducenciaResumenRow = {
  contraproducencia: string;
  cantidad: number;
  porcentaje: number;
};

export type ContraproducenciasResumen = {
  total: number;
  rows: ContraproducenciaResumenRow[];
};

/** Excluye NO_HUBO del ranking (misma regla que backend). */
export function isNoHuboContraproducencia(label: string): boolean {
  const n = label.trim().toUpperCase().replace(/_/g, " ");
  return n === "NO HUBO" || n === "NOHUBO";
}

/** Total general: campo dedicado del backend o suma de `contraproducencias_resumen`. */
export function calcTotalNoRealizadas(
  data: IndicadoresNoRealizadasResponse | null | undefined
): number {
  if (!data) return 0;
  if (typeof data.total === "number") {
    return data.total;
  }
  return (data.contraproducencias_resumen ?? []).reduce((acc, r) => acc + r.cantidad, 0);
}

function pct(cantidad: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((cantidad / total) * 1000) / 10;
}

function rowsFromBackendResumen(
  items: IndicadoresContraproducenciaResumenItem[],
  total: number
): ContraproducenciaResumenRow[] {
  return items.map((r) => ({
    contraproducencia: r.label,
    cantidad: r.cantidad,
    porcentaje: pct(r.cantidad, total),
  }));
}

/**
 * Arma el resumen por contraproducencia (5 buckets fijos) para UI/PDF/Excel.
 */
export function buildContraproducenciasResumen(
  data: IndicadoresNoRealizadasResponse | null | undefined
): ContraproducenciasResumen {
  const total = calcTotalNoRealizadas(data);
  if (!data || total <= 0) {
    return { total: 0, rows: [] };
  }

  if (data.contraproducencias_resumen?.length) {
    return {
      total,
      rows: rowsFromBackendResumen(data.contraproducencias_resumen, total),
    };
  }

  return { total, rows: [] };
}

export function formatPorcentajeNoRealizadas(porcentaje: number): string {
  return `${porcentaje.toLocaleString("es-AR", { maximumFractionDigits: 1 })}%`;
}
