import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { contraproducenciaBandejaSegment, tipoActuacionBandejaSegment } from "../Actuaciones/Components/bandejaTableCells";

const detallePagePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "EstablecimientoDetallePage.tsx"
);

describe("establecimiento historial columnas PR10.4b.4", () => {
  it("incluye columna Inspectores después de Tipo de actuación", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).toContain('header: "INSPECTORES"');
    expect(src).toContain("HistorialInspectoresCell");
    const tipoIdx = src.indexOf('header: "TIPO DE ACTUACIÓN"');
    const inspIdx = src.indexOf('header: "INSPECTORES"');
    const actasIdx = src.indexOf('header: "ACTAS Y TRÁMITES"');
    expect(tipoIdx).toBeGreaterThan(-1);
    expect(inspIdx).toBeGreaterThan(tipoIdx);
    expect(actasIdx).toBeGreaterThan(inspIdx);
  });

  it("mantiene columnas Fecha, Tipo y Actas y trámites", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).toContain('header: "FECHA"');
    expect(src).toContain('header: "TIPO DE ACTUACIÓN"');
    expect(src).toContain('header: "ACTAS Y TRÁMITES"');
    expect(src).toContain("HistorialActasTramitesCell");
    expect(src).toContain("BandejaTipoActuacionChipCell");
  });
});

describe("establecimiento historial columnas PR10.4b.2/PR10.4b.3", () => {
  it("incluye columna Actas y trámites", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).toContain('header: "ACTAS Y TRÁMITES"');
    expect(src).toContain("HistorialActasTramitesCell");
  });

  it("no incluye columnas removidas", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).not.toMatch(/accessorKey:\s*"contraproducencia"/);
    expect(src).not.toMatch(/accessorKey:\s*"nombre_local"/);
    expect(src).not.toMatch(/accessorKey:\s*"orden_trabajo_numero"/);
    expect(src).not.toMatch(/accessorKey:\s*"acta_inspeccion_num"/);
  });

  it("tipo de actuación pasa contraproducencia al chip compartido", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).toMatch(/BandejaTipoActuacionChipCell[\s\S]*contraproducencia=\{row\.original\.contraproducencia\}/);
    expect(tipoActuacionBandejaSegment("REINSPECCION")).toBe("Tipo: REINSPECCION");
    expect(contraproducenciaBandejaSegment("LOCAL CERRADO")).toBe("Contraproducencia: LOCAL CERRADO");
    expect(contraproducenciaBandejaSegment(null)).toBe("");
  });
});

describe("establecimiento detalle card PR10.4b.3", () => {
  it("muestra datos esenciales de la ficha", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).toContain("{tituloPrincipal}");
    expect(src).toContain("DNI/CUIT:");
    expect(src).toContain("RUBRO:");
    expect(src).toContain("DOMICILIO");
    expect(src).toContain("{domicilioLinea}");
    expect(src).toContain("Distrito:");
  });

  it("no muestra metadatos administrativos removidos", () => {
    const src = readFileSync(detallePagePath, "utf8");
    expect(src).not.toContain("ref. domicilio");
    expect(src).not.toContain("Calle normalizada");
    expect(src).not.toContain("Actuaciones registradas");
    expect(src).not.toContain("Última actuación");
    expect(src).not.toContain("actuaciones_count");
    expect(src).not.toContain("ultima_actuacion_fecha");
  });
});
