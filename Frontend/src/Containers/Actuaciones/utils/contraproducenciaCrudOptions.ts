import type { IActuacionListItem } from "../../../api/actuacionesListApi";

function trim(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

function looseKey(s: string): string {
  return s
    .toUpperCase()
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim();
}

/**
 * True si el usuario borró contraproducencia que existía al abrir edición.
 */
export function detectContraproducenciaClearedByUser(
  original: IActuacionListItem,
  draft: IActuacionListItem
): boolean {
  return Boolean(trim(original.contraproducencia)) && !trim(draft.contraproducencia);
}

/**
 * Marca `limpiar_contraproducencia` para el PUT cuando corresponde corrección de cierre.
 */
export function applyContraproducenciaClearFlag(
  original: IActuacionListItem | null | undefined,
  row: IActuacionListItem
): IActuacionListItem {
  if (!original || !detectContraproducenciaClearedByUser(original, row)) {
    return row;
  }
  return {
    ...row,
    limpiar_contraproducencia: true,
    contraproducencia: null,
  };
}

function mergeCatalogValue(catalog: string[], current: string | null | undefined): string[] {
  const cur = trim(current);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const name of catalog) {
    const t = trim(name);
    if (!t || seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  if (cur && !seen.has(cur)) {
    out.unshift(cur);
  }
  return out;
}

/**
 * Opciones de contraproducencia para edición CRUD (sin NO_HUBO salvo valor legacy guardado).
 */
export function buildContraproducenciaCrudSelectOptions(
  catalog: string[],
  valorGuardado: string | null | undefined
): { value: string; label: string }[] {
  const merged = mergeCatalogValue(catalog, valorGuardado).filter((n) => {
    if (looseKey(n) !== looseKey("NO_HUBO")) return true;
    return looseKey(valorGuardado ?? "") === looseKey("NO_HUBO");
  });

  return [
    { value: "", label: "Sin contraproducencia (visita realizada)" },
    ...merged.map((n) => ({ value: n, label: n })),
  ];
}
