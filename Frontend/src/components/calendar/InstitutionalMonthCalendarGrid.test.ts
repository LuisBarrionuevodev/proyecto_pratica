import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("InstitutionalMonthCalendarGrid", () => {
  const grid = read("src/components/calendar/InstitutionalMonthCalendarGrid.tsx");

  it("expone props de tamaño y footer personalizable", () => {
    expect(grid).toContain("cellMinHeight?: number");
    expect(grid).toContain("cellGap?: number");
    expect(grid).toContain("renderDayFooter?:");
    expect(grid).toContain("getDayButtonSx?:");
  });

  it("selección agrega ring primary sin reemplazar bgcolor del llamador", () => {
    expect(grid).toContain("boxShadow: ctx.selected ? `0 0 0 2px ${GLASS_COLORS.primary}` : \"none\"");
    expect(grid).toContain("...extraSx");
  });

  it("COMPLETAR-UX.1.2: un único indicador HOY en esquina superior derecha", () => {
    expect(grid).toContain('"&::after"');
    expect(grid).toContain("top: 6");
    expect(grid).toContain("right: 6");
    expect(grid).toContain("boxShadow: ctx.selected");
    const afterBlocks = grid.match(/"&::after"/g) ?? [];
    expect(afterBlocks).toHaveLength(1);
    expect(grid).not.toContain("width: 5");
    expect(grid).not.toContain("opacity: 0.85");
  });

  it("sin footer no agrega punto azul bajo el número del día", () => {
    expect(grid).toContain("footerEl !== undefined ? footerEl : <Box sx={{ height: 5 }} />");
    expect(grid).not.toContain("opacity: 0.85");
  });
});
