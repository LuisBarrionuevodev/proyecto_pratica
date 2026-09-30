/** @jsxImportSource react */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { AppDialog } from "../ui/AppDialog";
import { ResponsiveFiltersPanel } from "../ui/ResponsiveFiltersPanel";
import { ResponsiveFormGrid } from "../ui/ResponsiveFormGrid";
import { ResponsiveScrollableTabs } from "../ui/ResponsiveScrollableTabs";
import Tab from "@mui/material/Tab";
import {
    responsiveDialogFullscreenPaperLayoutSx,
    responsiveDialogPaperLayoutSx,
    responsiveFormGridSx,
    responsiveScrollableTabsLayoutSx,
} from "./responsivePatterns";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
    return readFileSync(join(root, rel), "utf8");
}

const theme = createTheme();

function render(ui: React.ReactElement) {
    return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("V1.1-RESP.2 — responsivePatterns", () => {
    it("dialog layout mobile usa márgenes sin redefinir glassDialogPaperSx", () => {
        const glass = readSrc("styles/GlassStyles.ts");
        const patterns = readSrc("styles/responsivePatterns.ts");
        expect(glass).toContain("glassDialogPaperSx");
        expect(patterns).toContain("responsiveDialogPaperLayoutSx");
        expect(patterns).not.toMatch(/import\s*\{[^}]*glassDialogPaperSx/);
        expect(patterns).toContain("899.95px");
        expect(patterns).toContain("599.95px");
    });

    it("AppDialog integra responsiveLayout y mobileFullScreen", () => {
        const appDialog = readSrc("ui/AppDialog.tsx");
        expect(appDialog).toContain("responsiveDialogPaperLayoutSx");
        expect(appDialog).toContain("mobileFullScreen");
        expect(appDialog).toContain("glassDialogPaperSx");
        const html = render(
            <AppDialog
                open
                disablePortal
                hideBackdrop
                appearance="glass"
                title="T"
                onClose={() => undefined}
            >
                body
            </AppDialog>
        );
        expect(html).toContain("MuiDialog-paper");
    });

    it("tabs mobile: scrollable y flex nowrap", () => {
        const tabsSrc = readSrc("ui/ResponsiveScrollableTabs.tsx");
        expect(tabsSrc).toContain('variant ?? (isDesktop ? "standard" : "scrollable")');
        expect(tabsSrc).toContain("glassTabsSecondaryPanelBarSx");
        expect(readSrc("styles/responsivePatterns.ts")).toMatch(/flexWrap:\s*"nowrap"/);
        const html = render(
            <ResponsiveScrollableTabs value={0}>
                <Tab label="Uno" />
                <Tab label="Dos" />
            </ResponsiveScrollableTabs>
        );
        expect(html).toContain("MuiTabs-root");
    });

    it("filtros: toggle y contenido montado en Collapse", () => {
        const filtersSrc = readSrc("ui/ResponsiveFiltersPanel.tsx");
        expect(filtersSrc).toContain("Mostrar filtros");
        expect(filtersSrc).toContain("Collapse");
        const html = render(
            <ResponsiveFiltersPanel activeFiltersSlot={<span data-chip="1">Activo</span>}>
                <input name="demo" />
            </ResponsiveFiltersPanel>
        );
        expect(html).toContain("Activo");
        expect(html).toContain('name="demo"');
    });

    it("form grid una columna en xs", () => {
        expect(readSrc("styles/formDialogStyles.ts")).toContain("gridTemplateColumns");
        const html = render(
            <ResponsiveFormGrid>
                <span>Campo</span>
            </ResponsiveFormGrid>
        );
        expect(html).toContain("Campo");
    });

    it("no agrega colores hex/rgba nuevos en responsivePatterns", () => {
        const patterns = readSrc("styles/responsivePatterns.ts");
        expect(patterns).not.toMatch(/#[0-9a-fA-F]{3,8}/);
        expect(patterns).not.toMatch(/rgba?\(/);
        expect(patterns).not.toContain("backdropFilter");
    });

    it("GlassStyles glassContent y glassSidebar intactos", () => {
        const glass = readSrc("styles/GlassStyles.ts");
        expect(glass).toContain("export const glassContent");
        expect(glass).toContain("export const glassSidebar");
        expect(glass).not.toContain("responsiveDialogPaperLayoutSx");
    });
});
