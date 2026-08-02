import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("PR8.1 Actuaciones — filtros rango vs específica", () => {
  it("panel separa búsqueda específica y rango de fechas", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("Búsqueda específica");
    expect(src).toContain("Rango de fechas");
    expect(src).toContain("buildActuacionesFiltroPayload");
    expect(src).toContain("Combinar también con rango");
    expect(src).not.toContain('label="Orden de Trabajo"');
  });

  it("payload omite fechas en búsqueda específica sin combinar", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/Actuaciones/utils/buildActuacionesFiltroPayload.ts"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("useRangeModifiers");
    expect(src).toContain("orden_trabajo: null");
  });

  it("Limpiar resetea lista y formulario", () => {
    const filtro = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const container = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const filtroSrc = readFileSync(filtro, "utf8");
    const containerSrc = readFileSync(container, "utf8");
    expect(filtroSrc).toContain("setBusquedaEspecifica(\"\")");
    expect(filtroSrc).toContain("onLimpiarLista?.()");
    expect(containerSrc).toContain("onLimpiarLista={limpiarLista}");
  });

  it("meta muestra búsqueda q y no prioriza OT", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("meta.q");
    expect(src).not.toContain("<strong>OT:</strong>");
  });
});

describe("UX-FILTROS-NAV-2 Actuaciones", () => {
  it("no muestra Refrescar en filtros", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toContain("Refrescar");
    expect(src).not.toContain("onRefrescar");
  });

  it("entra en estado vacío inicial", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toMatch(/useEffect\(\(\) => \{\s*void buscar\(/);
    expect(src).not.toContain("Buscá por acta, domicilio");
    expect(src).toContain("hasSearched && meta");
  });

  it("Limpiar vuelve a estado inicial vacío", () => {
    const filtro = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const container = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const filtroSrc = readFileSync(filtro, "utf8");
    const containerSrc = readFileSync(container, "utf8");
    expect(filtroSrc).toContain("onLimpiarLista?.()");
    expect(containerSrc).toContain("onLimpiarLista={limpiarLista}");
  });
});

describe("UX-FILTROS-NAV-2 Establecimientos", () => {
  it("distrito y rubro usan AppSelect con nombre visible", () => {
    const path = resolve(process.cwd(), "src/Containers/Establecimientos/EstablecimientosListPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain('label="Distrito"');
    expect(src).toContain('label="Rubro"');
    expect(src).toContain("fetchDistritosCatalogo");
    expect(src).toContain("fetchRubrosCatalogoCached");
    expect(src).not.toContain('label="ID distrito"');
    expect(src).not.toContain('label="ID rubro"');
    expect(src).not.toContain("Refrescar");
  });

  it("envía distrito_id y rubro_id al API (conversión desde catálogo)", () => {
    const path = resolve(process.cwd(), "src/Containers/Establecimientos/EstablecimientosListPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("distrito_id: parseOptionalInt(applied.distrito_id)");
    expect(src).toContain("rubro_id: parseOptionalInt(applied.rubro_id)");
    expect(src).toContain("label: d.nombre");
    expect(src).toContain("label: r.nombre");
  });
});

describe("UX-FILTROS-NAV-2 Gestión usuarios", () => {
  it("solo Buscar y Limpiar", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/GestionDeUsuarios/Components/FiltroUsuarios.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("Buscar");
    expect(src).toContain("Limpiar");
    expect(src).not.toContain("Refrescar");
  });
});

describe("UX-FILTROS-NAV-2 Denuncias", () => {
  it("Limpiar no dispara onFiltrar con mes actual", () => {
    const path = resolve(process.cwd(), "src/Containers/Relevamientos/Components/FiltroDenuncias.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("onLimpiarLista?.()");
    expect(src).not.toMatch(/handleLimpiar[\s\S]*onFiltrar\(/);
  });
});

describe("UX-FILTROS-NAV-2 Relevamientos", () => {
  it("sin Refrescar en panel de filtros", () => {
    const path = resolve(process.cwd(), "src/Containers/Relevamientos/Components/FiltroRelevamientos.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toContain("Refrescar");
  });
});

describe("PR8.1b Historial Notificaciones", () => {
  it("inicia sin mes/año aplicado", () => {
    const path = resolve(process.cwd(), "src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain('useState<number | "">("")');
    expect(src).toContain("buildHistorialNotificacionFiltroPayload");
    expect(src).toContain("Búsqueda específica");
  });

  it("payload global no envía mes/año por defecto", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/GestionNotificacion/utils/buildHistorialNotificacionFiltroPayload.ts"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain('kind: "global"');
    expect(src).toContain("omitirRangoFecha: true");
  });

  it("Limpiar borra mes/año y búsqueda", () => {
    const path = resolve(process.cwd(), "src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain('setHistMes("")');
    expect(src).toContain('setHistNumNotif("")');
    expect(src).toContain("setHistorialApplied(null)");
  });
});

describe("PR8.1b Recorrido Comprobaciones", () => {
  it("inicia sin mes/año aplicado", () => {
    const path = resolve(process.cwd(), "src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain('useState<number | "">("")');
    expect(src).toContain("buildRecorridoComprobacionFiltroPayload");
  });

  it("payload usa omitir_rango_fecha en búsqueda global", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/ActasComprobacion/utils/buildRecorridoComprobacionFiltroPayload.ts"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("omitirRangoFecha = true");
  });

  it("Limpiar borra mes/año y búsqueda", () => {
    const path = resolve(process.cwd(), "src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain('setRecMes("")');
    expect(src).toContain('setRecExpediente("")');
    expect(src).toContain("setRecAppliedPayload(null)");
  });
});
