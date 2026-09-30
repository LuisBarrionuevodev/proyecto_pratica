import type { SemanticColors } from "./colors/semanticColorsType";

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
  surfaceDialogTitle: "--d-surface-dialog-title",
  surfaceDialogContent: "--d-surface-dialog-content",
  surfaceDialogActions: "--d-surface-dialog-actions",
  textPrimary: "--d-text-primary",
  textSecondary: "--d-text-secondary",
  textMuted: "--d-text-muted",
  textInverse: "--d-text-inverse",
  textDisabled: "--d-text-disabled",
  borderSubtle: "--d-border-subtle",
  borderDefault: "--d-border-default",
  borderStrong: "--d-border-strong",
  borderActive: "--d-border-active",
  actionPrimary: "--d-action-primary",
  actionPrimaryHover: "--d-action-primary-hover",
  actionPrimaryMuted: "--d-action-primary-muted",
  actionPrimaryGlow: "--d-action-primary-glow",
  actionHover: "--d-action-hover",
  actionSelected: "--d-action-selected",
  actionTabSelected: "--d-action-tab-selected",
  actionTabSelectedHover: "--d-action-tab-selected-hover",
  actionTabPrimarySelected: "--d-action-tab-primary-selected",
  actionTabPrimarySelectedHover: "--d-action-tab-primary-selected-hover",
  statusSuccess: "--d-status-success",
  statusWarning: "--d-status-warning",
  statusError: "--d-status-error",
  statusInfo: "--d-status-info",
  tableRowEven: "--d-table-row-even",
  tableRowOdd: "--d-table-row-odd",
  tableRowHover: "--d-table-row-hover",
  tableRowSelected: "--d-table-row-selected",
  tableRowSelectedHover: "--d-table-row-selected-hover",
  scrollbarTrack: "--d-scrollbar-track",
  scrollbarThumb: "--d-scrollbar-thumb",
  scrollbarThumbHover: "--d-scrollbar-thumb-hover",
  primitiveBlack: "--d-primitive-black",
  primitiveWhite: "--d-primitive-white",
  borderNeo: "--d-border-neo",
  surfaceAlertInfo: "--d-surface-alert-info",
  shadowSidebar: "--d-shadow-sidebar",
  shadowContent: "--d-shadow-content",
  shadowPanel: "--d-shadow-panel",
  surfaceAnalyticsCard: "--d-surface-analytics-card",
  surfaceDashboardGlassCard: "--d-surface-dashboard-glass-card",
  surfaceDashboardSection: "--d-surface-dashboard-section",
  surfaceDashboardSectionHeader: "--d-surface-dashboard-section-header",
  calendarDayBg: "--d-calendar-day-bg",
  calendarDayHover: "--d-calendar-day-hover",
  calendarDaySelected: "--d-calendar-day-selected",
  calendarDaySelectedText: "--d-calendar-day-selected-text",
  calendarDayBorder: "--d-calendar-day-border",
  calendarCompletarVerdeBg: "--d-calendar-completar-verde-bg",
  calendarCompletarVerdeText: "--d-calendar-completar-verde-text",
  calendarCompletarAmarilloBg: "--d-calendar-completar-amarillo-bg",
  calendarCompletarAmarilloText: "--d-calendar-completar-amarillo-text",
  calendarCompletarRojoBg: "--d-calendar-completar-rojo-bg",
  calendarCompletarRojoText: "--d-calendar-completar-rojo-text",
  calendarCompletarNeutralBg: "--d-calendar-completar-neutral-bg",
  calendarCompletarNeutralText: "--d-calendar-completar-neutral-text",
  calendarCompletarFooterText: "--d-calendar-completar-footer-text",
  chartGrid: "--d-chart-grid",
  profileHeroBackground: "--d-profile-hero-bg",
  statusSuccessSurface: "--d-status-success-surface",
  statusWarningSurface: "--d-status-warning-surface",
  statusErrorSurface: "--d-status-error-surface",
} as const;

/**
 * Inyecta variables CSS desde la paleta semántica activa (dark o light).
 */
export function applyDigitalizaCssVariables(
  colors: SemanticColors,
  root: HTMLElement = document.documentElement
): void {
  const c = colors;
  const set = (name: string, value: string) => root.style.setProperty(name, value);

  set(CSS_VAR_NAMES.surfaceApp, c.surface.app);
  set(CSS_VAR_NAMES.surfaceSidebar, c.surface.sidebar);
  set(CSS_VAR_NAMES.surfaceContent, c.surface.content);
  set(CSS_VAR_NAMES.surfacePanel, c.surface.panel);
  set(CSS_VAR_NAMES.surfacePanelSubtle, c.surface.panelSubtle);
  set(CSS_VAR_NAMES.surfacePanelElevated, c.surface.panelElevated);
  set(CSS_VAR_NAMES.surfaceInput, c.surface.input);
  set(CSS_VAR_NAMES.surfaceOverlay, c.surface.overlay);
  set(CSS_VAR_NAMES.surfaceDialogTitle, c.surface.dialogTitle);
  set(CSS_VAR_NAMES.surfaceDialogContent, c.surface.dialogContent);
  set(CSS_VAR_NAMES.surfaceDialogActions, c.surface.dialogActions);
  set(CSS_VAR_NAMES.textPrimary, c.text.primary);
  set(CSS_VAR_NAMES.textSecondary, c.text.secondary);
  set(CSS_VAR_NAMES.textMuted, c.text.muted);
  set(CSS_VAR_NAMES.textInverse, c.text.inverse);
  set(CSS_VAR_NAMES.textDisabled, c.text.disabled);
  set(CSS_VAR_NAMES.borderSubtle, c.border.subtle);
  set(CSS_VAR_NAMES.borderDefault, c.border.default);
  set(CSS_VAR_NAMES.borderStrong, c.border.strong);
  set(CSS_VAR_NAMES.borderActive, c.border.active);
  set(CSS_VAR_NAMES.actionPrimary, c.action.primary);
  set(CSS_VAR_NAMES.actionPrimaryHover, c.action.primaryHover);
  set(CSS_VAR_NAMES.actionPrimaryMuted, c.action.primaryMuted);
  set(CSS_VAR_NAMES.actionPrimaryGlow, c.action.primaryGlow);
  set(CSS_VAR_NAMES.actionHover, c.action.hover);
  set(CSS_VAR_NAMES.actionSelected, c.action.selected);
  set(CSS_VAR_NAMES.actionTabSelected, c.action.tabSelected);
  set(CSS_VAR_NAMES.actionTabSelectedHover, c.action.tabSelectedHover);
  set(CSS_VAR_NAMES.actionTabPrimarySelected, c.action.tabPrimarySelected);
  set(CSS_VAR_NAMES.actionTabPrimarySelectedHover, c.action.tabPrimarySelectedHover);
  set(CSS_VAR_NAMES.statusSuccess, c.status.success);
  set(CSS_VAR_NAMES.statusWarning, c.status.warning);
  set(CSS_VAR_NAMES.statusError, c.status.error);
  set(CSS_VAR_NAMES.statusInfo, c.status.info);
  set(CSS_VAR_NAMES.tableRowEven, c.surface.tableRowEven);
  set(CSS_VAR_NAMES.tableRowOdd, c.surface.tableRowOdd);
  set(CSS_VAR_NAMES.tableRowHover, c.surface.tableRowHover);
  set(CSS_VAR_NAMES.tableRowSelected, c.surface.tableRowSelected);
  set(CSS_VAR_NAMES.tableRowSelectedHover, c.surface.tableRowSelectedHover);
  set(CSS_VAR_NAMES.scrollbarTrack, c.surface.scrollbarTrack);
  set(CSS_VAR_NAMES.scrollbarThumb, c.surface.scrollbarThumb);
  set(CSS_VAR_NAMES.scrollbarThumbHover, c.surface.scrollbarThumbHover);
  set(CSS_VAR_NAMES.primitiveBlack, c.primitive.black);
  set(CSS_VAR_NAMES.primitiveWhite, c.primitive.white);
  set(CSS_VAR_NAMES.borderNeo, c.border.neo);
  set(CSS_VAR_NAMES.surfaceAlertInfo, c.surface.alertInfo);
  set(CSS_VAR_NAMES.shadowSidebar, c.shadow.sidebar);
  set(CSS_VAR_NAMES.shadowContent, c.shadow.content);
  set(CSS_VAR_NAMES.shadowPanel, c.shadow.panel);
  set(CSS_VAR_NAMES.surfaceAnalyticsCard, c.surface.analyticsCard);
  set(CSS_VAR_NAMES.surfaceDashboardGlassCard, c.surface.dashboardGlassCard);
  set(CSS_VAR_NAMES.surfaceDashboardSection, c.surface.dashboardSection);
  set(CSS_VAR_NAMES.surfaceDashboardSectionHeader, c.surface.dashboardSectionHeader);
  set(CSS_VAR_NAMES.calendarDayBg, c.calendar.dayBg);
  set(CSS_VAR_NAMES.calendarDayHover, c.calendar.dayHover);
  set(CSS_VAR_NAMES.calendarDaySelected, c.calendar.daySelected);
  set(CSS_VAR_NAMES.calendarDaySelectedText, c.calendar.daySelectedText);
  set(CSS_VAR_NAMES.calendarDayBorder, c.calendar.dayBorder);
  set(CSS_VAR_NAMES.calendarCompletarVerdeBg, c.calendar.completarVerdeBg);
  set(CSS_VAR_NAMES.calendarCompletarVerdeText, c.calendar.completarVerdeText);
  set(CSS_VAR_NAMES.calendarCompletarAmarilloBg, c.calendar.completarAmarilloBg);
  set(CSS_VAR_NAMES.calendarCompletarAmarilloText, c.calendar.completarAmarilloText);
  set(CSS_VAR_NAMES.calendarCompletarRojoBg, c.calendar.completarRojoBg);
  set(CSS_VAR_NAMES.calendarCompletarRojoText, c.calendar.completarRojoText);
  set(CSS_VAR_NAMES.calendarCompletarNeutralBg, c.calendar.completarNeutralBg);
  set(CSS_VAR_NAMES.calendarCompletarNeutralText, c.calendar.completarNeutralText);
  set(CSS_VAR_NAMES.calendarCompletarFooterText, c.calendar.completarFooterText);
  set(CSS_VAR_NAMES.chartGrid, c.chart.grid);
  set(CSS_VAR_NAMES.profileHeroBackground, c.profile.heroBackground);
  set(CSS_VAR_NAMES.statusSuccessSurface, c.status.successSurface);
  set(CSS_VAR_NAMES.statusWarningSurface, c.status.warningSurface);
  set(CSS_VAR_NAMES.statusErrorSurface, c.status.errorSurface);
}
