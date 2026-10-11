import { GLASS_COLORS } from "./GlassStyles";
import { FONT_FAMILY_UI } from "../theme/typography";
import { ButtonStylesInicio } from "./InicioStyles";

export const acercaDePageSx = {
  display: "flex",
  flexDirection: "column" as const,
  height: "100vh",
  width: "100vw",
  overflow: "hidden",
  bgcolor: "transparent",
};

export const acercaDeScrollSx = {
  flex: 1,
  minHeight: 0,
  overflow: "auto",
  backgroundColor: "transparent",
};

export const acercaDeContentSx = {
  p: { xs: 2, sm: 3, md: 4 },
  maxWidth: { md: 880, lg: 960 },
  mx: "auto",
  width: "100%",
  boxSizing: "border-box" as const,
};

export const acercaDeSectionSx = {
  backgroundColor: GLASS_COLORS.cardBg,
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "14px",
  p: { xs: 2, sm: 2.5, md: 3 },
  mb: { xs: 2, md: 2.5 },
};

export const acercaDeTitleSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: { xs: "1.35rem", sm: "1.5rem", md: "1.75rem" },
  color: GLASS_COLORS.textPrimary,
  mb: { xs: 2, md: 2.5 },
  lineHeight: 1.25,
};

export const acercaDeSectionTitleSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 600,
  fontSize: { xs: "1.05rem", md: "1.125rem" },
  color: GLASS_COLORS.textPrimary,
  mb: 1,
};

export const acercaDeBodySx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 400,
  fontSize: { xs: "0.9375rem", md: "1rem" },
  color: GLASS_COLORS.textMuted,
  lineHeight: 1.55,
};

export const acercaDeBackButtonSx = {
  ...ButtonStylesInicio,
  width: { xs: "100%", sm: "auto" },
  minWidth: { sm: 240 },
  height: { xs: 48, sm: 52 },
  mt: { xs: 1, md: 2 },
  fontSize: { xs: "15px", md: "16px" },
};
