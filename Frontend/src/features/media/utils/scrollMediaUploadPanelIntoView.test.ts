import { describe, expect, it, vi } from "vitest";
import { scrollMediaUploadPanelIntoView } from "./scrollMediaUploadPanelIntoView";

describe("scrollMediaUploadPanelIntoView", () => {
  it("desplaza el contenedor scrolleable cuando el panel no está visible", () => {
    const scrollTo = vi.fn();
    const panel = {
      getBoundingClientRect: () => ({ top: 400, bottom: 500, left: 0, right: 0, width: 0, height: 0, x: 0, y: 0, toJSON: () => ({}) }),
      scrollIntoView: vi.fn(),
    } as unknown as HTMLElement;
    const container = {
      scrollHeight: 800,
      clientHeight: 200,
      scrollTop: 0,
      getBoundingClientRect: () => ({ top: 100, bottom: 300, left: 0, right: 0, width: 0, height: 0, x: 0, y: 0, toJSON: () => ({}) }),
      scrollTo,
    } as unknown as HTMLElement;

    scrollMediaUploadPanelIntoView(panel, container);

    expect(scrollTo).toHaveBeenCalled();
    expect(panel.scrollIntoView).not.toHaveBeenCalled();
  });

  it("llama scrollIntoView si no hay contenedor", () => {
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
