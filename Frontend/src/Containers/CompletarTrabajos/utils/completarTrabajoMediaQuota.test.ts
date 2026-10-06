import { describe, expect, it } from "vitest";
import { sliceFilesToAvailableQuota } from "./completarTrabajoMediaQuota";

describe("sliceFilesToAvailableQuota", () => {
  it("solo agrega archivos hasta el cupo disponible", () => {
    const files = [new File(["a"], "a.jpg"), new File(["b"], "b.jpg"), new File(["c"], "c.jpg")];
    const result = sliceFilesToAvailableQuota(files, "FOTO_ACTA", 9, []);
    expect(result.added).toBe(1);
    expect(result.skipped).toBe(2);
    expect(result.accepted).toHaveLength(1);
  });
});
