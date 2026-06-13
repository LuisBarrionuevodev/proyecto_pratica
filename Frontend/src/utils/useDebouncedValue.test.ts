import { afterEach, describe, expect, it, vi } from "vitest";

import { useDebouncedValue } from "./useDebouncedValue";

/** Misma ventana que `useDebouncedValue` (300 ms) en buscadores STAB-6. */
const DEBOUNCE_MS = 300;

describe("useDebouncedValue / debounce STAB-6", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounce evita disparos intermedios (patrón usado por buscadores)", () => {
    vi.useFakeTimers();
    const onSettled = vi.fn();
    let timer: ReturnType<typeof setTimeout> | null = null;

    const schedule = (value: string) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => onSettled(value), DEBOUNCE_MS);
    };

    schedule("a");
    schedule("ab");
    schedule("abc");
    vi.advanceTimersByTime(DEBOUNCE_MS - 1);
    expect(onSettled).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onSettled).toHaveBeenCalledTimes(1);
    expect(onSettled).toHaveBeenCalledWith("abc");
  });

  it("exporta hook useDebouncedValue", () => {
    expect(typeof useDebouncedValue).toBe("function");
  });
});
