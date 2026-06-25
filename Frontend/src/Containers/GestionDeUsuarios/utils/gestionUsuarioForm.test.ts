import { describe, expect, it } from "vitest";

import {
  buildCreateUsuarioPayload,
  buildUpdateUsuarioPayload,
  gestionUsuarioFormFromUser,
  normalizeUsuarioRoleForApi,
  usuarioRoleLabel,
  validateGestionUsuarioForm,
} from "./gestionUsuarioForm";
import { mapGestionUsuarioApiErrors } from "./gestionUsuarioFormErrors";

describe("gestionUsuarioForm", () => {
  it("usuarioRoleLabel muestra etiquetas humanas sin cambiar valores API", () => {
    expect(usuarioRoleLabel("admin")).toBe("Administrador");
    expect(usuarioRoleLabel("relevador")).toBe("Relevador");
    expect(normalizeUsuarioRoleForApi("relevador")).toBe("relevador");
  });

  it("precarga formulario de edición sin password", () => {
    const form = gestionUsuarioFormFromUser({
      username: "jperez",
      email: "a@b.com",
      role: "relevador",
    });
    expect(form.username).toBe("jperez");
    expect(form.password).toBe("");
    expect(form.role).toBe("relevador");
  });

  it("password obligatorio solo en alta", () => {
    const createErrors = validateGestionUsuarioForm(
      { username: "abc", email: "x@y.com", password: "", role: "usuario" },
      true
    );
    expect(createErrors.password).toBeTruthy();

    const editErrors = validateGestionUsuarioForm(
      { username: "abc", email: "x@y.com", password: "", role: "usuario" },
      false
    );
    expect(editErrors.password).toBeUndefined();
  });

  it("buildCreateUsuarioPayload conserva contrato POST", () => {
    expect(
      buildCreateUsuarioPayload({
        username: " u ",
        email: " e@x.com ",
        password: "secret",
        role: "relevador",
      })
    ).toEqual({
      username: "u",
      email: "e@x.com",
      password: "secret",
      role: "relevador",
    });
  });

  it("buildUpdateUsuarioPayload omite password vacío", () => {
    expect(
      buildUpdateUsuarioPayload({
        username: "u",
        email: "e@x.com",
        password: "   ",
        role: "admin",
      })
    ).toEqual({
      username: "u",
      email: "e@x.com",
      password: undefined,
      role: "admin",
    });
  });
});

describe("mapGestionUsuarioApiErrors", () => {
  it("mapea errors.email del backend al campo email", () => {
    const err = {
      response: {
        data: {
          errors: { email: "Email ya registrado" },
        },
      },
    };
    const { fieldErrors, globalMessage } = mapGestionUsuarioApiErrors(err, "fallback");
    expect(fieldErrors.email).toBe("Email ya registrado");
    expect(globalMessage).toBeNull();
  });

  it("usa detail heurístico para email duplicado", () => {
    const err = {
      response: {
        data: {
          detail: "El email ya está en uso",
        },
      },
    };
    const { fieldErrors } = mapGestionUsuarioApiErrors(err, "fallback");
    expect(fieldErrors.email).toContain("email");
  });

  it("devuelve globalMessage cuando no hay campo", () => {
    const err = {
      response: {
        data: {
          detail: "Error interno",
        },
      },
    };
    const { fieldErrors, globalMessage } = mapGestionUsuarioApiErrors(err, "No se pudo guardar");
    expect(Object.keys(fieldErrors)).toHaveLength(0);
    expect(globalMessage).toBeTruthy();
  });
});
