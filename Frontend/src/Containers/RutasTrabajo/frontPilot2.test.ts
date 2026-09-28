import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("FRONT-PILOT.2 — placeholders login / recuperar", () => {
  it("InputStyles define color y placeholder oscuros", () => {
    const login = read("src/styles/LoginStyles.ts");
    expect(login).toContain('color: "#111111"');
    expect(login).toContain("MuiInputBase-input::placeholder");
    expect(login).toContain("opacity: 1");
  });

  it("InputRecuperarStyles define color y placeholder oscuros", () => {
    const rec = read("src/styles/RecuperarCuentaStyles.ts");
    expect(rec).toContain('color: "#111111"');
    expect(rec).toContain("MuiInputBase-input::placeholder");
    expect(rec).toContain("opacity: 1");
  });
});

describe("FRONT-PILOT.2 — MapaOtSecuenciaPreview", () => {
  it("prioriza rango OT estimado sin Próxima OT", () => {
    const src = read("src/Containers/RutasTrabajo/Components/MapaOtSecuenciaPreview.tsx");
    expect(src).not.toContain("Próxima OT (estimado)");
    expect(src).toContain("Rango OT estimado");
    expect(src).toContain("first_display");
    expect(src).toContain("last_display");
    expect(src).toContain("GLASS_COLORS.textPrimary");
    expect(src).toContain('dsVariant="primary"');
    expect(src).toContain('role === "admin"');
  });
});

describe("FRONT-PILOT.2 — RutasMapaOperativoView cabecera", () => {
  it("sin título Indicadores; contexto y métricas territoriales", () => {
    const mapa = read("src/Containers/RutasTrabajo/views/RutasMapaOperativoView.tsx");
    expect(mapa).not.toContain("Indicadores (snapshot)");
    expect(mapa).not.toContain('"Indicadores"');
    expect(mapa).toContain("RutaContextoLine");
    expect(mapa).toContain("mapa-final-metricas-territoriales");
    expect(mapa).toContain("Direcciones");
    expect(mapa).toContain("En mapa");
    expect(mapa).toContain("Distritos");
    expect(mapa).toContain("Ámbito");
    expect(mapa).toContain('gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) auto" }');
  });
});

describe("FRONT-PILOT.2 — ModalAsignarInspectoresGrupo", () => {
  it("Listo en footer actions junto a Cancelar", () => {
    const modal = read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx");
    const actionsBlock = modal.slice(modal.indexOf("actions={"), modal.indexOf(">", modal.indexOf("actions={")) + 800);
    expect(actionsBlock).toContain("Cancelar");
    expect(actionsBlock).toContain("Listo");
    expect(actionsBlock).toContain('data-testid="modal-inspectores-listo"');
    expect(actionsBlock).toContain('dsVariant="primary"');
    const listIdx = modal.indexOf("ref={listParentRef}");
    const listoInContent = modal.slice(listIdx).includes(">Listo</AppButton>");
    expect(listoInContent).toBe(false);
  });

  it("lista con altura responsive y scroll interno único", () => {
    const modal = read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx");
    expect(modal).toContain("clamp(180px, 32vh, 320px)");
    expect(modal).toContain("maxHeight: 320");
    const autoCount = (modal.match(/overflow:\s*"auto"/g) ?? []).length;
    expect(autoCount).toBe(1);
  });
});
