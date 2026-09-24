/**
 * Inspectores en la grilla Glide de CargarActuaciones: lista canónica en `Inspectores`
 * (compatibilidad con slots Inspector 1–3 solo lectura / datos heredados).
 */
import type { GridRow } from "../../../api/gridApi";

const INSPECTORES_KEY = "Inspectores" as const;

/** Dedup preservando orden (alineado al backend). */
export function dedupeInspectoresPreserveOrder(names: string[]): string[] {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const n of names) {
        const t = n.trim();
        if (!t || seen.has(t)) continue;
        seen.add(t);
        out.push(t);
    }
    return out;
}

/**
 * Lista de inspectores para mostrar/editar: prioriza `Inspectores` (array);
 * si no hay, deriva de Inspector 1–3; acepta string legacy (coma-separado).
 */
export function getInspectoresListFromRow(row: GridRow): string[] {
    const raw = row[INSPECTORES_KEY] as unknown;
    if (Array.isArray(raw)) {
        return dedupeInspectoresPreserveOrder(raw.map((x) => String(x)));
    }
    if (typeof raw === "string" && raw.trim()) {
        return dedupeInspectoresPreserveOrder(raw.split(",").map((s) => s.trim()));
    }
    const slots = [
        row["Inspector 1"],
        row["Inspector 2"],
        row["Inspector 3"],
    ]
        .map((x) => (x == null ? "" : String(x).trim()))
        .filter(Boolean);
    return dedupeInspectoresPreserveOrder(slots);
}

const MAX_CELL_CHARS = 72;

/** Texto compacto para la celda (una sola columna). */
export function formatInspectoresCellDisplay(names: string[]): string {
    if (names.length === 0) return "";
    const full = names.join(", ");
    if (full.length <= MAX_CELL_CHARS) return full;
    return `${full.slice(0, MAX_CELL_CHARS - 1)}…`;
}
