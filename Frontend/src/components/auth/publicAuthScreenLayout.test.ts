import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PublicAuthScreenLayout", () => {
  it("usa PNG institucional una sola vez", () => {
    const layout = read("src/components/auth/PublicAuthScreenLayout.tsx");
    expect(layout).toContain("logo-smt.png");
    expect(layout).toContain("public-auth-brand-logo");
  });

  it("Login y Recuperar usan layout sin logo duplicado en caja", () => {
    const login = read("src/Containers/Login/index.tsx");
    const box = read("src/Containers/Login/Components/LoginBox.tsx");
    const recuperar = read("src/Containers/RecuperarCuenta/index.tsx");
    expect(login).toContain("PublicAuthScreenLayout");
    expect(box).not.toContain("TextDigitaliza");
    expect(recuperar).toContain("PublicAuthScreenLayout");
  });
});
