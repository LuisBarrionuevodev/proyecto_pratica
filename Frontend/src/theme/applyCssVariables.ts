import { darkColors } from "./colors/dark";

/** Nombres de custom properties expuestas en `:root` para CSS global / librerías. */
export const CSS_VAR_NAMES = {
  surfaceApp: "--d-surface-app",
  surfaceSidebar: "--d-surface-sidebar",
  surfaceContent: "--d-surface-content",
  surfacePanel: "--d-surface-panel",
  surfacePanelSubtle: "--d-surface-panel-subtle",
  surfacePanelElevated: "--d-surface-panel-elevated",
  surfaceInput: "--d-surface-input",
  surfaceOverlay: "--d-surface-overlay",
  textPrimary: "--d-text-primary",
  textSecondary: "--d-text-secondary",
  textMuted: "--d-text-muted",
  borderSubtle: "--d-border-subtle",
  borderDefault: "--d-border-default",
  borderStrong: "--d-border-strong",
  borderActive: "--d-border-active",
  actionPrimary: "--d-action-primary",
  actionPrimaryHover: "--d-action-primary-hover",
  actionHover: "--d-action-hover",
  actionSelected: "--d-action-selected",
  statusSuccess: "--d-status-success",
  statusWarning: "--d-status-warning",
  statusError: "--d-status-error",
  statusInfo: "--d-status-info",
  tableRowEven: "--d-table-row-even",
  tableRowOdd: "--d-table-row-odd",
  scrollbarTrack: "--d-scrollbar-track",
  scrollbarThumb: "--d-scrollbar-thumb",
  scrollbarThumbHover: "--d-scrollbar-thumb-hover",
  primitiveBlack: "--d-primitive-black",
  primitiveWhite: "--d-primitive-white",
  borderNeo: "--d-border-neo",
  actionPrimaryMuted: "--d-action-primary-muted",
  surfaceAlertInfo: "--d-surface-alert-info",
} as const;

/**
 * Inyecta variables CSS desde `darkColors` (misma fuente que MUI / GLASS_COLORS).
 * Llamar una vez al arranque (main.tsx).
 */
export function applyDigitalizaCssVariables(root: HTMLElement = document.documentElement): void {
  const c = darkColors;
  const set = (name: string, value: string) => root.style.setProperty(name, value);

  set(CSS_VAR_NAMES.surfaceApp, c.surface.app);
  set(CSS_VAR_NAMES.surfaceSidebar, c.surface.sidebar);
  set(CSS_VAR_NAMES.surfaceContent, c.surface.content);
  set(CSS_VAR_NAMES.surfacePanel, c.surface.panel);
  set(CSS_VAR_NAMES.surfacePanelSubtle, c.surface.panelSubtle);
  set(CSS_VAR_NAMES.surfacePanelElevated, c.surface.panelElevated);
  set(CSS_VAR_NAMES.surfaceInput, c.surface.input);
  set(CSS_VAR_NAMES.surfaceOverlay, c.surface.overlay);
  set(CSS_VAR_NAMES.textPrimary, c.text.primary);
  set(CSS_VAR_NAMES.textSecondary, c.text.secondary);
  set(CSS_VAR_NAMES.textMuted, c.text.muted);
  set(CSS_VAR_NAMES.borderSubtle, c.border.subtle);
  set(CSS_VAR_NAMES.borderDefault, c.border.default);
  set(CSS_VAR_NAMES.borderStrong, c.border.strong);
  set(CSS_VAR_NAMES.borderActive, c.border.active);
  set(CSS_VAR_NAMES.actionPrimary, c.action.primary);
  set(CSS_VAR_NAMES.actionPrimaryHover, c.action.primaryHover);
  set(CSS_VAR_NAMES.actionHover, c.action.hover);
  set(CSS_VAR_NAMES.actionSelected, c.action.selected);
  set(CSS_VAR_NAMES.statusSuccess, c.status.success);
  set(CSS_VAR_NAMES.statusWarning, c.status.warning);
  set(CSS_VAR_NAMES.statusError, c.status.error);
  set(CSS_VAR_NAMES.statusInfo, c.status.info);
  set(CSS_VAR_NAMES.tableRowEven, c.surface.tableRowEven);
  set(CSS_VAR_NAMES.tableRowOdd, c.surface.tableRowOdd);
  set(CSS_VAR_NAMES.scrollbarTrack, c.surface.scrollbarTrack);
  set(CSS_VAR_NAMES.scrollbarThumb, c.surface.scrollbarThumb);
  set(CSS_VAR_NAMES.scrollbarThumbHover, c.surface.scrollbarThumbHover);
  set(CSS_VAR_NAMES.primitiveBlack, c.primitive.black);
  set(CSS_VAR_NAMES.primitiveWhite, c.primitive.white);
  set(CSS_VAR_NAMES.borderNeo, c.border.neo);
  set(CSS_VAR_NAMES.actionPrimaryMuted, c.action.primaryMuted);
  set(CSS_VAR_NAMES.surfaceAlertInfo, c.surface.alertInfo);
}
