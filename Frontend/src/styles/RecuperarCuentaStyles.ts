import { FONT_FAMILY_UI } from "../theme/typography";
import { darkColors } from "../theme/colors";

const auth = darkColors.auth;
const shadow = darkColors.shadow;
export const InputRecuperarStyles = {
    position: "relative",
    backgroundColor: auth.input,
    width: "450px",
    fontSize: "22px",
    borderRadius: "10px",
    "& .MuiInputBase-input": {
        fontFamily: FONT_FAMILY_UI,
        fontWeight: 500,
        color: auth.inputText,
        zIndex: 1,
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

export const BoxRecuperarContenidoStyles = {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "600px",
    height: "300px",
    borderRadius: "10px",
    background: auth.card,
    border: `1px solid ${auth.cardBorder}`,
    boxShadow: shadow.authCard,
    gap: 3,
    mt: "50px",
}

export const BoxNuevaContraseñaStyles = {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "600px",
    height: "300px",
    borderRadius: "10px",
    background: auth.card,
    border: `1px solid ${auth.cardBorder}`,
    boxShadow: shadow.authCard,
    gap: 3,
    p: 2,
    mt: "40px",
}

export const ErrorTextRecuperarStyles = {
    textAlign:"center",
    color: "red", 
    fontSize: 15, 
    fontWeight: 500
}

export const ButtonRecuperarStyles = {
    backgroundColor: auth.button,
    color: "white",
    height: "40px",
    width: "500px",
    borderRadius: "5px",
    position: "relative",
    "&::after": {
        content: '""',
        position: "absolute",
        width: "100%",
        height: "100%",
        boxShadow: `6px 6px 3px ${auth.shadow}`,
        opacity: 0,
        transition: "opacity 0.3s",
        borderRadius: "5px",
    },
    "&:hover::after": {
        opacity: 1,
    },
}
