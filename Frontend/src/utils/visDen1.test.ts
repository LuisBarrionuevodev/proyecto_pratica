import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { DENUNCIA_MODAL_LABELS } from "../Containers/Relevamientos/utils/denunciaModalLabels";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("VIS-DEN.1 — modales Denuncias alineados CRUD glass", () => {
  const agregar = read("src/Containers/CargarRelevamientos/Components/DenunciaForm.tsx");
  const gestionar = read("src/Containers/Relevamientos/Components/DenunciaCrudDialog.tsx");

  it("exporta labels de modales", () => {
    expect(DENUNCIA_MODAL_LABELS.AGREGAR_DENUNCIA).toBe("Agregar denuncia");
    expect(DENUNCIA_MODAL_LABELS.GESTIONAR_DENUNCIA).toBe("Gestionar denuncia");
  });

  it("Agregar denuncia usa CrudGlassDialog y patrón operativo", () => {
    expect(agregar).toContain("CrudGlassDialog");
    expect(agregar).toContain("CrudDialogHeader");
    expect(agregar).toContain("CrudDialogSection");
    expect(agregar).toContain("CrudFormSlot");
    expect(agregar).toContain("CrudDialogActions");
    expect(agregar).toContain("appearance=\"glass\"");
    expect(agregar).toContain("DENUNCIA_MODAL_LABELS.AGREGAR_DENUNCIA");
    expect(agregar).not.toContain("AppDialog");
    expect(agregar).not.toContain("Registrar denuncia");
    expect(agregar).toContain("createDenuncia");
  });

  it("Gestionar denuncia usa CrudGlassDialog con título unificado", () => {
    expect(gestionar).toContain("CrudGlassDialog");
    expect(gestionar).toContain("DENUNCIA_MODAL_LABELS.GESTIONAR_DENUNCIA");
    expect(gestionar).not.toContain("Editar denuncia");
    expect(gestionar).toContain("NumeroEsquinaEditor");
    expect(gestionar).toContain("CrudFormSlot");
  });
});
