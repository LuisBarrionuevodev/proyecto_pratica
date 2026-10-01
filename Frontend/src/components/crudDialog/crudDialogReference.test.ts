import { describe, expect, it } from "vitest";

import {
  formatCrudDialogActuacionReference,
  formatCrudDialogOtReference,
  resolveCrudDialogHeaderReference,
} from "./crudDialogReference";

describe("crudDialogReference", () => {
  it("formatea OT sin duplicar prefijo", () => {
    expect(formatCrudDialogOtReference("123456")).toBe("OT 123456");
    expect(formatCrudDialogOtReference("OT 99")).toBe("OT 99");
    expect(formatCrudDialogOtReference("—")).toBeNull();
  });

  it("prioriza OT sobre actuación en header", () => {
    expect(resolveCrudDialogHeaderReference("123", 42)).toBe("OT 123");
    expect(resolveCrudDialogHeaderReference("", 42)).toBe("Actuación #42");
    expect(formatCrudDialogActuacionReference(0)).toBeNull();
  });
});
