import { describe, expect, it, vi } from "vitest";
import { scheduleActuacionListRefreshAfterSave } from "./actuacionEditListRefresh";

describe("scheduleActuacionListRefreshAfterSave", () => {
  it("no refresca si el modal sigue abierto para fotos", () => {
    const trigger = vi.fn();
    const onRefresh = vi.fn();
    scheduleActuacionListRefreshAfterSave(true, trigger, onRefresh);
    expect(trigger).not.toHaveBeenCalled();
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("refresca listado cuando no hay defer de cierre", () => {
    const trigger = vi.fn();
    const onRefresh = vi.fn();
    scheduleActuacionListRefreshAfterSave(false, trigger, onRefresh);
    expect(trigger).toHaveBeenCalledTimes(1);
  });
});
