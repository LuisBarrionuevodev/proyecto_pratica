import { describe, expect, it } from "vitest";

import {
  contraproducenciaPermitidaCompletarTrabajo,
  filtrarContraproducenciasPorTipoIniciador,
} from "./contraproducenciasPorTipoIniciador";

const CATALOG = [
  "LOCAL CERRADO",
  "CLIMA",
  "ZONA ROJA",
  "NO_HUBO",
  "OTROS",
  "NO ES EL RUBRO",
  "DIRECCION INCORRECTA",
  "NO EXISTE/NO ES EL RUBRO",
  "NO PERMITE INSPECCION",
];

describe("contraproducenciasPorTipoIniciador", () => {
  it("excluye NO_HUBO del catálogo de Completar trabajo", () => {
    const out = filtrarContraproducenciasPorTipoIniciador(CATALOG, "RELEVAMIENTO");
    expect(out.some((x) => x.toUpperCase().includes("NO_HUBO"))).toBe(false);
  });

  it("reinspección oficio no incluye correctivas de rubro", () => {
    const out = filtrarContraproducenciasPorTipoIniciador(CATALOG, "REINSPECCION_OFICIO");
    expect(out).toContain("LOCAL CERRADO");
    expect(out).not.toContain("NO ES EL RUBRO");
    expect(out).not.toContain("DIRECCION INCORRECTA");
  });

  it("conserva valor legacy guardado aunque no esté en el set del tipo", () => {
    const out = filtrarContraproducenciasPorTipoIniciador(CATALOG, "REINSPECCION_OFICIO", "ZONA ROJA");
    expect(out).toContain("ZONA ROJA");
  });

  it("NO_HUBO no es permitido en Completar trabajo", () => {
    expect(contraproducenciaPermitidaCompletarTrabajo("RELEVAMIENTO", "NO_HUBO")).toBe(false);
    expect(contraproducenciaPermitidaCompletarTrabajo("RELEVAMIENTO", "LOCAL CERRADO")).toBe(true);
  });
});
