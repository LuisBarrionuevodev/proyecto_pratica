import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  relevamientoDistritoDisplay,
  relevamientoOrientacionLinea,
  relevamientoRelevadoresLineas,
  relevamientoTurnoDisplay,
} from "./utils/relevamientoCrudDisplay";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("REL-GESTION-RELEVAMIENTOS.2 — tabla y filtros", () => {
  it("relevadores múltiples en líneas separadas con turno del relevamiento", () => {
    const lineas = relevamientoRelevadoresLineas({
      id: 1,
      fecha: "2026-06-01",
      calle: "X",
      numero: "1",
      rubro: "Pan",
      relevadores: [
        { id: 1, nombre: "Fabian Esquivel" },
        { id: 2, nombre: "Juan Pérez" },
      ],
    });
    expect(lineas).toBe("Fabian Esquivel\nJuan Pérez");
    expect(relevamientoTurnoDisplay("MANIANA")).toBe("Mañana");
    expect(relevamientoTurnoDisplay("TARDE")).toBe("Tarde");
  });

  it("orientación bajo rubro y distrito_mostrar con fallback", () => {
    expect(
      relevamientoOrientacionLinea({
        id: 1,
        fecha: null,
        calle: "X",
        numero: "y Y",
        numero_tipo: "ESQUINA",
        rubro: "Carnicería",
        angulo_esquina: "NE",
      })
    ).toBe("Orientación: NE");
    expect(
      relevamientoOrientacionLinea({
        id: 1,
        fecha: null,
        calle: "X",
        numero: "100",
        numero_tipo: "NUMERO",
        rubro: "Carnicería",
        angulo_esquina: "NE",
      })
    ).toBeNull();
    expect(relevamientoDistritoDisplay({ id: 1, fecha: null, calle: "X", numero: "1", rubro: "R", distrito_mostrar: "Distrito 1" })).toBe("Distrito 1");
    expect(relevamientoDistritoDisplay({ id: 1, fecha: null, calle: "X", numero: "1", rubro: "R", distrito_mostrar: null })).toBe("—");
  });

  it("TableRelevamientos: columnas y relevador+turno", () => {
    const src = read("Containers/Relevamientos/Components/TableRelevamientos.tsx");
    expect(src).toContain('header: "Relevador"');
    expect(src).toContain("relevamientoRelevadoresLineas");
    expect(src).toContain("relevamientoTurnoDisplay(row.original.turno)");
    expect(src).not.toContain('accessorKey: "angulo_esquina"');
    expect(src).not.toContain('accessorKey: "turno"');
    expect(src).toContain('header: "Está abierto"');
    expect(src).toContain('accessorKey: "distrito_mostrar"');
    expect(src).toContain("relevamientoDistritoDisplay");
    expect(src).toContain('header: "Domicilio"');
  });

  it("FiltroRelevamientos envía esta_abierto y distrito_id al backend", () => {
    const filtro = read("Containers/Relevamientos/Components/FiltroRelevamientos.tsx");
    expect(filtro).toContain("fetchDistritosCatalogo");
    expect(filtro).toContain('label="Está abierto"');
    expect(filtro).toContain('label="Distrito"');
    expect(filtro).toContain('esta_abierto: estaAbiertoParsed');
    expect(filtro).toContain("distrito_id: distritoParsed");
    expect(filtro).toContain('setEstaAbierto("")');
    expect(filtro).toContain('setDistritoId("")');
  });

  it("relevamientosListApi serializa filtros nuevos", () => {
    const api = read("api/relevamientosListApi.ts");
    expect(api).toContain('params.esta_abierto = "true"');
    expect(api).toContain("params.distrito_id = String(filters.distrito_id)");
  });

  it("RelevamientosContainer reinicia paginación al filtrar", () => {
    const container = read("Containers/Relevamientos/RelevamientosContainer.tsx");
    expect(container).toContain("page: 1");
    expect(container).toContain("esta_abierto: filtros.esta_abierto");
    expect(container).toContain("distrito_id: filtros.distrito_id");
  });
});
