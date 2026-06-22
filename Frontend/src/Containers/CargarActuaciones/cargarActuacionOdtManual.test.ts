import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const modalPath = join(
  dirname(fileURLToPath(import.meta.url)),
  "Components",
  "CargarActuacionNuevaModal.tsx"
);

describe("CargarActuacionNuevaModal ODT manual", () => {
  it("usa AppTextField para Orden de trabajo, no OrdenTrabajoSearchAutocomplete", () => {
    const src = readFileSync(modalPath, "utf8");
    expect(src).toContain('label="Orden de trabajo"');
    expect(src).toContain("AppTextField");
    expect(src).not.toContain("OrdenTrabajoSearchAutocomplete");
  });
});
