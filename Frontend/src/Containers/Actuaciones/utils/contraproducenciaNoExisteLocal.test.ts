import { describe, expect, it } from "vitest";
import { esFamiliaNoExisteLocalContraproducencia } from "./contraproducenciaNoExisteLocal";

describe("esFamiliaNoExisteLocalContraproducencia", () => {
  it("reconoce NO_EXISTE_LOCAL y alias", () => {
    expect(esFamiliaNoExisteLocalContraproducencia("NO_EXISTE_LOCAL")).toBe(true);
    expect(esFamiliaNoExisteLocalContraproducencia("NO EXISTE LOCAL")).toBe(true);
    expect(esFamiliaNoExisteLocalContraproducencia("LOCAL CERRADO")).toBe(false);
  });
});
