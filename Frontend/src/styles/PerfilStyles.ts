import { FONT_FAMILY_UI } from "../theme/typography";
import { CSS_VAR_NAMES } from "../theme/applyCssVariables";
import { GLASS_COLORS } from "./GlassStyles";

const profileHeroBg = `var(${CSS_VAR_NAMES.profileHeroBackground})`;

export const BoxPerfilStyle = {
    background: profileHeroBg,
    minHeight: { xs: "180px", sm: "200px", md: "220px" },
    widht:"100vw",
    padding: { xs: 3, sm: 4, md: 5 },
    display: "flex",
    alignItems: "center",
    flexDirection:{xs:"column", md:"row"},
    gap: { xs: 2, sm: 3 },
}

export const InputCambiarInfoStyle = {
    position: "relative",
    backgroundColor: "#D9D9D9",
    width: { sm: "450px" },
    fontSize: "22px",
    borderRadius: "10px",
    "& .MuiInputBase-input": {
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 500,
        zIndex: 1,
    },

    '& .MuiOutlinedInput-root': {
        borderRadius: "10px",
        "&::after": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            boxShadow: " 6px 6px 2px #000000",
            borderRadius: "10px",
            opacity: 0,
            transition: "opacity 0.3s ease-in-out",
            zIndex: 1,
        },

        '&.Mui-focused': {
            "&::after": {
                opacity: 1,
            },
        },
    },
}

/** Inputs de perfil (dark/light vía tokens). */
export const profileInputStyle = {
    width: "100%",
    "& .MuiInputBase-input": {
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 500,
        color: GLASS_COLORS.textPrimary,
        fontSize: "14px",
    },
    "& .MuiOutlinedInput-root": {
        backgroundColor: `var(${CSS_VAR_NAMES.surfaceInput})`,
        borderRadius: "8px",
        "& fieldset": {
            borderColor: GLASS_COLORS.borderMedium,
        },
        "&:hover fieldset": {
            borderColor: `var(${CSS_VAR_NAMES.borderStrong})`,
        },
        "&.Mui-focused fieldset": {
            borderColor: GLASS_COLORS.primary,
            borderWidth: "2px",
        },
    },
    "& .MuiInputBase-input::placeholder": {
        color: GLASS_COLORS.textMuted,
        opacity: 1,
    },
};

/** @deprecated Usar `profileInputStyle`. */
export const inputDarkStyle = profileInputStyle;

export const profilePasswordCardSx = {
    backgroundColor: GLASS_COLORS.cardBg,
    borderRadius: "16px",
    border: `1px solid ${GLASS_COLORS.borderMedium}`,
    boxShadow: `var(${CSS_VAR_NAMES.shadowPanel})`,
    display: "flex",
    flexDirection: "column",
    width: { xs: "230px", sm: "450px", md: "550px" },
    gap: 3,
    p: { xs: 3, sm: 4 },
} as const;

export const profileFieldLabelSx = {
    fontFamily: FONT_FAMILY_UI,
    ml: 1,
    mb: 1,
    fontSize: 13,
    fontWeight: 500,
    color: GLASS_COLORS.textSecondary,
} as const;

export const EditNombreStyle = {

    width: "100%",
    input: {
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 800,
        fontSize: {
            xs: "28px",
            sm: "42px",
            md: "56px",
            lg: "64px",
        },
        color: GLASS_COLORS.textPrimary,
    }
}

export const InfoPerfilStyle = {
    fontFamily: FONT_FAMILY_UI,
    fontSize: "12px",
    color: GLASS_COLORS.textSecondary,
    textTransform: "uppercase",
}

export const AvatarPerfilStye = {
    width: { xs: 100, sm: 140, md: 180 },
    height: { xs: 100, sm: 140, md: 180 },
    border: `4px solid var(${CSS_VAR_NAMES.borderStrong})`,
    boxShadow: `var(${CSS_VAR_NAMES.shadowPanel})`,
    cursor: "pointer",
    transition: "0.2s",
    "&:hover": {
        transform: "scale(1.03)",
    },
}

export const NombrePerfilStyle = {
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 800,
    fontSize: {
        xs: "20px",
        sm: "40px",
        md: "56px",
        lg: "64px",
    },
    color: GLASS_COLORS.textPrimary,
    lineHeight: 1,
    textAlign:""
}

export const RolPerfilStyle = {
    fontFamily: FONT_FAMILY_UI,
    fontSize: {xs:"10px",sm:"14px"},
    color: GLASS_COLORS.textSecondary,
}

export const buttonStyle = {
    backgroundColor: "#0166FF",
    color: "#FFFFFF",
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 600,
    fontSize: "14px",
    height: "48px",
    width: "100%",
    borderRadius: "24px",
    textTransform: "none",
    mt: 2,
    transition: "all 0.2s ease",
    "&:hover": {
        backgroundColor: "#0055DD",
        transform: "scale(1.02)",
    },
};

export const ButtonGuardarInfoStyle = {
    backgroundColor: "#0166FF",
    color: "white",
    height: "40px",
    width: { sm: "440px" },
    borderRadius: "5px",
    position: "relative",
    "&::after": {
        content: '""',
        position: "absolute",
        width: "100%",
        height: "100%",
        boxShadow: "6px 6px 3px #000000",
        opacity: 0,
        transition: "opacity 0.3s",
        borderRadius: "5px",
    },
    "&:hover::after": {
        opacity: 1,
    },
}
