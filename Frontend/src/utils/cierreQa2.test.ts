import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { canAccessModule, getVisibleHomeCards, getVisibleMenuSections } from "../auth/accessConfig";
import { formatToolbarUserDisplay, resolveRealDisplayName } from "../auth/userDisplay";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("CIERRE-QA-2 A — Pool no achica Urgentes", () => {
  it("columna derecha usa flex slots independientes", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    expect(styles).toContain("planificacionUrgentesSlotSx");
    expect(styles).toContain("planificacionPoolSlotSx");
    expect(view).toContain("planificacionUrgentesSlotSx");
    expect(view).toContain("planificacionPoolSlotSx");
  });

  it("Urgentes y Pool usan list viewport con scroll propio", () => {
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(urgentes).toContain("planificacionListViewportSx");
    expect(pool).toContain("planificacionListViewportSx");
    expect(pool).toContain("planificacionFixedSectionSx");
  });
});

describe("CIERRE-QA-2 B — Toolbar usuario/perfil", () => {
  it("Relevador sin nombre muestra solo Relevador", () => {
    const d = formatToolbarUserDisplay(null, "usuario", "relevador");
    expect(d.primary).toBe("Relevador");
    expect(d.showRoleBadge).toBe(false);
  });

  it("Relevador con nombre muestra nombre y badge", () => {
    const d = formatToolbarUserDisplay("Pablo García", "usuario", "relevador");
    expect(d.primary).toBe("Pablo García");
    expect(d.roleLabel).toBe("Relevador");
    expect(d.showRoleBadge).toBe(true);
  });

  it("no usa placeholder usuario como nombre real", () => {
    expect(resolveRealDisplayName(null, "usuario")).toBeNull();
    expect(resolveRealDisplayName("usuario", "usuario")).toBeNull();
  });

  it("TopBar usa AppSessionProvider", () => {
    const src = read("src/Componets/TopBar.tsx");
    expect(src).toContain("useAppSession");
    expect(src).not.toContain('setUserName("Usuario")');
    expect(src).not.toContain("apiClient.get");
  });
});

describe("CIERRE-QA-2 C/D — Permisos unificados sin flicker", () => {
  it("canAccessModule alinea nav e inicio", () => {
    expect(canAccessModule("admin", "/gestionDeUsuarios")).toBe(true);
    expect(canAccessModule("usuario", "/gestionDeUsuarios")).toBe(false);
    expect(canAccessModule("relevador", "/cargarActuacion")).toBe(true);
    expect(canAccessModule("relevador", "/rutasTrabajo")).toBe(false);
  });

  it("admin ve Gestión Usuarios en nav e inicio juntos", () => {
    const home = getVisibleHomeCards("admin").map((c) => c.to);
    const nav = getVisibleMenuSections("admin").flatMap((s) => s.items.map((i) => i.path));
    expect(home).toContain("/gestionDeUsuarios");
    expect(nav).toContain("/gestionDeUsuarios");
  });

  it("relevador nunca ve gestión usuarios ni rutas", () => {
    const home = getVisibleHomeCards("relevador").map((c) => c.to);
    const nav = getVisibleMenuSections("relevador").flatMap((s) => s.items.map((i) => i.path));
    expect(home).not.toContain("/gestionDeUsuarios");
    expect(home).not.toContain("/rutasTrabajo");
    expect(nav).not.toContain("/gestionDeUsuarios");
    expect(home).toHaveLength(3);
  });

  it("Inicio default deny: skeleton mientras carga", () => {
    const src = read("src/Containers/Inicio/Components/InicioOperacionesGrid.tsx");
    expect(src).toContain('status === "loading"');
    expect(src).toContain("Skeleton");
    expect(src).toContain("getVisibleHomeCards");
    expect(src).not.toContain('useState<AppRole>("usuario")');
  });

  it("Nav e Inicio usan accessConfig", () => {
    expect(read("src/Componets/NavLeft.tsx")).toContain("getVisibleMenuSections");
    expect(read("src/Containers/Inicio/Components/InicioOperacionesGrid.tsx")).toContain("getVisibleHomeCards");
    expect(read("src/App.tsx")).toContain("AppSessionProvider");
  });

  it("Nav no renderiza secciones mientras loading", () => {
    const src = read("src/Componets/NavLeft.tsx");
    expect(src).toContain('status === "loading"');
    expect(src).not.toContain('useState<AppRole>("usuario")');
  });
});
