import { describe, expect, it } from "vitest";

import {
  DATE_ONLY_RE,
  formatFechaDateOnlyEsAR,
  parseDateOnlyLocal,
} from "./formatFechaDateOnlyEsAR";

describe("DATE_ONLY_RE", () => {
  it("acepta YYYY-MM-DD estricto", () => {
    expect(DATE_ONLY_RE.test("2026-09-03")).toBe(true);
    expect(DATE_ONLY_RE.test("2026-09-03T02:00:00Z")).toBe(false);
  });
});

describe("parseDateOnlyLocal", () => {
  it("D1 — 2026-09-03 conserva día 03", () => {
    const d = parseDateOnlyLocal("2026-09-03");
    expect(d).not.toBeNull();
    expect(d!.getFullYear()).toBe(2026);
    expect(d!.getMonth()).toBe(8);
    expect(d!.getDate()).toBe(3);
  });

  it("D2 — 2026-09-01 conserva día 01 (no 31/08)", () => {
    const d = parseDateOnlyLocal("2026-09-01");
    expect(d).not.toBeNull();
    expect(d!.getDate()).toBe(1);
    expect(d!.getMonth()).toBe(8);
  });

  it("D3 — 2026-01-01 conserva año y día (no 31/12/2025)", () => {
    const d = parseDateOnlyLocal("2026-01-01");
    expect(d).not.toBeNull();
    expect(d!.getFullYear()).toBe(2026);
    expect(d!.getMonth()).toBe(0);
    expect(d!.getDate()).toBe(1);
  });

  it("D4 — 2026-03-31 fin de mes", () => {
    const d = parseDateOnlyLocal("2026-03-31");
    expect(d).not.toBeNull();
    expect(d!.getFullYear()).toBe(2026);
    expect(d!.getMonth()).toBe(2);
    expect(d!.getDate()).toBe(31);
  });
});

describe("formatFechaDateOnlyEsAR", () => {
  it("D1 — formatea 2026-09-03 sin desfase de día", () => {
    const out = formatFechaDateOnlyEsAR("2026-09-03");
    expect(out).not.toMatch(/\b2\b.*sep/i);
    expect(out).toMatch(/3/i);
    expect(out).toMatch(/2026/);
  });

  it("D5 — null, undefined y vacío usan fallback", () => {
    expect(formatFechaDateOnlyEsAR(null)).toBe("—");
    expect(formatFechaDateOnlyEsAR(undefined)).toBe("—");
    expect(formatFechaDateOnlyEsAR("")).toBe("—");
    expect(formatFechaDateOnlyEsAR("   ")).toBe("—");
  });

  it("D6 — timestamp no se interpreta como date-only", () => {
    const ts = "2026-09-03T02:00:00Z";
    expect(formatFechaDateOnlyEsAR(ts)).toBe(ts);
    expect(formatFechaDateOnlyEsAR(ts)).not.toBe(formatFechaDateOnlyEsAR("2026-09-03"));
  });
});
