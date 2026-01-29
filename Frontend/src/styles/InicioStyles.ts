import { GLASS_COLORS } from "./GlassStyles";

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
    fontFamily: "Tactic Sans",
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
    fontFamily: "Tactic Sans",
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
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: GLASS_COLORS.hoverBg,
        borderColor: GLASS_COLORS.borderMedium,
        transform: "translateY(-2px)",
    },
};

export const StyleBoxTextCard = {
    textAlign: "center",
    marginTop: "20px",
};

export const StyleTextCard = {
    color: GLASS_COLORS.textPrimary,
    fontFamily: "Tactic Sans",
    fontWeight: 600,
    fontSize: "16px",
    lineHeight: 1.3,
};

export const StyleTextCardSecondary = {
    color: GLASS_COLORS.textMuted,
    fontFamily: "Tactic Sans",
    fontWeight: 400,
    fontSize: "13px",
    lineHeight: 1.4,
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
        fontFamily: "Tactic Sans",
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
        fontFamily: "Tactic Sans",
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








