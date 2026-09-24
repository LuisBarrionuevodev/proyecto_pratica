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
  "NO SE RATIFICÓ",
  "NO PAGÓ TODAVÍA EL DECOMISO",
];

describe("contraproducenciasPorTipoIniciador", () => {
  it("excluye NO_HUBO del catálogo de Completar trabajo", () => {
    const out = filtrarContraproducenciasPorTipoIniciador(CATALOG, "RELEVAMIENTO");
    expect(out.some((x) => x.toUpperCase().includes("NO_HUBO"))).toBe(false);
  });

  it("reinspección oficio no incluye correctivas de rubro", () => {
    const out = filtrarContraproducenciasPorTipoIniciador(CATALOG, "REINSPECCION_OFICIO");
    expect(out).toContain("LOCAL CERRADO");
    expect(out).toContain("NO SE RATIFICÓ");
    expect(out).toContain("NO PAGÓ TODAVÍA EL DECOMISO");
    expect(out).not.toContain("NO ES EL RUBRO");
    expect(out).not.toContain("DIRECCION INCORRECTA");
  });

  it("reinspección notificación no incluye contras exclusivas de oficio", () => {
    const out = filtrarContraproducenciasPorTipoIniciador(CATALOG, "REINSPECCION_NOTIFICACION");
    expect(out).not.toContain("NO SE RATIFICÓ");
    expect(out).not.toContain("NO PAGÓ TODAVÍA EL DECOMISO");
  });

  it("filtra contras de oficio por subtipo de actuación", () => {
    const clausura = filtrarContraproducenciasPorTipoIniciador(
      CATALOG,
      "REINSPECCION_OFICIO",
      null,
      "RATIFICACION DE CLAUSURA"
    );
    expect(clausura).toContain("NO SE RATIFICÓ");
    expect(clausura).not.toContain("NO PAGÓ TODAVÍA EL DECOMISO");

    const decomiso = filtrarContraproducenciasPorTipoIniciador(
      CATALOG,
      "REINSPECCION_OFICIO",
      null,
      "RATIFICACION DE DECOMISO"
    );
    expect(decomiso).toContain("NO PAGÓ TODAVÍA EL DECOMISO");
    expect(decomiso).not.toContain("NO SE RATIFICÓ");
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
