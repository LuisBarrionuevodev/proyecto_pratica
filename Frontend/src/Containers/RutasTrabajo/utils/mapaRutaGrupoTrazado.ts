/**
 * Estilos de trazado por grupo para legibilidad en pantalla y en B/N (captura/impresión).
 * No dependen solo del color: patrón de trazo, grosor y código G1, G2… estable por id de grupo.
 */

/** Línea continua + distintos guiones (se distinguen sin color). */
export const POLYLINE_DASH_BY_INDEX: (string | undefined)[] = [
  undefined,
  "14 10",
  "6 10",
  "18 6 2 6",
  "10 5 1 5",
  "4 8",
  "20 8 4 8",
];

/** Grosor alternado (contraste al imprimir en escala de grises). */
export const POLYLINE_WEIGHT_BY_INDEX = [4, 3, 5, 4, 3, 5, 4];

/** Anillos externos del pin (blanco/negro) por índice — visibles sin cromática. */
export const MARKER_RING_BOXSHADOW: string[] = [
  "0 0 0 2px #ffffff, 0 0 0 4px #0a0a0a",
  "0 0 0 1px #0a0a0a, 0 0 0 3px #ffffff",
  "0 0 0 3px #ffffff, 0 0 0 5px #0a0a0a",
  "0 0 0 2px #0a0a0a",
  "0 0 0 1px #ffffff, 0 0 0 4px #0a0a0a",
  "0 0 0 2px #ffffff",
  "0 0 0 1px #0a0a0a, 0 0 0 3px #ffffff, 0 0 0 5px #0a0a0a",
];

/**
 * Orden estable de grupos por `id` y mapa id → G1, G2…
 */
export function buildGrupoCodigoPorId(grupoIds: number[]): Map<number, string> {
  const sorted = [...grupoIds].sort((a, b) => a - b);
  return new Map(sorted.map((id, i) => [id, `G${i + 1}`]));
}

/**
 * Índice de estilo (0..n-1) alineado al orden G1, G2… por id de grupo.
 */
export function grupoEstiloIndex(grupoId: number, grupoIdsSorted: number[]): number {
  const idx = grupoIdsSorted.indexOf(grupoId);
  return idx < 0 ? 0 : idx;
}

/** Nombre de grupo truncado para tooltips (evita saturar el mapa). */
export function grupoNombreEnMapa(nombre: string, maxLen = 14): string {
  const t = nombre.trim();
  if (!t) return "";
  if (t.length <= maxLen) return t;
  return `${t.slice(0, Math.max(1, maxLen - 1))}…`;
}
