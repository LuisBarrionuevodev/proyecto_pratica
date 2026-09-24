import { describe, expect, it, vi } from "vitest";

import {
  clearPersistKeyIfMatch,
  GESTION_PERSIST_OPS,
  GESTION_RECONCILE_REFRESH_MSG,
  invalidatePendingMutationCallbacks,
  isMutationSeqCurrent,
  isPersistingForRow,
  nextMutationSeq,
  runGestionReconcile,
} from "./gestionMutationLifecycle";

describe("gestionMutationLifecycle", () => {
  it("isPersistingForRow solo coincide actuacionId + op", () => {
    const key = { actuacionId: 10, op: GESTION_PERSIST_OPS.notifAltaExpediente };
    expect(isPersistingForRow(key, 10, GESTION_PERSIST_OPS.notifAltaExpediente)).toBe(true);
    expect(isPersistingForRow(key, 11, GESTION_PERSIST_OPS.notifAltaExpediente)).toBe(false);
    expect(isPersistingForRow(key, 10, GESTION_PERSIST_OPS.compOficioAlta)).toBe(false);
    expect(isPersistingForRow(null, 10, GESTION_PERSIST_OPS.notifAltaExpediente)).toBe(false);
  });

  it("mutation seq invalida tokens anteriores", () => {
    const ref = { current: 0 };
    const t1 = nextMutationSeq(ref);
    expect(isMutationSeqCurrent(ref, t1)).toBe(true);
    invalidatePendingMutationCallbacks(ref);
    expect(isMutationSeqCurrent(ref, t1)).toBe(false);
    const t2 = nextMutationSeq(ref);
    expect(isMutationSeqCurrent(ref, t2)).toBe(true);
  });

  it("clearPersistKeyIfMatch solo limpia la operación esperada", () => {
    const key = { actuacionId: 5, op: GESTION_PERSIST_OPS.compExpedienteSalida };
    expect(clearPersistKeyIfMatch(key, 5, GESTION_PERSIST_OPS.compExpedienteSalida)).toBeNull();
    expect(clearPersistKeyIfMatch(key, 6, GESTION_PERSIST_OPS.compExpedienteSalida)).toBe(key);
    expect(clearPersistKeyIfMatch(key, 5, GESTION_PERSIST_OPS.compOficioAlta)).toBe(key);
  });

  it("runGestionReconcile no propaga rechazo y llama onError", async () => {
    const onError = vi.fn();
    const err = new Error("network");
    runGestionReconcile(async () => {
      throw err;
    }, onError);
    await new Promise((r) => setTimeout(r, 0));
    expect(onError).toHaveBeenCalledWith(err);
  });

  it("runGestionReconcile ejecuta task async", async () => {
    const spy = vi.fn().mockResolvedValue(undefined);
    runGestionReconcile(spy);
    await new Promise((r) => setTimeout(r, 0));
    expect(spy).toHaveBeenCalledOnce();
  });

  it("mensaje de reconcile definido", () => {
    expect(GESTION_RECONCILE_REFRESH_MSG).toMatch(/guardaron correctamente/i);
  });
});
