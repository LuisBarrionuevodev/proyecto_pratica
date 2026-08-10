import { describe, expect, it } from "vitest";

import {
  MAPA_TIPO_INICIADOR_OPTIONS,
  mapaRealizadosEmptyMessage,
  mapaRealizadosTipoQueryValue,
} from "./mapaOperativo";
describe("mapaOperativo — filtros Realizados", () => {
  it("opciones alineadas a tipos operativos de Actuaciones", () => {
    expect(MAPA_TIPO_INICIADOR_OPTIONS).toEqual([
      { value: "TODOS", label: "Todos" },
      { value: "INSPECCION", label: "Inspección" },
      { value: "REINSPECCION", label: "Reinspección" },
      { value: "RATIFICACION_CLAUSURA", label: "Ratificación de clausura" },
      { value: "RATIFICACION_DECOMISO", label: "Ratificación de decomiso" },
      { value: "VERIFICAR_INFORMAR", label: "Verificar e informar" },
    ]);
  });

  it("no muestra Denuncia, Transporte, Oficio ni Notificación", () => {
    const labels = MAPA_TIPO_INICIADOR_OPTIONS.map((o) => o.label);
    const values = MAPA_TIPO_INICIADOR_OPTIONS.map((o) => o.value);
    expect(labels).not.toContain("Denuncia");
    expect(labels).not.toContain("Transporte");
    expect(labels).not.toContain("Oficio");
    expect(labels).not.toContain("Notificación");
    expect(values).not.toContain("DENUNCIAS");
    expect(values).not.toContain("OFICIO");
    expect(values).not.toContain("NOTIFICACION");
  });

  it("mapaRealizadosTipoQueryValue omite vacío y TODOS", () => {
    expect(mapaRealizadosTipoQueryValue("")).toBeUndefined();
    expect(mapaRealizadosTipoQueryValue("TODOS")).toBeUndefined();
    expect(mapaRealizadosTipoQueryValue("REINSPECCION")).toBe("REINSPECCION");
  });

  it("mapaRealizadosEmptyMessage distingue filtro activo", () => {
    expect(mapaRealizadosEmptyMessage({ tipo: "REINSPECCION" })).toContain("Reinspección");
    expect(mapaRealizadosEmptyMessage({ tipo: "TODOS" })).toContain("geocode");
  });
});
