import { FONT_FAMILY_UI } from "../theme/typography";
import { darkColors } from "../theme/colors";

const auth = darkColors.auth;
const shadow = darkColors.shadow;

export const recuperarCardShellSx = {
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "center",
  width: "100%",
  maxWidth: { xs: "100%", sm: 520 },
  borderRadius: "10px",
  background: auth.card,
  border: `1px solid ${auth.cardBorder}`,
  boxShadow: shadow.authCard,
  gap: { xs: 2, sm: 2.5 },
  p: { xs: 2.5, sm: 3 },
  boxSizing: "border-box",
  minWidth: 0,
};

export const InputRecuperarStyles = {
  position: "relative",
  backgroundColor: auth.input,
  width: "100%",
  maxWidth: { xs: "100%", sm: 350 },
  alignSelf: "center",
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

  "& .MuiOutlinedInput-root": {
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

    "&.Mui-focused": {
      "&::after": {
        opacity: 1,
      },
    },
  },
};

/** @deprecated Usar `recuperarCardShellSx` vía `RecuperarCuentaStepShell`. */
export const BoxRecuperarContenidoStyles = recuperarCardShellSx;

/** @deprecated Usar `recuperarCardShellSx` vía `RecuperarCuentaStepShell`. */
export const BoxNuevaContraseñaStyles = recuperarCardShellSx;

export const ErrorTextRecuperarStyles = {
  textAlign: "center",
  color: "red",
  fontSize: 15,
  fontWeight: 500,
  fontFamily: FONT_FAMILY_UI,
  width: "100%",
};

export const ButtonRecuperarStyles = {
  backgroundColor: auth.button,
  color: "white",
  fontFamily: FONT_FAMILY_UI,
  minHeight: { xs: 44, sm: 40 },
  height: { xs: 44, sm: 40 },
  width: "100%",
  maxWidth: { xs: "100%", sm: 350 },
  alignSelf: "center",
  borderRadius: "5px",
  position: "relative",
  textTransform: "none",
  fontSize: { xs: "16px", sm: "1rem" },
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
};
