import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { CSS_VAR_NAMES } from "./applyCssVariables";
import { darkColors, lightColors } from "./colors";
import { moduleSlicesTabsSx } from "../styles/GlassStyles";
import { dashboardAnalyticsCardSx } from "../styles/DashboardStyles";
import { createGridTheme } from "../Containers/CargarActuaciones/config/gridTheme";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readSrc(rel: string): string {
  return readFileSync(join(root, rel), "utf8");
}

describe("FRONT-PROD.3.2 — light visual polish guards", () => {
  it("LogoSMT no está referenciado en el frontend", () => {
    const calendar = readSrc("components/calendar/InstitutionalMonthCalendarGrid.tsx");
    expect(calendar).not.toContain("#FFFFFF");
    expect(calendar).toContain("CSS_VAR_NAMES.calendarDayBg");
    expect(calendar).toContain("GLASS_COLORS.textPrimary");
    const topBar = readSrc("Componets/TopBar.tsx");
    const login = readSrc("Containers/Login/Components/LoginBox.tsx");
    expect(topBar + login).not.toMatch(/LogoSMT/i);
  });

  it("Perfil evita hardcodes dark core en estilos", () => {
    const perfil = readSrc("styles/PerfilStyles.ts");
    expect(perfil).not.toContain("#2B2E34");
    expect(perfil).not.toContain("#3a3d44");
    expect(perfil).toContain("profileHeroBg");
    expect(perfil).toContain("profileInputStyle");
  });

  it("Dashboard analytics card usa token semántico", () => {
    expect(dashboardAnalyticsCardSx.backgroundColor).toContain("--d-surface-analytics-card");
    expect(darkColors.surface.analyticsCard).toBe("rgba(12, 18, 32, 0.72)");
    expect(lightColors.surface.analyticsCard).toContain("255");
  });

  it("tabs compartidos usan GLASS_COLORS (no blanco fijo)", () => {
    const tabs = moduleSlicesTabsSx as Record<string, unknown>;
    const tabRoot = tabs["& .MuiTab-root"] as Record<string, unknown>;
    expect(String(tabRoot.color)).toContain("--d-text-secondary");
    expect(String(tabRoot.color)).not.toBe("#FFFFFF");
  });

  it("Glide light usa texto primario oscuro en celdas principales", () => {
    const theme = createGridTheme(lightColors);
    expect(theme.textHeader).toBe("#18202C");
    expect(theme.textMedium).toBe("#18202C");
    expect(theme.textDark).toBe("#18202C");
  });

  it("calendario y chart exponen variables CSS", () => {
    expect(CSS_VAR_NAMES.calendarDayBg).toBe("--d-calendar-day-bg");
    expect(CSS_VAR_NAMES.chartGrid).toBe("--d-chart-grid");
    expect(lightColors.calendar.dayBorder).toBe("#D4DAE3");
  });

  it("fondo light solo en shell autenticado (CSS)", () => {
    const css = readSrc("index.css");
    expect(css).toContain("body.authenticated-route");
    expect(css).toMatch(
      /\[data-theme="light"\] body\.authenticated-route[\s\S]*BackgroundInicioLight\.png/
    );
    expect(css).toMatch(/body\.public-route[\s\S]*BackgroundInicio2\.png/);
  });
});
