import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildRutaPublicadaDocumentModel } from "./buildRutaPublicadaDocumentModel";
import {
  buildBloqueDireccionOperativaPdf,
  buildEstablecimientoSecundarioText,
} from "../utils/establecimientoSecundario";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

const rutaBase: IRutaTrabajo = {
  id: 1,
  fecha: "2026-07-11",
  turno: "MANIANA",
  estado_ruta: "PUBLICADA",
  numero: 3,
  observaciones: null,
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

const grupoBase: IRutaGrupoMin = {
  id: 10,
  ruta_trabajo_id: 1,
  nombre: "Grupo 1",
  estado: "ACTIVO",
  inspectores: [
    { id: 1, inspector_id: 100, inspector_nombre: "Pérez, Juan", inspector_legajo: "1234" },
  ],
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

function itemBase(overrides: Partial<IRutaItemMin> = {}): IRutaItemMin {
  return {
    id: 501,
    ruta_trabajo_id: 1,
    ruta_grupo_id: 10,
    iniciador_ruta_id: 200,
    tipo_iniciador: "RELEVAMIENTO",
    orden_trabajo_id: null,
    actuacion_id: null,
    orden_trabajo: null,
    estado_ruta_item: "ASIGNADO",
    deleted_at: null,
    domicilio_texto: "San Martín Y Maipú",
    distrito_nombre: "Centro",
    rubro_nombre: "Carnicería",
    ...overrides,
  };
}

describe("PR7.10 buildEstablecimientoSecundarioText", () => {
  it("arma línea con nombre y ángulo", () => {
    expect(
      buildEstablecimientoSecundarioText({ nombre_fantasia: "El Toro", angulo_esquina: "NE" })
    ).toBe("Nombre fantasía: El Toro · Esquina: NE");
  });

  it("retorna null sin datos", () => {
    expect(buildEstablecimientoSecundarioText({ nombre_fantasia: null, angulo_esquina: "" })).toBeNull();
  });
});

describe("PR7.10 buildBloqueDireccionOperativaPdf", () => {
  it("orden salida: domicilio e intersección con ángulo", () => {
    const bloque = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "San Martín Y Maipú",
      rubro_nombre: "Carnicería",
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    expect(bloque).toBe("San Martín Y Maipú\nÁngulo: NE");
  });

  it("orden salida: calle+número sin ángulo", () => {
    const bloque = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "Maipú 500",
      rubro_nombre: "Panadería",
    });
    expect(bloque).toBe("Maipú 500");
    expect(bloque).not.toContain("null");
    expect(bloque).not.toContain("undefined");
  });
});

describe("PR7.10 buildRutaPublicadaDocumentModel", () => {
  it("incluye nombre_fantasia y angulo_esquina en filas de grupo", () => {
    const item = itemBase({
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [item]);
    const fila = model.grupos[0]?.items[0];
    expect(fila?.nombreFantasia).toBe("El Toro");
    expect(fila?.anguloEsquina).toBe("NE");
    expect(fila?.establecimientoSecundario).toBe("Nombre fantasía: El Toro · Esquina: NE");
  });

  it("sin datos no incluye establecimientoSecundario", () => {
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [itemBase()]);
    const fila = model.grupos[0]?.items[0];
    expect(fila?.establecimientoSecundario).toBeNull();
    expect(fila?.nombreFantasia).toBeNull();
    expect(fila?.anguloEsquina).toBeNull();
  });

  it("órdenes de salida: solo dirección y ángulo", () => {
    const item = itemBase({
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [item]);
    const salida = model.inspectoresSalida[0];
    expect(salida?.direccionesRuta[0]).toBe("San Martín Y Maipú\nÁngulo: NE");
    expect(salida?.direccionesRuta[0]).not.toContain("Carnicería");
    expect(salida?.direccionesRuta[0]).not.toContain("fantasía");
  });

  it("distingue dos ítems misma esquina con distinto ángulo", () => {
    const itemA = itemBase({
      id: 501,
      rubro_nombre: "Carnicería",
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    const itemB = itemBase({
      id: 502,
      rubro_nombre: "Verdulería",
      nombre_fantasia: null,
      angulo_esquina: "SO",
    });
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], [itemA, itemB]);
    const dirs = model.inspectoresSalida[0]?.direccionesRuta ?? [];
    expect(dirs).toHaveLength(2);
    expect(dirs[0]).toBe("San Martín Y Maipú\nÁngulo: NE");
    expect(dirs[1]).toBe("San Martín Y Maipú\nÁngulo: SO");
    expect(dirs[0]).not.toBe(dirs[1]);
  });
});

describe("PR7.10 PDF renderers", () => {
  it("RutaResumenPdfDocument renderiza establecimientoSecundario", () => {
    const src = read("src/documentos/renderers/RutaResumenPdfDocument.tsx");
    expect(src).toContain("establecimientoSecundario");
    expect(src).toContain("tableBodyCellSecondary");
  });

  it("OrdenesSalidaPdfDocument usa direccionesRuta multi-línea del modelo", () => {
    const src = read("src/documentos/renderers/OrdenesSalidaPdfDocument.tsx");
    expect(src).toContain("direccionesRuta.join");
    expect(src).toContain("textoDirecciones");
  });
});

describe("PR7.10 Completar Trabajo intacto", () => {
  it("documentos no tocan completar trabajo", () => {
    const src = read("src/documentos/builders/buildRutaPublicadaDocumentModel.ts");
    expect(src).not.toContain("CompletarTrabajo");
    expect(src).not.toContain("nombre_local");
  });
});
