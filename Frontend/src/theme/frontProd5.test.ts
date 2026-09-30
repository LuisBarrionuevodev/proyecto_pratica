import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { darkColors, lightColors } from "./colors";
import { resolveGlideCellTheme } from "../Containers/CargarActuaciones/config/glideGridSemantics";
import { createGridTheme } from "../Containers/CargarActuaciones/config/gridTheme";
import { completarPendingFooterSx } from "../Containers/CompletarTrabajos/utils/completarTrabajoCalendarDisplay";
import { CRUD_DIALOG_TEXT, crudDialogPaperSx } from "../styles/crudDialogTokens";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

describe("FRONT-PROD.5 — modales light, calendario, Glide, submit", () => {
  it("CRUD dialog tokens usan superficies semánticas, no paper oscuro fijo", () => {
    expect(CRUD_DIALOG_TEXT.primary).toContain("--d-text-primary");
    expect(String(crudDialogPaperSx.backgroundColor)).toContain("--d-surface-panel-elevated");
    const tokensSrc = readSrc("styles/crudDialogTokens.ts");
    expect(tokensSrc).not.toContain("rgba(12, 18, 32, 0.88)");
    expect(tokensSrc).not.toMatch(/CRUD_DIALOG_TEXT[\s\S]*#ffffff/i);
  });

  it("Mandar todo commitea la grilla Glide antes del batch", () => {
    const relev = readSrc("Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx");
    const actu = readSrc("Containers/CargarActuaciones/Components/TablaCargarActuacionesGlideStyled.tsx");
    expect(relev).toContain("commitGlideGridBeforeSubmit");
    expect(actu).toContain("commitGlideGridBeforeSubmit");
    expect(relev).toContain("dataRef.current = newData");
    expect(actu).toContain("dataRef.current = newData");
  });

  it("calendario Completar: footer pendientes más legible", () => {
    expect(lightColors.calendar.completarFooterText).toBe(lightColors.text.primary);
    expect(completarPendingFooterSx.fontSize).toBe("0.76rem");
    expect(completarPendingFooterSx.fontWeight).toBe(600);
  });

  it("Glide: fuente base mayor y celdas pintadas con contraste por tema", () => {
    expect(createGridTheme(lightColors).baseFontStyle).toBe("13px");
    const lightErr = resolveGlideCellTheme(lightColors, "error");
    const darkErr = resolveGlideCellTheme(darkColors, "error");
    expect(lightErr.textDark).toBe(lightColors.text.primary);
    expect(darkErr.textDark).toBe(darkColors.text.primary);
    expect(lightErr.baseFontStyle).toBe("700 13px");
  });

  it("formulario denuncia hace flush del foco antes de guardar", () => {
    const form = readSrc("Containers/CargarRelevamientos/Components/DenunciaForm.tsx");
    expect(form).toContain("flushActiveElementBeforeAction");
    const crudFields = readSrc("styles/crudDialogTokens.ts");
    expect(crudFields).toContain("MuiInputBase-multiline");
  });

  it("denuncia CRUD: label en slot, sin label duplicado en controles", () => {
    const slot = readSrc("components/crudDialog/CrudFormSlot.tsx");
    expect(slot).toContain("slotLabelInEdit");
    const dialog = readSrc("Containers/Relevamientos/Components/DenunciaCrudDialog.tsx");
    expect(dialog).toContain("slotLabelInEdit");
    const dialogTextFields = dialog.match(/<AppTextField[\s\S]*?\/>/g) ?? [];
    expect(dialogTextFields.length).toBeGreaterThan(0);
    for (const block of dialogTextFields) {
      expect(block).not.toMatch(/\blabel="/);
    }
    const dialogSelects = dialog.match(/<AppSelect[\s\S]*?\/>/g) ?? [];
    for (const block of dialogSelects) {
      expect(block).not.toMatch(/\n\s+label="/);
    }
    const alta = readSrc("Containers/CargarRelevamientos/Components/DenunciaForm.tsx");
    expect(alta).toContain("slotLabelInEdit");
    const altaTextFields = alta.match(/<AppTextField[\s\S]*?\/>/g) ?? [];
    for (const block of altaTextFields) {
      expect(block).not.toMatch(/\blabel="/);
    }
  });
});
