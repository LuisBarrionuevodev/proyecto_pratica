export const InputCambiarInfoStyle = {
    position: "relative",
    backgroundColor: "#D9D9D9",
    width: {sm:"450px"},
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
}

export const ButtonGuardarInfoStyle = {
    backgroundColor: "#0166FF",
    color: "white",
    height: "40px",
    width: {sm:"440px"},
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