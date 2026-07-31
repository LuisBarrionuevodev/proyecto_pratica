import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  establecimientoContribuyenteDocumentoLinea,
  establecimientoContribuyenteTitulo,
} from "./utils/establecimientoContribuyenteVisible";
import { establecimientoDomicilioLineaVisible } from "./utils/establecimientoDomicilioVisible";

const listPagePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "EstablecimientosListPage.tsx"
);

describe("establecimientos listado PR10.4b.6", () => {
  it("muestra columna Domicilio unificada", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain('header: "DOMICILIO"');
    expect(src).toContain("EstablecimientoListDomicilioCell");
    expect(src).not.toMatch(/accessorKey:\s*"calle"/);
    expect(src).not.toMatch(/accessorKey:\s*"numero"/);
    expect(src).not.toMatch(/header:\s*"CALLE"/);
    expect(src).not.toMatch(/header:\s*"NÚMERO"/);
    expect(src).not.toMatch(/header:\s*"DISTRITO"/);
  });

  it("muestra columna Contribuyente / Razón social unificada", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain('header: "CONTRIBUYENTE / RAZÓN SOCIAL"');
    expect(src).toContain("EstablecimientoContribuyenteCell");
    expect(src).not.toMatch(/accessorKey:\s*"contrib_nombre"/);
    expect(src).not.toMatch(/accessorKey:\s*"contrib_apellido"/);
    expect(src).not.toMatch(/accessorKey:\s*"documento"/);
    expect(src).not.toMatch(/header:\s*"NOMBRE"/);
    expect(src).not.toMatch(/header:\s*"APELLIDO"/);
    expect(src).not.toMatch(/header:\s*"DOCUMENTO"/);
  });

  it("mantiene navegación al detalle", () => {
    const src = readFileSync(listPagePath, "utf8");
    expect(src).toContain('navigate(`/establecimientos/${row.original.id}`)');
    expect(src).toContain("Ver ficha");
    expect(src).toContain('dsVariant="primary"');
  });

  it("domicilio prioriza domicilio_texto del API", () => {
    expect(
      establecimientoDomicilioLineaVisible({
        domicilio_texto: "San Martín 2869",
        calle: "raw",
        calle_normalizada: null,
        numero: "1",
      })
    ).toBe("San Martín 2869");
  });

  it("domicilio fallback usa normalizada antes que raw", () => {
    expect(
      establecimientoDomicilioLineaVisible({
        domicilio_texto: null,
        calle: "calle raw",
        calle_normalizada: "San Martín",
        numero: "2869",
      })
    ).toBe("San Martín 2869");
  });

  it("contribuyente muestra razón social con prioridad", () => {
    expect(
      establecimientoContribuyenteTitulo({
        razon_social: "Supermercado X SRL",
        contrib_apellido: "Monteros",
        contrib_nombre: "Pedro",
        documento: "30-12345678-9",
      })
    ).toBe("Supermercado X SRL");
  });

  it("contribuyente muestra nombre y apellido si no hay razón social", () => {
    expect(
      establecimientoContribuyenteTitulo({
        razon_social: null,
        contrib_apellido: "Monteros",
        contrib_nombre: "Pedro Arturo",
        documento: "42006775",
      })
    ).toBe("Monteros Pedro Arturo");
  });

  it("muestra DNI/CUIT debajo del titular", () => {
    expect(establecimientoContribuyenteDocumentoLinea("42006775")).toBe("DNI/CUIT: 42006775");
    expect(establecimientoContribuyenteDocumentoLinea("")).toBe("");
  });
});
