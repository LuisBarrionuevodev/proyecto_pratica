import { describe, expect, it, vi } from "vitest";
import {
  notifyCompletarTrabajoPendientesRefresh,
  subscribeCompletarTrabajoPendientesRefresh,
} from "./completarTrabajoPendientesRefresh";

describe("completarTrabajoPendientesRefresh", () => {
  it("notifica a los suscriptores", () => {
    const listener = vi.fn();
    const unsub = subscribeCompletarTrabajoPendientesRefresh(listener);
    notifyCompletarTrabajoPendientesRefresh();
    expect(listener).toHaveBeenCalledTimes(1);
    unsub();
    notifyCompletarTrabajoPendientesRefresh();
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
