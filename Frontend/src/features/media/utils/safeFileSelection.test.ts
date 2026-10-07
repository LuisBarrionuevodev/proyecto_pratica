import { describe, expect, it } from "vitest";
import { safeFilesFromFileList } from "./safeFileSelection";

describe("safeFilesFromFileList", () => {
  it("convierte FileList a array una sola vez", () => {
    const file = new File(["x"], "a.jpg", { type: "" });
    const list = {
      0: file,
      length: 1,
      item: (i: number) => (i === 0 ? file : null),
    } as unknown as FileList;
    const out = safeFilesFromFileList(list);
    expect(out).toHaveLength(1);
    expect(out[0]?.type).toBe("");
  });
});
