/**
 * Búsqueda de direcciones para geolocalización manual (PR6C.5).
 * Provider desacoplado: Nominatim hoy; Google Places futuro vía feature flag.
 */

export const SMT_GEO_CONTEXT = "San Miguel de Tucumán, Tucumán, Argentina";

export type GeocodeSearchProviderName = "nominatim" | "google";

export interface GeocodeSearchResult {
  lat: number;
  lng: number;
  label: string;
}

const NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search";

/**
 * Agrega contexto SMT si el input no lo trae ya.
 */
export function buildSearchQuery(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) return "";

  const lower = trimmed.toLowerCase();
  const hasContext =
    lower.includes("san miguel") ||
    lower.includes("tucumán") ||
    lower.includes("tucuman") ||
    lower.includes("argentina");

  if (hasContext) return trimmed;
  return `${trimmed}, ${SMT_GEO_CONTEXT}`;
}

export function getGeocodeSearchProviderName(): GeocodeSearchProviderName {
  const raw = (import.meta.env.VITE_GEOCODE_SEARCH_PROVIDER ?? "nominatim").trim().toLowerCase();
  return raw === "google" ? "google" : "nominatim";
}

async function searchWithNominatim(input: string): Promise<GeocodeSearchResult | null> {
  const query = buildSearchQuery(input);
  if (!query) return null;

  const url = `${NOMINATIM_SEARCH_URL}?format=json&q=${encodeURIComponent(query)}&limit=1`;
  const resp = await fetch(url, { headers: { "Accept-Language": "es" } });
  if (!resp.ok) {
    throw new Error(`Nominatim respondió ${resp.status}`);
  }

  const data: unknown = await resp.json();
  if (!Array.isArray(data) || !data[0]) return null;

  const first = data[0] as { lat?: string; lon?: string; display_name?: string };
  const lat = parseFloat(String(first.lat ?? ""));
  const lng = parseFloat(String(first.lon ?? ""));
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;

  return {
    lat,
    lng,
    label: String(first.display_name ?? query),
  };
}

async function searchWithGoogleStub(_input: string): Promise<GeocodeSearchResult | null> {
  throw new Error(
    "Google Geocode search no está habilitado todavía. Use VITE_GEOCODE_SEARCH_PROVIDER=nominatim."
  );
}

/**
 * Busca una dirección con el provider configurado.
 */
export async function searchAddress(input: string): Promise<GeocodeSearchResult | null> {
  const provider = getGeocodeSearchProviderName();
  if (provider === "google") {
    return searchWithGoogleStub(input);
  }
  return searchWithNominatim(input);
}
