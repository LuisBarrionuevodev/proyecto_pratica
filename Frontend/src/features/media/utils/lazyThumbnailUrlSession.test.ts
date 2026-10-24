import { describe, expect, it, vi } from "vitest";
import { LazyThumbnailUrlSession } from "./lazyThumbnailUrlSession";

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("LazyThumbnailUrlSession PERF.2", () => {
  it("galería 10 ítems: solo los visibles solicitan URL", async () => {
    const fetchUrl = vi.fn().mockResolvedValue({ download_url: "https://cdn/x.jpg" });
    const sessions = Array.from({ length: 10 }, (_, i) =>
      new LazyThumbnailUrlSession(i + 1, fetchUrl)
    );

    const visibleCount = 3;
    for (let i = 0; i < visibleCount; i++) {
      await sessions[i].onVisible();
    }

    expect(fetchUrl).toHaveBeenCalledTimes(visibleCount);
    for (let i = 0; i < visibleCount; i++) {
      expect(fetchUrl).toHaveBeenCalledWith(i + 1);
    }
    for (let i = visibleCount; i < 10; i++) {
      expect(sessions[i].getPhase()).toBe("idle");
      expect(sessions[i].shouldFetchOnVisible()).toBe(true);
    }
  });

  it("scroll: cada ítem visible solicita su URL una sola vez", async () => {
    const fetchUrl = vi.fn().mockResolvedValue({ download_url: "https://cdn/y.jpg" });
    const session = new LazyThumbnailUrlSession(7, fetchUrl);

    await session.onVisible();
    await session.onVisible();
    await session.onVisible();

    expect(fetchUrl).toHaveBeenCalledTimes(1);
    expect(session.getPhase()).toBe("ok");
    expect(session.getUrl()).toBe("https://cdn/y.jpg");
  });

  it("imagen cargada conserva preview tras más interacciones", async () => {
    const fetchUrl = vi.fn().mockResolvedValue({ download_url: "https://cdn/keep.jpg" });
    const session = new LazyThumbnailUrlSession(1, fetchUrl);

    await session.onVisible();
    const url = session.getUrl();
    expect(session.getPhase()).toBe("ok");

    await session.onVisible();
    expect(session.getUrl()).toBe(url);
    expect(fetchUrl).toHaveBeenCalledTimes(1);
  });

  it("error de download-url: estado local, reintento no afecta otras sesiones", async () => {
    const fail = new LazyThumbnailUrlSession(
      1,
      vi.fn().mockRejectedValue(new Error("403"))
    );
    const ok = new LazyThumbnailUrlSession(
      2,
      vi.fn().mockResolvedValue({ download_url: "https://cdn/ok.jpg" })
    );

    await fail.onVisible();
    await ok.onVisible();

    expect(fail.getPhase()).toBe("error");
    expect(ok.getPhase()).toBe("ok");

    const retryFetch = vi
      .fn()
      .mockRejectedValueOnce(new Error("403"))
      .mockResolvedValueOnce({ download_url: "https://cdn/fixed.jpg" });
    const failRetry = new LazyThumbnailUrlSession(1, retryFetch);
    await failRetry.onVisible();
    expect(failRetry.getPhase()).toBe("error");
    await failRetry.retry();
    expect(failRetry.getPhase()).toBe("ok");
    expect(retryFetch).toHaveBeenCalledTimes(2);
    expect(ok.getPhase()).toBe("ok");
  });

  it("no inicia fetch duplicado mientras hay request en vuelo", async () => {
    const d = deferred<{ download_url: string }>();
    const fetchUrl = vi.fn(() => d.promise);
    const session = new LazyThumbnailUrlSession(5, fetchUrl);

    const first = session.onVisible();
    const second = session.onVisible();
    expect(fetchUrl).toHaveBeenCalledTimes(1);
    expect(session.getPhase()).toBe("loading");

    d.resolve({ download_url: "https://cdn/async.jpg" });
    await first;
    await second;
    expect(session.getPhase()).toBe("ok");
    expect(fetchUrl).toHaveBeenCalledTimes(1);
  });

  it("nuevo archivo_id (reemplazo tras eliminar) reinicia sesión", async () => {
    const fetchUrl = vi
      .fn()
      .mockResolvedValueOnce({ download_url: "https://cdn/a.jpg" })
      .mockResolvedValueOnce({ download_url: "https://cdn/b.jpg" });

    const first = new LazyThumbnailUrlSession(10, fetchUrl);
    await first.onVisible();
    expect(first.getUrl()).toBe("https://cdn/a.jpg");

    const second = new LazyThumbnailUrlSession(11, fetchUrl);
    expect(second.getPhase()).toBe("idle");
    await second.onVisible();
    expect(second.getUrl()).toBe("https://cdn/b.jpg");
    expect(fetchUrl).toHaveBeenCalledTimes(2);
  });
});
