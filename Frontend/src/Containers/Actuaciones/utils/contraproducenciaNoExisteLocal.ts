function looseKey(s: string): string {
  return s
    .toUpperCase()
    .replace(/_/g, " ")
    .replace(/\//g, " ")
    .split(/\s+/)
    .join(" ")
    .trim()
    .normalize("NFD")
    .replace(/\u0300-\u036f/g, "");
}

const NO_EXISTE_LOCAL_KEYS = new Set(
  [
    "NO EXISTE",
    "NO EXISTE LOCAL",
    "NO EXISTE LOCAL",
    "NO EXISTE NO COINCIDE RUBRO",
    "NO EXISTE NO ES EL RUBRO",
    "NO_EXISTE_LOCAL",
  ].map(looseKey)
);

/**
 * Visita no realizada terminal (misma familia que backend `contraproducencia_es_familia_no_existe_local`).
 */
export function esFamiliaNoExisteLocalContraproducencia(value: string | null | undefined): boolean {
  const t = (value ?? "").trim();
  if (!t) return false;
  return NO_EXISTE_LOCAL_KEYS.has(looseKey(t));
}
