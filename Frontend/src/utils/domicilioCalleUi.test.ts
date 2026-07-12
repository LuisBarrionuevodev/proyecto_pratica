import { describe, expect, it } from "vitest";

import {
  domicilioCalleCargadaEditable,
  domicilioCalleEsClaveTecnica,
  domicilioCalleParaPayload,
  domicilioCalleValorEdicion,
  domicilioNumeroValorEdicion,
  domicilioEsquinaCargadaEditable,
  domicilioEsquinaEsClaveTecnica,
  domicilioEsquinaParaPayload,
  domicilioNumeroEditable,
  domicilioRowParaEdicionCalle,
} from "./domicilioCalleUi";

const rowMonteagudo = {
  calle: "monteagudo",
  calle_key: "monteagudo",
  calle_raw: "monteagudo barrio sur",
  calle_cargada: "Monteagudo 120",
  calle_normalizada: "Dr Bernardo Monteagudo",
  calle_estado: "OK",
};

const rowEsquina = {
  calle: "monteagudo",
  calle_key: "monteagudo",
  calle_normalizada: "Dr Bernardo Monteagudo",
  calle_estado: "OK",
  numero_tipo: "ESQUINA",
  numero: "santiago del estero",
  esquina_key: "santiago del estero",
  esquina_raw: "santiago del estero",
  esquina_normalizada: "Santiago del Estero",
};

describe("domicilioCalleUi modal calle", () => {
  it("Actuación: hidrata calle_normalizada si existe", () => {
    expect(domicilioCalleCargadaEditable(rowMonteagudo)).toBe("Dr Bernardo Monteagudo");
  });

  it("Actuación: no hidrata calle_key", () => {
    const row = { calle: "monteagudo", calle_key: "monteagudo" };
    expect(domicilioCalleCargadaEditable(row)).toBe("");
    expect(domicilioCalleEsClaveTecnica("monteagudo", row)).toBe(true);
    expect(domicilioRowParaEdicionCalle(row).calle).toBeNull();
  });

  it("Completar Trabajo: hidrata calle humana", () => {
    expect(
      domicilioCalleCargadaEditable({
        calle: "monteagudo",
        calle_key: "monteagudo",
        calle_raw: "Monteagudo 120",
      })
    ).toBe("Monteagudo 120");
  });

  it("guardar sin editar no manda calle_key ni reenvía calle hidratada", () => {
    const hydrated = domicilioCalleCargadaEditable(rowMonteagudo);
    expect(domicilioCalleParaPayload(hydrated, rowMonteagudo)).toBeUndefined();
    expect(domicilioCalleParaPayload("monteagudo", rowMonteagudo)).toBeUndefined();
    expect(domicilioCalleParaPayload("Calle editada", rowMonteagudo)).toBe("Calle editada");
  });

  it("edicion CRUD prioriza calle del draft sobre calle_normalizada", () => {
    const draft = { ...rowMonteagudo, calle: "Catamarca" };
    expect(domicilioCalleValorEdicion(draft)).toBe("Catamarca");
    expect(domicilioCalleCargadaEditable(draft)).toBe("Dr Bernardo Monteagudo");
  });

  it("edicion CRUD permite string vacío temporal en calle sin volver a normalizada", () => {
    const draft = { ...rowMonteagudo, calle: "" };
    expect(domicilioCalleValorEdicion(draft)).toBe("");
  });
});

describe("domicilioCalleUi modal esquina", () => {
  it("Actuación ESQUINA: muestra esquina_normalizada", () => {
    expect(domicilioEsquinaCargadaEditable(rowEsquina)).toBe("Santiago del Estero");
    expect(domicilioNumeroEditable(rowEsquina)).toBe("Santiago del Estero");
  });

  it("sin normalizada usa esquina_raw", () => {
    expect(
      domicilioEsquinaCargadaEditable({
        numero_tipo: "ESQUINA",
        numero: "santiago del estero",
        esquina_key: "santiago del estero",
        esquina_raw: "Santiago del Estero cargada",
      })
    ).toBe("Santiago del Estero cargada");
  });

  it("nunca muestra esquina_key / slug técnico", () => {
    const row = {
      numero_tipo: "ESQUINA",
      numero: "santiago del estero",
      esquina_key: "santiago del estero",
    };
    expect(domicilioEsquinaCargadaEditable(row)).toBe("");
    expect(domicilioEsquinaEsClaveTecnica("santiago del estero", row)).toBe(true);
  });

  it("guardar sin editar no manda esquina técnica", () => {
    const hydrated = domicilioEsquinaCargadaEditable(rowEsquina);
    expect(domicilioEsquinaParaPayload(hydrated, rowEsquina)).toBeUndefined();
    expect(domicilioEsquinaParaPayload("santiago del estero", rowEsquina)).toBeUndefined();
  });

  it("Completar Trabajo: edición manda texto humano", () => {
    expect(domicilioEsquinaParaPayload("Av. Mate de Luna", rowEsquina)).toBe("Av. Mate de Luna");
  });

  it("domicilioRowParaEdicionCalle hidrata calle y esquina", () => {
    const draft = domicilioRowParaEdicionCalle(rowEsquina);
    expect(draft.calle).toBe("Dr Bernardo Monteagudo");
    expect(draft.numero).toBe("Santiago del Estero");
  });
});
