import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const dialogPath = resolve(fileURLToPath(new URL(".", import.meta.url)), "CorreccionEstablecimientoDialog.tsx");
const detallePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../EstablecimientoDetallePage.tsx"
);
const fichaHeaderPath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "EstablecimientoFichaHeader.tsx"
);

describe("CorreccionEstablecimientoDialog 1B", () => {
  it("domicilio usa selector Número / Esquina y no borra al cambiar de modo", () => {
    const src = readFileSync(dialogPath, "utf8");
    expect(src).toContain('value="NUMERO">Número');
    expect(src).toContain('value="ESQUINA">Esquina');
    expect(src).toContain("setNumeroTipo(next)");
    expect(src).not.toContain("setNumero(\"\")");
    expect(src).not.toContain("setEsquina(\"\")");
  });

  it("contribuyente usa selector visual y conserva ambos si el histórico es mixto", () => {
    const src = readFileSync(dialogPath, "utf8");
    expect(src).toContain('value="persona">Contribuyente');
    expect(src).toContain('value="razon_social">Razón social');
    expect(src).toContain("Ambos (datos actuales)");
    expect(src).toContain("inferTitularCorreccionModo");
    expect(src).toContain("CUIT / DNI");
  });

  it("ficha muestra acciones discretas y corrección de local", () => {
    const pageSrc = readFileSync(detallePath, "utf8");
    const headerSrc = readFileSync(fichaHeaderPath, "utf8");
    expect(pageSrc).toContain('role === "admin" || role === "usuario"');
    expect(headerSrc).toContain("Corregir datos del local");
    expect(headerSrc).toContain('dsVariant="ghost"');
    expect(headerSrc).toContain('onCorregir("local")');
  });

  it("modales conservan Ver alcance y confirmación primary", () => {
    const src = readFileSync(dialogPath, "utf8");
    expect(src).toContain("Ver alcance");
    expect(src).toContain("Confirmar corrección");
    expect(src).toContain('dsVariant="primary"');
  });

  it("DOCUMENTO_AJENO ofrece vincular sin autoaplicar", () => {
    const src = readFileSync(dialogPath, "utf8");
    expect(src).toContain('codigo === "DOCUMENTO_AJENO"');
    expect(src).toContain("VINCULACION_ACCION");
    expect(src).toContain("onVincularDocumento");
    expect(src).not.toContain("aplicarVinculacionEstablecimiento");
  });
});
