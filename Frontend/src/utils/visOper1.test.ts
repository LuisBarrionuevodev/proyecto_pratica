import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { OPER_RUTA_LABELS } from "./operRutaPoolAcciones";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("VIS-OPER.1 labels operativos", () => {
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");
  const dialog = read("src/components/operRuta/AgregarARutaOperDialog.tsx");
  const prorroga = read("src/Containers/GestionNotificacion/components/ReinspeccionOperativaAccionCell.tsx");

  it("exporta labels centralizados", () => {
    expect(OPER_RUTA_LABELS.DAR_PRORROGA).toBe("Dar prórroga");
    expect(OPER_RUTA_LABELS.GESTIONAR_EN_RUTA).toBe("Gestionar en ruta");
    expect(OPER_RUTA_LABELS.SACAR_DE_RUTA).toBe("Sacar de ruta");
    expect(OPER_RUTA_LABELS.MODAL_TITULO).toBe("Gestionar en ruta");
    expect(OPER_RUTA_LABELS.AGREGAR_SOLO_A_LA_RUTA).toBe("Agregar solo a la ruta");
  });

  it("OperRutaPoolAccionesCell usa primary y danger", () => {
    expect(cell).toContain("OPER_RUTA_LABELS.GESTIONAR_EN_RUTA");
    expect(cell).toContain('dsVariant="primary"');
    expect(cell).toContain('dsVariant="danger"');
    expect(cell).toContain("OPER_RUTA_LABELS.SACAR_DE_RUTA");
    expect(cell).not.toContain("Agregar a ruta de trabajo");
    expect(cell).not.toContain("Sacar del pool");
    expect(cell).not.toContain("Sacar de ruta/pool");
  });

  it("ReinspeccionOperativaAccionCell muestra Dar prórroga", () => {
    expect(prorroga).toContain("OPER_RUTA_LABELS.DAR_PRORROGA");
    expect(prorroga).toContain('dsVariant="primary"');
  });

  it("AgregarARutaOperDialog usa CrudGlassDialog y título Gestionar en ruta", () => {
    expect(dialog).toContain("CrudGlassDialog");
    expect(dialog).toContain("CrudDialogHeader");
    expect(dialog).toContain("OPER_RUTA_LABELS.MODAL_TITULO");
    expect(dialog).toContain("appearance=\"glass\"");
    expect(dialog).not.toContain("Agregar a ruta de trabajo");
    expect(dialog).not.toContain("Agregar solo al pool del día");
    expect(dialog).toContain("agregarDesdePoolRuta");
    expect(dialog).toContain("createRutaPoolDia");
  });
});
