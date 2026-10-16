import { describe, expect, it, vi } from "vitest";
import { scrollMediaUploadPanelIntoView } from "./scrollMediaUploadPanelIntoView";

describe("scrollMediaUploadPanelIntoView", () => {
  it("llama scrollIntoView con nearest", () => {
    const scrollIntoView = vi.fn();
    const panel = { scrollIntoView } as unknown as HTMLElement;

    scrollMediaUploadPanelIntoView(panel);

    expect(scrollIntoView).toHaveBeenCalledWith(
      expect.objectContaining({ block: "nearest", inline: "nearest" })
    );
  });

  it("no hace nada sin panel", () => {
    expect(() => scrollMediaUploadPanelIntoView(null)).not.toThrow();
  });
});
