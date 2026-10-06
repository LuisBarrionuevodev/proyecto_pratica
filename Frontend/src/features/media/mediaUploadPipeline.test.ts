import { describe, expect, it, vi } from "vitest";
import { MOBILE_UPLOAD_CONCURRENCY } from "./mediaUploadPipeline";

describe("mediaUploadPipeline", () => {
  it("usa concurrencia 1 para móvil por defecto", () => {
    expect(MOBILE_UPLOAD_CONCURRENCY).toBe(1);
  });
});
