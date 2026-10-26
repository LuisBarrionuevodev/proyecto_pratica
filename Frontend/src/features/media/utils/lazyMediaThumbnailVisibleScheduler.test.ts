import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  flushLazyThumbnailVisibleQueueForTests,
  resetLazyThumbnailVisibleSchedulerForTests,
  scheduleLazyThumbnailVisible,
} from "./lazyMediaThumbnailVisibleScheduler";

describe("lazyMediaThumbnailVisibleScheduler PERF.6", () => {
  let rafSpy: ReturnType<typeof vi.fn>;
  let rafId: number;

  beforeEach(() => {
    rafId = 0;
    rafSpy = vi.fn((cb: FrameRequestCallback) => {
      rafId += 1;
      return rafId;
    });
    vi.stubGlobal("requestAnimationFrame", rafSpy);
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
    resetLazyThumbnailVisibleSchedulerForTests();
  });

  afterEach(() => {
    resetLazyThumbnailVisibleSchedulerForTests();
    vi.unstubAllGlobals();
  });

  it("agrupa múltiples miniaturas visibles en un solo requestAnimationFrame", () => {
    const runs: number[] = [];
    scheduleLazyThumbnailVisible(1, () => runs.push(1));
    scheduleLazyThumbnailVisible(2, () => runs.push(2));
    scheduleLazyThumbnailVisible(3, () => runs.push(3));

    expect(rafSpy).toHaveBeenCalledTimes(1);
    expect(runs).toHaveLength(0);

    const cb = rafSpy.mock.calls[0]?.[0] as FrameRequestCallback;
    cb(0);
    expect(runs).toEqual([1, 2, 3]);
  });

  it("no encola dos veces el mismo archivo en el mismo frame", () => {
    const run = vi.fn();
    scheduleLazyThumbnailVisible(9, run);
    scheduleLazyThumbnailVisible(9, run);

    const cb = rafSpy.mock.calls[0]?.[0] as FrameRequestCallback;
    cb(0);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("flush de tests ejecuta la cola pendiente", () => {
    const run = vi.fn();
    scheduleLazyThumbnailVisible(4, run);
    flushLazyThumbnailVisibleQueueForTests();
    expect(run).toHaveBeenCalledTimes(1);
  });
});
