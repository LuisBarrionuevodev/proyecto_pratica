export const LoginBoxGlobalStyle = {
    display: "flex",
    marginTop: "50px",
    justifyContent: "center",
    alignContent: "center"
}
export const LoginBoxStyle = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    width: "450px",
    height: "500px",
    borderRadius: "10px",
    background: "#FFFFFF",
    border: "1px solid #353535",
    boxShadow: "10px 10px 0px #000000",
    gap: "20px"
}

export const LoginLogoStyle = {
    display: "flex", 
    justifySelf: "center", 
    flexDirection: "column"
}

export const LoginBoxInputStyles = {
    display: "flex",
    alignItems: "center",
    justifyItems: "center",
    flexDirection: "column",
    gap: "20px",

}
export const InputStyles = {
    position: "relative",
    backgroundColor: "#D9D9D9",
    width: "350px",
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


export const ButtonStyle = {
    backgroundColor: "#0166FF",
    width: "350px",
    height: "25px",
    fontFamily: "Tactic Sans",
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
        boxShadow: "6px 6px 3px #000000",
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
