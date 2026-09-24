/**
 * Formato compacto para totales en donuts y KPIs del dashboard (evita desborde visual).
 */

export function formatDashboardCompactCount(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} mill`;
  }
  if (n >= 10_000) {
    return `${(n / 1_000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} mil`;
  }
  return n.toLocaleString("es-AR");
}

export function formatDashboardKgCompact(kg: number): { main: string; suffix: string } {
  if (kg >= 10_000) {
    return {
      main: (kg / 1000).toLocaleString("es-AR", { maximumFractionDigits: 1 }),
      suffix: "mil kg",
    };
  }
  const main =
    kg >= 1000
      ? kg.toLocaleString("es-AR", { maximumFractionDigits: 0 })
      : kg.toLocaleString("es-AR", { maximumFractionDigits: kg % 1 === 0 ? 0 : 1 });
  return { main, suffix: "kg" };
}

/** Tamaño de fuente para valor centrado según longitud del texto. */
export function donutCenterFontSize(text: string): string {
  const len = text.length;
  if (len > 12) return "0.72rem";
  if (len > 9) return "0.88rem";
  if (len > 7) return "1rem";
  return "1.2rem";
}
