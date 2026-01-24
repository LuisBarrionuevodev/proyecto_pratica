export const InputRecuperarStyles = {
    position: "relative",
    backgroundColor: "#D9D9D9",
    width: "450px",
    fontSize: "22px",
    borderRadius: "10px",
    "& .MuiInputBase-input": {
        fontFamily: "Tactic Sans",
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
};

export const BoxRecuperarContenidoStyles = {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "600px",
    height: "300px",
    borderRadius: "10px",
    background: "#FFFFFF",
    border: "1px solid #353535",
    boxShadow: "10px 10px 0px #000000",
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
    background: "#FFFFFF",
    border: "1px solid #353535",
    boxShadow: "10px 10px 0px #000000",
    gap: 3,
    p: 2,
    mt: "40px",
}

export const ErrorTextRecuperarStyles = {
    color: "red", 
    fontSize: 14, 
    fontWeight: 500
}

export const ButtonRecuperarStyles = {
    backgroundColor: "#0166FF",
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
        boxShadow: "6px 6px 3px #000000",
        opacity: 0,
        transition: "opacity 0.3s",
        borderRadius: "5px",
    },
    "&:hover::after": {
        opacity: 1,
    },
}
