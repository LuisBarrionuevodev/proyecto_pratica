import { GLASS_COLORS } from "./GlassStyles";
import { FONT_FAMILY_UI } from "../theme/typography";
import { CSS_VAR_NAMES } from "../theme/applyCssVariables";

// =============================================================================
// ESTILOS GLASSMORPHISM PARA INICIO
// =============================================================================

// Contenedor principal - glass oscuro
export const BoxInicio = {
    display: "flex",
    backgroundColor: "transparent",
    gap: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingTop: "20px",
    paddingBottom: "20px",
};

export const BoxTitulo = {
    marginLeft: "10%",
    width: { xs: "300px", sm: "500px", md: "600px" },
};

export const TitleStyle = {
    color: GLASS_COLORS.textPrimary,
    textShadow: "2px 2px 8px rgba(0, 0, 0, 0.5)",
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 800,
    fontSize: { xs: "28px", sm: "36px", md: "42px" },
};

export const BoxInputInicio = {
    justifyContent: { md: "space-evenly" },
    alignContent: "center",
};

export const ButtonStylesInicio = {
    width: { xs: "350px", sm: "500px", md: "500px" },
    height: "60px",
    borderRadius: "12px",
    backgroundColor: GLASS_COLORS.cardBg,
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 600,
    fontSize: { xs: "16px", sm: "18px" },
    color: GLASS_COLORS.textPrimary,
    textTransform: "none",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: GLASS_COLORS.hoverBg,
        transform: "scale(1.02)",
    },
};

export const LogoSumaStyle = {
    display: "flex",
    position: "absolute",
    width: { xs: "30px", sm: "40px", md: "40px" },
    marginRight: { xs: "300px", sm: "440px", md: "440px" },
    borderRadius: "12px",
    border: `2px solid ${GLASS_COLORS.borderLight}`,
};

// =============================================================================
// ESTILOS DE CARDS - Glass oscuro
// =============================================================================

export const CardStyle = {
    display: "flex",
    justifyContent: "flex-start",
    alignItems: "center",
    height: "120px",
    backgroundColor: GLASS_COLORS.cardBg,
    borderRadius: "14px",
    padding: "16px 20px",
    gap: 2,
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    transition: "background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease",
    "&:hover": {
        backgroundColor: GLASS_COLORS.hoverBg,
        borderColor: GLASS_COLORS.borderMedium,
        transform: "translateY(-2px)",
    },
};

/**
 * Cards de accesos en columna izquierda de Inicio: layout vertical (icono arriba, título y descripción abajo),
 * proporción más alta que ancha al ocupar el ancho de la grilla 2×3.
 */
export const CardStyleInicioAccesos = {
    ...CardStyle,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "flex-start",
    justifyContent: "flex-start",
    height: "auto",
    minHeight: "136px",
    padding: "14px 16px",
    gap: 0.75,
};

/**
 * Cáscara común para las 9 cards del dashboard Inicio (grilla 3×3): misma base visual y relleno de celda.
 */
export const InicioCardShellGrid = {
    ...CardStyle,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "flex-start",
    justifyContent: "flex-start",
    boxSizing: "border-box" as const,
    height: "100%",
    minHeight: 0,
    padding: "14px 16px",
    gap: 0.75,
    overflow: "auto",
};

/** Misma estética que CardStyle, altura flexible para cards de columna derecha (Inicio). */
export const InicioCardStyleColumn = {
    ...CardStyle,
    height: "auto",
    minHeight: "152px",
    flexDirection: "column" as const,
    alignItems: "flex-start",
    justifyContent: "center",
    padding: "18px 18px",
};

/** Card fina (misma línea visual, menos padding) para columna derecha de Inicio. */
export const InicioCardStyleFina = {
    ...CardStyle,
    height: "auto",
    minHeight: "138px",
    flexDirection: "column" as const,
    alignItems: "flex-start",
    justifyContent: "center",
    padding: "14px 18px",
    gap: 0.75,
};

export const StyleBoxTextCard = {
    textAlign: "center",
    marginTop: "20px",
};

export const StyleTextCard = {
    color: GLASS_COLORS.textPrimary,
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 600,
    fontSize: "16px",
    lineHeight: 1.3,
};

export const StyleTextCardSecondary = {
    color: GLASS_COLORS.textMuted,
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 400,
    fontSize: "13px",
    lineHeight: 1.4,
};

/** Desktop: tipografía ligeramente mayor en cards de acceso (xs/sm sin cambio). */
export const InicioAccesoCardTitleSx = {
    ...StyleTextCard,
    fontSize: { xs: "15px", md: "16px", lg: "17px" },
};

export const InicioAccesoCardDescriptionSx = {
    ...StyleTextCardSecondary,
    fontSize: { xs: "12px", md: "13px", lg: "14px" },
    lineHeight: 1.45,
};

/** Cáscara desktop: más padding y altura mínima moderada (solo md+). */
export const InicioCardShellGridDesktop = {
    padding: { xs: "14px 16px", md: "18px 20px", lg: "20px 22px" },
    minHeight: { xs: "unset", md: "148px", lg: "156px" },
    gap: { xs: 0.75, md: 1, lg: 1.1 },
};

/** Card institucional horizontal bajo la grilla de accesos. */
export const InicioAboutCardShell = {
    ...InicioCardShellGrid,
    flexDirection: { xs: "column" as const, md: "row" as const },
    alignItems: { xs: "flex-start", md: "center" },
    justifyContent: "space-between",
    width: "100%",
    padding: { xs: "14px 16px", md: "20px 24px", lg: "22px 28px" },
    gap: { xs: 1.5, md: 3 },
    minHeight: { xs: "unset", md: "auto" },
};

export const InicioAboutCtaSx = {
    ...ButtonStylesInicio,
    width: { xs: "100%", md: "auto" },
    minWidth: { md: 168 },
    height: { xs: 44, md: 44 },
    fontSize: { xs: "14px", md: "14px" },
    fontWeight: 500,
    flexShrink: 0,
    textAlign: "center",
};

/** Fila desktop: card Mapa ancha con imagen a la derecha. */
export const InicioMapaHeroShellSx = {
    ...InicioCardShellGrid,
    display: "flex",
    flexDirection: "row" as const,
    alignItems: "stretch",
    width: "100%",
    minHeight: { md: 196, lg: 220 },
    padding: { md: "22px 24px", lg: "24px 28px" },
    boxSizing: "border-box" as const,
    position: "relative",
    overflow: "hidden",
    backgroundSize: "cover",
    backgroundPosition: "right center",
    backgroundRepeat: "no-repeat",
    "&::before": {
        content: '""',
        position: "absolute",
        inset: 0,
        borderRadius: "inherit",
        background: `linear-gradient(90deg, var(${CSS_VAR_NAMES.surfaceOverlay}) 0%, var(${CSS_VAR_NAMES.surfaceOverlay}) 42%, transparent 78%)`,
        pointerEvents: "none",
    },
};

export const InicioMapaHeroTextSx = {
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 600,
    lineHeight: 1.35,
};

// =============================================================================
// BUSCADOR - Estilo prominente sobre fondo transparente (como Early Bird)
// =============================================================================

export const SearchFieldStyles = {
    width: { xs: "90%", sm: "500px", md: "650px", lg: "750px" },
    "& .MuiInputBase-root": {
        backgroundColor: GLASS_COLORS.cardBg,
        borderRadius: "50px", // Pill shape como Early Bird
        color: GLASS_COLORS.textPrimary,
        border:`1px solid ${GLASS_COLORS.borderLight}`,
        fontFamily: FONT_FAMILY_UI,
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.15)",
        transition: "all 0.2s ease",
        "&:hover": {
            boxShadow: "0 6px 25px rgba(0, 0, 0, 0.2)",
        },
        "&.Mui-focused": {
            boxShadow: "0 6px 30px rgba(0, 0, 0, 0.25)",
        },
    },
    "& .MuiInputBase-input": {
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 500,
        padding: "16px 24px",
        fontSize: "16px",
        "&::placeholder": {
            color: GLASS_COLORS.textPrimary,
            opacity: 1,
        },
    },
    "& .MuiOutlinedInput-notchedOutline": {
        border: "none",
    },
    "& .MuiInputAdornment-root": {
        marginLeft: "12px",
    },
};








