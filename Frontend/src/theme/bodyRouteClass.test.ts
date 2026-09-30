import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function createClassList() {
  const set = new Set<string>();
  return {
    add: (...tokens: string[]) => tokens.forEach((t) => set.add(t)),
    remove: (...tokens: string[]) => tokens.forEach((t) => set.delete(t)),
    contains: (token: string) => set.has(token),
    toggle: (token: string, force?: boolean) => {
      const on = force ?? !set.has(token);
      if (on) set.add(token);
      else set.delete(token);
    },
  };
}

describe("bodyRouteClass lifecycle", () => {
  beforeEach(() => {
    const classList = createClassList();
    vi.stubGlobal("document", { body: { classList } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("public-route excluye authenticated-route", async () => {
    const { setBodyPublicRoute } = await import("./bodyRouteClass");
    setBodyPublicRoute(true);
    expect(document.body.classList.contains("public-route")).toBe(true);
    expect(document.body.classList.contains("authenticated-route")).toBe(false);
  });

  it("authenticated-route excluye public-route", async () => {
    const { setBodyAuthenticatedRoute } = await import("./bodyRouteClass");
    setBodyAuthenticatedRoute(true);
    expect(document.body.classList.contains("authenticated-route")).toBe(true);
    expect(document.body.classList.contains("public-route")).toBe(false);
  });

  it("cleanup al desactivar", async () => {
    const { setBodyAuthenticatedRoute, setBodyPublicRoute } = await import("./bodyRouteClass");
    setBodyAuthenticatedRoute(true);
    setBodyAuthenticatedRoute(false);
    expect(document.body.classList.contains("authenticated-route")).toBe(false);
    setBodyPublicRoute(true);
    setBodyPublicRoute(false);
    expect(document.body.classList.contains("public-route")).toBe(false);
  });
});
