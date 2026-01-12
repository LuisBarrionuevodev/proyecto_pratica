import type { ILocal } from "../types/Local";

export function filterLocales(
  locales: ILocal[],
  distrito: string,
  search: string
) {
  return locales.filter((l) => {
    if (distrito && l.distrito !== distrito) return false;
    if (search && !l.nombre.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });
}
