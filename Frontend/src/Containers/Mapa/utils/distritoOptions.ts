import distritosGeo from "../distritos.json";

/**
 * Opciones de distrito para AppSelect: valor numérico como string (id municipal) y etiqueta.
 * Se infieren desde nombres tipo "Distrito N" del GeoJSON local.
 */
export function buildDistritoSelectOptions(): { value: string; label: string }[] {
  const base = [{ value: "", label: "Todos los distritos" }];
  const fc = distritosGeo as { features?: { properties?: { nombre?: string } }[] };
  const features = fc.features ?? [];
  const parsed: { value: string; label: string }[] = [];
  for (const f of features) {
    const nombre = (f.properties as { nombre?: string } | null)?.nombre;
    if (!nombre) continue;
    const m = /^Distrito\s+(\d+)$/i.exec(nombre.trim());
    if (!m) continue;
    parsed.push({ value: m[1], label: nombre });
  }
  parsed.sort((a, b) => Number(a.value) - Number(b.value));
  return [...base, ...parsed];
}
