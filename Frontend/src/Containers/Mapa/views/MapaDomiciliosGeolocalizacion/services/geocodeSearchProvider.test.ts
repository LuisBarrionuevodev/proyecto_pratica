import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildSearchQuery,
  getGeocodeSearchProviderName,
  searchAddress,
  SMT_GEO_CONTEXT,
} from "./geocodeSearchProvider";

describe("geocodeSearchProvider", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.stubEnv("VITE_GEOCODE_SEARCH_PROVIDER", "nominatim");
  });

  it('buildSearchQuery("San Martín 1009") agrega contexto SMT', () => {
    expect(buildSearchQuery("San Martín 1009")).toBe(`San Martín 1009, ${SMT_GEO_CONTEXT}`);
  });

  it("buildSearchQuery no duplica contexto si ya incluye San Miguel", () => {
    const input = "San Martín 1009, San Miguel de Tucumán";
    expect(buildSearchQuery(input)).toBe(input);
  });

  it("buildSearchQuery no duplica contexto si ya incluye Tucumán", () => {
    const input = "Av. Sarmiento 500, Tucumán";
    expect(buildSearchQuery(input)).toBe(input);
  });

  it("buildSearchQuery no duplica contexto si ya incluye Argentina", () => {
    const input = "Calle 9 de Julio, Argentina";
    expect(buildSearchQuery(input)).toBe(input);
  });

  it("provider Nominatim arma query correcta", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          lat: "-26.8241",
          lon: "-65.2226",
          display_name: "San Martín 1009, San Miguel de Tucumán",
        },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchAddress("San Martín 1009");
    expect(result).toEqual({
      lat: -26.8241,
      lng: -65.2226,
      label: "San Martín 1009, San Miguel de Tucumán",
    });

    const calledUrl = String(fetchMock.mock.calls[0]?.[0]);
    expect(calledUrl).toContain("nominatim.openstreetmap.org/search");
    expect(decodeURIComponent(calledUrl)).toContain(SMT_GEO_CONTEXT);
    expect(decodeURIComponent(calledUrl)).toContain("San Martín 1009");
  });

  it("provider google lanza error controlado", async () => {
    vi.stubEnv("VITE_GEOCODE_SEARCH_PROVIDER", "google");
    expect(getGeocodeSearchProviderName()).toBe("google");
    await expect(searchAddress("San Martín 1009")).rejects.toThrow(/Google Geocode search/i);
    vi.stubEnv("VITE_GEOCODE_SEARCH_PROVIDER", "nominatim");
  });

  it("getGeocodeSearchProviderName default nominatim", () => {
    expect(getGeocodeSearchProviderName()).toBe("nominatim");
  });
});
