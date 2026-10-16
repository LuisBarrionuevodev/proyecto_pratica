import { afterEach, describe, expect, it, vi } from "vitest";
import {
  appWebUpdateButtonLabel,
  detectAppWebUpdateMode,
  runAppWebUpdate,
} from "./appWebUpdate";

describe("appWebUpdate", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sin service worker usa recarga dura", async () => {
    vi.stubGlobal("navigator", { serviceWorker: undefined });
    await expect(detectAppWebUpdateMode()).resolves.toBe("hard_reload");
    expect(appWebUpdateButtonLabel("hard_reload")).toBe("Recargar aplicación");
  });

  it("con SW en espera ofrece actualizar aplicación", async () => {
    const waiting = { postMessage: vi.fn() };
    vi.stubGlobal("navigator", {
      serviceWorker: {
        getRegistration: vi.fn().mockResolvedValue({ waiting }),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    });
    await expect(detectAppWebUpdateMode()).resolves.toBe("service_worker_update");
    expect(appWebUpdateButtonLabel("service_worker_update")).toBe("Actualizar aplicación");
  });

  it("runAppWebUpdate recarga la página en modo hard_reload", async () => {
    const reload = vi.fn();
    vi.stubGlobal("window", { location: { reload } });
    await runAppWebUpdate("hard_reload");
    expect(reload).toHaveBeenCalled();
  });
});
