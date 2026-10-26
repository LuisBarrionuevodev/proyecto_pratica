import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LazyThumbnailUrlSession } from "../utils/lazyThumbnailUrlSession";
import {
  flushLazyThumbnailVisibleQueueForTests,
  resetLazyThumbnailVisibleSchedulerForTests,
  scheduleLazyThumbnailVisible,
} from "../utils/lazyMediaThumbnailVisibleScheduler";

describe("useLazyMediaDownloadUrl batching PERF.6", () => {
  beforeEach(() => {
    let id = 0;
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      id += 1;
      return id;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
    resetLazyThumbnailVisibleSchedulerForTests();
  });

  afterEach(() => {
    resetLazyThumbnailVisibleSchedulerForTests();
    vi.unstubAllGlobals();
  });

  it("simula viewport múltiple: callbacks agrupados y fetch por tile", async () => {
    const fetchUrl = vi.fn().mockResolvedValue({ download_url: "https://cdn/x.jpg" });
    const sessions = [1, 2, 3, 4].map((archivoId) => new LazyThumbnailUrlSession(archivoId, fetchUrl));

    sessions.forEach((session, index) => {
      scheduleLazyThumbnailVisible(index + 1, () => {
        void session.onVisible();
      });
    });

    flushLazyThumbnailVisibleQueueForTests();
    await Promise.resolve();

    expect(fetchUrl).toHaveBeenCalledTimes(4);
    for (const session of sessions) {
      expect(session.getPhase()).toBe("ok");
    }
  });

  it("reintento y eliminación lógica: sesión reemplazada no altera hermanas", async () => {
    const fetchUrl = vi.fn().mockImplementation(async (id: number) => ({
      download_url: `https://cdn/${id}.jpg`,
    }));

    const first = new LazyThumbnailUrlSession(10, fetchUrl);
    const second = new LazyThumbnailUrlSession(11, fetchUrl);
    await first.onVisible();
    await second.onVisible();

    const replacement = new LazyThumbnailUrlSession(12, fetchUrl);
    await replacement.onVisible();

    expect(first.getPhase()).toBe("ok");
    expect(second.getPhase()).toBe("ok");
    expect(replacement.getPhase()).toBe("ok");
    expect(first.getUrl()).toBe("https://cdn/10.jpg");
    expect(replacement.getUrl()).toBe("https://cdn/12.jpg");
  });
});
