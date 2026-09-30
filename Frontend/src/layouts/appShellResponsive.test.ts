import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { layoutShell } from "../theme/tokens";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
    return readFileSync(join(root, rel), "utf8");
}

describe("V1.1-RESP.1 — shell responsive mobile-first", () => {
    it("breakpoint desktop centralizado en layoutShell (md / 900px MUI)", () => {
        expect(layoutShell.desktopMinBreakpoint).toBe("md");
        const theme = readSrc("configs/theme.ts");
        expect(theme).toContain("createTheme");
    });

    it("AppLayout usa useMediaQuery con desktopMinBreakpoint y no innerWidth", () => {
        const layout = readSrc("layouts/AppLayout.tsx");
        expect(layout).toContain("useMediaQuery");
        expect(layout).toContain("layoutShell.desktopMinBreakpoint");
        expect(layout).not.toMatch(/window\.innerWidth/);
        expect(layout).toContain("mobileTemporary");
        expect(layout).toContain("showMobileMenuButton");
        expect(layout).toContain("RoleRouteGuard");
    });

    it("desktop: sidebar permanente solo cuando isDesktopShell", () => {
        const layout = readSrc("layouts/AppLayout.tsx");
        expect(layout).toContain("isDesktopShell");
        expect(layout).toContain("onToggle={(open) => setSidebarOpen(open)}");
        expect(layout).toContain("currentSidebarWidth");
    });

    it("mobile: drawer temporal y cierre al cambiar ruta", () => {
        const layout = readSrc("layouts/AppLayout.tsx");
        expect(layout).toContain('setMobileNavOpen(false)');
        expect(layout).toContain("location.pathname");

        const nav = readSrc("Componets/NavLeft.tsx");
        expect(nav).toContain('variant="temporary"');
        expect(nav).toContain("mobileTemporary?.onClose()");
        expect(nav).toContain('aria-label="Cerrar menú de navegación"');
    });

    it("TopBar expone hamburger accesible en móvil", () => {
        const topBar = readSrc("Componets/TopBar.tsx");
        expect(topBar).toContain("showMobileMenuButton");
        expect(topBar).toContain("onMobileMenuOpen");
        expect(topBar).toContain('aria-label="Abrir menú de navegación"');
        expect(topBar).toContain("MenuIcon");
    });

    it("navegación única: getVisibleMenuSections en NavLeft", () => {
        const nav = readSrc("Componets/NavLeft.tsx");
        expect(nav).toContain("getVisibleMenuSections");
        expect(nav).toContain("visibleSections.map");
        expect(nav).not.toMatch(/items:\s*\[/);
    });

    it("shell evita overflow horizontal global en raíz", () => {
        const layout = readSrc("layouts/AppLayout.tsx");
        expect(layout).toContain('maxWidth: "100%"');
        expect(layout).toMatch(/overflowX:\s*"hidden"/);
    });

    it("drawer móvil reutiliza glassSidebar sin superficie glass paralela", () => {
        const navStyles = readSrc("styles/NavBarStyles.ts");
        expect(navStyles).toContain("styleNavDrawerPaper");
        expect(navStyles).toContain("StyleDrawerTemporary");
        expect(navStyles).toMatch(/StyleDrawerTemporary[\s\S]*styleNavDrawerPaper/);
        expect(navStyles).not.toContain('"0 16px 16px 0"');
        const layout = readSrc("layouts/AppLayout.tsx");
        expect(layout).toContain("...glassContent");
    });
});
