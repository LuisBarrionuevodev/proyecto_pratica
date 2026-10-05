import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PublicAuthScreenLayout", () => {
  it("usa TextDigitaliza.svg (desktop izq / mobile centrado)", () => {
    const layout = read("src/components/auth/PublicAuthScreenLayout.tsx");
    expect(layout).toContain("TextDigitaliza.svg");
    expect(layout).toContain("public-auth-brand-logo-mobile");
    expect(layout).toContain("public-auth-brand-logo-desktop");
    expect(layout).not.toContain("logo-smt.png");
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

describe("Recuperar contraseña responsive", () => {
  it("tres etapas comparten shell y estilos fluidos", () => {
    const email = read("src/Containers/RecuperarCuenta/Components/EmailBox.tsx");
    const codigo = read("src/Containers/RecuperarCuenta/Components/CodigoBox.tsx");
    const nueva = read("src/Containers/RecuperarCuenta/Components/NuevaContraseña.tsx");
    const styles = read("src/styles/RecuperarCuentaStyles.ts");
    expect(email).toContain("RecuperarCuentaStepShell");
    expect(codigo).toContain("RecuperarCuentaStepShell");
    expect(nueva).toContain("RecuperarCuentaStepShell");
    expect(styles).toContain('xs: "16px"');
    expect(styles).toContain('width: "100%"');
  });

  it("mantiene ruta pública con BackgroundInicio2", () => {
    const recuperar = read("src/Containers/RecuperarCuenta/index.tsx");
    expect(recuperar).toContain("setBodyPublicRoute(true)");
  });
});
