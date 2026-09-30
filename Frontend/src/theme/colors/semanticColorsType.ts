/**
 * Forma semántica compartida dark/light (FRONT-PROD.3).
 * Ambas paletas deben `satisfies SemanticColors` sin divergir estructura.
 */
export type SemanticColors = {
  surface: {
    app: string;
    sidebar: string;
    content: string;
    panel: string;
    panelSubtle: string;
    panelElevated: string;
    input: string;
    overlay: string;
    dialogTitle: string;
    dialogContent: string;
    dialogActions: string;
    tableHeader: string;
    tableRowEven: string;
    tableRowOdd: string;
    tableRowHover: string;
    tableRowSelected: string;
    tableRowSelectedHover: string;
    alertInfo: string;
    scrollbarTrack: string;
    scrollbarThumb: string;
    scrollbarThumbHover: string;
    analyticsCard: string;
    dashboardGlassCard: string;
    dashboardSection: string;
    dashboardSectionHeader: string;
  };
  calendar: {
    dayBg: string;
    dayHover: string;
    daySelected: string;
    daySelectedText: string;
    dayBorder: string;
    completarVerdeBg: string;
    completarVerdeText: string;
    completarAmarilloBg: string;
    completarAmarilloText: string;
    completarRojoBg: string;
    completarRojoText: string;
    completarNeutralBg: string;
    completarNeutralText: string;
    completarFooterText: string;
  };
  chart: {
    grid: string;
  };
  profile: {
    heroBackground: string;
  };
  text: {
    primary: string;
    secondary: string;
    muted: string;
    inverse: string;
    disabled: string;
  };
  border: {
    subtle: string;
    default: string;
    strong: string;
    active: string;
    neo: string;
  };
  action: {
    primary: string;
    primaryHover: string;
    primaryMuted: string;
    primaryGlow: string;
    hover: string;
    selected: string;
    tabSelected: string;
    tabSelectedHover: string;
    tabPrimarySelected: string;
    tabPrimarySelectedHover: string;
  };
  status: {
    success: string;
    successSurface: string;
    warning: string;
    warningSurface: string;
    error: string;
    errorSurface: string;
    info: string;
  };
  shadow: {
    sidebar: string;
    content: string;
    panel: string;
    neoOffset: string;
    authCard: string;
  };
  auth: {
    card: string;
    cardBorder: string;
    input: string;
    inputText: string;
    shadow: string;
    button: string;
  };
  primitive: {
    black: string;
    white: string;
    grayMedium: string;
    grayLight: string;
    grayLighter: string;
  };
};
