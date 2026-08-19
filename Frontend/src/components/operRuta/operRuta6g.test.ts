import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.6G — selección exacta de ruta/turno", () => {
  const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");

  it("limpia ruta y grupo al cambiar turno o fecha", () => {
    expect(dialog).toContain("handleTurnoChange");
    expect(dialog).toContain("handleFechaChange");
    expect(dialog).toContain("resetRutaGrupo");
    expect(dialog).toContain("setTurno(nextTurno)");
    expect(dialog).toContain("resetRutaGrupo()");
  });

  it("confirma grupo usando selectedRutaId en agregar-desde-pool", () => {
    expect(dialog).toContain("const selectedRutaId = Number(rutaId)");
    expect(dialog).toContain("await agregarDesdePoolRuta(selectedRutaId");
    expect(dialog).not.toMatch(/agregarDesdePoolRuta\(Number\(operContext/);
  });

  it("crea pool con ruta_trabajo_id de la ruta seleccionada", () => {
    expect(dialog).toContain("ruta_trabajo_id: selectedRutaId");
    expect(dialog).toContain("resolverPoolId(");
    expect(dialog).toContain("selectedRutaId");
  });

  it("no auto-selecciona ruta si ya hay una incompatible", () => {
    expect(dialog).toContain("rutasFiltradas.length === 1 && !rutaId");
  });

  it("bloquea pool en otra ruta activa con mensaje claro", () => {
    expect(dialog).toContain("El pendiente ya está asociado a otra ruta activa");
    expect(dialog).toContain("poolRutaId !== selectedRutaId");
  });

  it("crear grupo usa createRutaGrupo(Number(rutaId)", () => {
    expect(dialog).toContain("createRutaGrupo(Number(rutaId)");
  });

  it("operContext no pisa ruta seleccionada al confirmar", () => {
    expect(dialog).not.toContain("operContext?.ruta_trabajo_id ?? Number(rutaId)");
    expect(dialog).toContain("operContext?.estado_operativo_pool ?? estadoOperativoPool");
  });
});
