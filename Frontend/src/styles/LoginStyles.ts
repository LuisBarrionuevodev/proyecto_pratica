import { FONT_FAMILY_UI } from "../theme/typography";
import { darkColors } from "../theme/colors";

const auth = darkColors.auth;
const shadow = darkColors.shadow;
export const LoginBoxGlobalStyle = {
    display: "flex",
    justifyContent: "center",
    alignContent: "center",
    width: "100%",
    minWidth: 0,
}
export const LoginBoxStyle = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    width: "100%",
    maxWidth: { xs: "100%", sm: 455, md: 460 },
    borderRadius: "10px",
    background: auth.card,
    border: `1px solid ${auth.cardBorder}`,
    boxShadow: { xs: `8px 8px 0px ${auth.shadow}`, sm: shadow.authCard },
    boxSizing: "border-box",
    gap: { xs: 1.75, sm: 2.25 },
    px: { xs: 2.5, sm: 4 },
    pt: { xs: 3, sm: 4 },
    pb: { xs: 3, sm: 3 },
}

export const LoginLogoStyle = {
    display: "flex", 
    alignItems:"center",
    justifySelf: "center", 
    flexDirection: "column"
    
}

export const LoginBoxInputStyles = {
    display: "flex",
    alignItems: "center",
    justifyItems: "center",
    flexDirection: "column",
    gap: { xs: 1.75, sm: 2.25 },
    width: "100%",
    maxWidth: { xs: "100%", sm: 380 },
    minWidth: 0,
    alignSelf: "center",
    pb: 0,
}
export const InputStyles = {
    position: "relative",
    backgroundColor: auth.input,
    width: "100%",
    maxWidth: { xs: "100%", sm: 380 },
    fontSize: { xs: "16px", sm: "22px" },
    borderRadius: "10px",
    "& .MuiInputBase-input": {
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 500,
        color: auth.inputText,
        zIndex: 1,
        fontSize: { xs: "16px", sm: "22px" },
    },
    "& .MuiInputBase-input::placeholder": {
        color: auth.inputText,
        opacity: 1,
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
            boxShadow: ` 6px 6px 2px ${auth.shadow}`,
            borderRadius: "10px",
            opacity: 0,
            transition: "opacity 0.3s ease-in-out",
            zIndex: 1,
            pointerEvents: "none",
        },

        '&.Mui-focused': {
            "&::after": {
                opacity: 1,
            },
        },
    },
};


export const ButtonStyle = {
    backgroundColor: auth.button,
    width: "100%",
    maxWidth: { xs: "100%", sm: 380 },
    minHeight: { xs: 44, sm: 25 },
    height: { xs: 44, sm: 25 },
    fontFamily: FONT_FAMILY_UI,
    fontWeight: 200,
    color: "white",
    zIndex: 1,
    borderRadius: "5px",
    transition: "transform 0.4s ease-in-out",
    "&::after": {
        content: '""',
        position: "absolute",
        width: "100%",
        height: "100%",
        boxShadow: `6px 6px 3px ${auth.shadow}`,
        opacity: 0,
        transition: "opacity 0.4s ease-in-out",
        zIndex: -1,
        borderRadius: "5px",
    },

    ':hover': {
        "&::after": {
            opacity: 1,
        },
    },
};
