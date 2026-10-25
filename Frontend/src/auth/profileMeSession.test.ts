import { afterEach, describe, expect, it, vi } from "vitest";

const getMock = vi.fn();

vi.mock("../api/apiClient", () => ({
  apiClient: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

import { clearProfileMeSessionCache, fetchProfileMe } from "./profileMeSession";

describe("profileMeSession PERF.3", () => {
  afterEach(() => {
    clearProfileMeSessionCache();
    getMock.mockReset();
  });

  it("dos consumidores simultáneos comparten una sola request", async () => {
    getMock.mockReturnValue(
      Promise.resolve({
        data: {
          user: { username: "a", role: "admin" },
          profile: { nickname: null, avatar_key: "avatar1" },
        },
      })
    );

    const [a, b] = await Promise.all([fetchProfileMe(), fetchProfileMe()]);
    expect(a.user.username).toBe("a");
    expect(b.user.username).toBe("a");
    expect(getMock).toHaveBeenCalledTimes(1);
  });

  it("logout/login: clear y force vuelven a consultar", async () => {
    getMock.mockResolvedValue({
      data: {
        user: { username: "u1", role: "relevador" },
        profile: { nickname: null, avatar_key: "avatar1" },
      },
    });
    await fetchProfileMe();
    expect(getMock).toHaveBeenCalledTimes(1);

    clearProfileMeSessionCache();
    getMock.mockResolvedValue({
      data: {
        user: { username: "u2", role: "admin" },
        profile: { nickname: "n", avatar_key: "avatar2" },
      },
    });
    const me = await fetchProfileMe({ force: true });
    expect(me.user.username).toBe("u2");
    expect(getMock).toHaveBeenCalledTimes(2);
  });
});
