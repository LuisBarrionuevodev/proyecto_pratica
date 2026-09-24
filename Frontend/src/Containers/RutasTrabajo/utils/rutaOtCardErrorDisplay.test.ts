import { describe, expect, it } from "vitest";

import { MENSAJE_OT_CONSUMIDA_CARD } from "./rutaOtAsignacionMessages";
import { otItemCardErrorDisplay } from "./rutaOtCardErrorDisplay";

describe("otItemCardErrorDisplay", () => {
  it("OT consumida muestra error inline y no alert lateral duplicado", () => {
    const r = otItemCardErrorDisplay({
      inlineMessage: MENSAJE_OT_CONSUMIDA_CARD,
      otConsumida: true,
    });
    expect(r.showInlineError).toBe(true);
    expect(r.inlineMessage).toBe(MENSAJE_OT_CONSUMIDA_CARD);
    expect(r.showSideOtConsumidaAlert).toBe(false);
  });

  it("otro error inline tampoco muestra alert lateral OT consumida", () => {
    const r = otItemCardErrorDisplay({
      inlineMessage: "La orden de trabajo ya está asociada a otro item activo",
      otConsumida: false,
    });
    expect(r.showInlineError).toBe(true);
    expect(r.showSideOtConsumidaAlert).toBe(false);
  });

  it("sin mensaje no muestra error inline ni alert", () => {
    const r = otItemCardErrorDisplay({ inlineMessage: "", otConsumida: false });
    expect(r.showInlineError).toBe(false);
    expect(r.showSideOtConsumidaAlert).toBe(false);
  });
});
