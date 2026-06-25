import { describe, expect, it, vi } from "vitest";

import { scrollActuacionFormToFirstFieldError } from "./actuacionFormScroll";

describe("scrollActuacionFormToFirstFieldError", () => {
  it("hace scroll al primer input con clase Mui-error", () => {
    const badInput = {
      scrollIntoView: vi.fn(),
      focus: vi.fn(),
    };
    const container = {
      querySelector: vi.fn(() => badInput),
      scrollTo: vi.fn(),
    } as unknown as HTMLElement;

    scrollActuacionFormToFirstFieldError(container, { calle: "Calle requerida" });
    expect(container.querySelector).toHaveBeenCalled();
    expect(badInput.scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "center" });
    expect(badInput.focus).toHaveBeenCalledWith({ preventScroll: true });
  });

  it("no hace nada sin errores", () => {
    const container = {
      querySelector: vi.fn(),
      scrollTo: vi.fn(),
    } as unknown as HTMLElement;
    scrollActuacionFormToFirstFieldError(container, {});
    expect(container.querySelector).not.toHaveBeenCalled();
    expect(container.scrollTo).not.toHaveBeenCalled();
  });
});
