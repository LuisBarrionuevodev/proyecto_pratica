import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { isApiValidationError } from "./parseApiError";
import {
  shouldRefreshDenunciasAfterSaveFailure,
  shouldRefreshRelevamientosAfterSaveFailure,
} from "../Containers/Relevamientos/utils/refreshOnSavePolicy";

describe("isApiValidationError", () => {
  it("detecta 422", () => {
    expect(isApiValidationError({ response: { status: 422, data: { detail: "x" } } })).toBe(true);
  });

  it("detecta 400", () => {
    expect(isApiValidationError({ response: { status: 400, data: { detail: "x" } } })).toBe(true);
  });

  it("no marca 500", () => {
    expect(isApiValidationError({ response: { status: 500, data: { detail: "x" } } })).toBe(false);
  });
});

describe("refreshOnSavePolicy", () => {
  it("relevamiento validation no refresca", () => {
    expect(
      shouldRefreshRelevamientosAfterSaveFailure({
        ok: false,
        kind: "validation",
        fieldErrors: { fecha: "Requerida" },
      })
    ).toBe(false);
  });

  it("relevamiento éxito refresca", () => {
    expect(shouldRefreshRelevamientosAfterSaveFailure({ ok: true })).toBe(true);
  });

  it("denuncia 422 no refresca", () => {
    const err = { response: { status: 422, data: { errors: { motivo: "Requerido" } } } };
    expect(shouldRefreshDenunciasAfterSaveFailure(err, { motivo: "Requerido" })).toBe(false);
  });

  it("denuncia error global no validación no refresca por defecto", () => {
    const err = { response: { status: 500, data: { detail: "Error interno" } } };
    expect(shouldRefreshDenunciasAfterSaveFailure(err, {})).toBe(false);
  });
});

describe("TabNomenclaturaTable STAB-9b", () => {
  it("no usa window.alert", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/GestionarDomicilios/components/TabNomenclaturaTable.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).not.toMatch(/window\.alert/);
    expect(src).not.toMatch(/\balert\s*\(/);
  });
});
