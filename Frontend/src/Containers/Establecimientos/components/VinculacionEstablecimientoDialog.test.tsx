import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const dialogPath = resolve(fileURLToPath(new URL(".", import.meta.url)), "VinculacionEstablecimientoDialog.tsx");
const detallePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../EstablecimientoDetallePage.tsx"
);
const fichaHeaderPath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "EstablecimientoFichaHeader.tsx"
);
const apiPath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../../../api/establecimientosOperativosApi.ts"
);

describe("VinculacionEstablecimientoDialog V1.1", () => {
  it("busca por documento, pide confirmación y envía fingerprint", () => {
    const src = readFileSync(dialogPath, "utf8");
    expect(src).toContain("previewVinculacionEstablecimiento");
    expect(src).toContain("aplicarVinculacionEstablecimiento");
    expect(src).toContain("fingerprint: preview.fingerprint");
    expect(src).toContain("VINCULACION_ACCION");
    expect(src).toContain("Confirmar vinculación");
    expect(src).toContain("Cancelar");
    expect(src).toContain("CUIT / DNI correcto");
    expect(src).not.toContain("resolve_contribuyente");
  });

  it("muestra alcance y no promete reescribir PDF ni datos del destino", () => {
    const src = readFileSync(dialogPath, "utf8");
    expect(src).toContain("Otros locales del contribuyente anterior");
    expect(src).toContain("Otros locales del destino");
    expect(src).toContain("no se modifican");
    expect(src).toContain("ficha_logica_destino");
    expect(src).toContain("snapshots_y_pdf");
    expect(src).toContain("datos personales");
  });

  it("ficha muestra la acción aparte y el canal de corrección se mantiene", () => {
    const pageSrc = readFileSync(detallePath, "utf8");
    const headerSrc = readFileSync(fichaHeaderPath, "utf8");
    expect(headerSrc).toContain("VINCULACION_FICHA_ACCION");
    expect(pageSrc).toContain("VinculacionEstablecimientoDialog");
    expect(pageSrc).toContain("CorreccionEstablecimientoDialog");
    expect(pageSrc).toContain("onVincularDocumento");
    expect(pageSrc).toContain('role === "admin" || role === "usuario"');
  });

  it("API usa endpoints de vinculaciones y no envía contribuyente_id", () => {
    const src = readFileSync(apiPath, "utf8");
    expect(src).toContain("/vinculaciones/preview");
    expect(src).toContain("/vinculaciones");
    expect(src).toContain("confirmado: true");
    expect(src).toContain("IVinculacionEstablecimientoPayload");
    expect(src).not.toContain("limpiar_contribuyente");
  });
});
