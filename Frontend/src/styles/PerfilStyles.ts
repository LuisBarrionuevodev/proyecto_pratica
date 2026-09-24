export const BoxPerfilStyle = {
    background:
        "linear-gradient(180deg, #3a3d44 0%, #2B2E34 50%, #1A1C20 100%)",
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

export const inputDarkStyle = {
    width: "100%",
    "& .MuiInputBase-input": {
        fontFamily: '"Tactic Sans", sans-serif',
        fontWeight: 500,
        color: "#FFFFFF",
        fontSize: "14px",
    },
    "& .MuiOutlinedInput-root": {
        backgroundColor: "#2B2E34",
        borderRadius: "8px",
        "& fieldset": {
            borderColor: "#3a3d44",
        },
        "&:hover fieldset": {
            borderColor: "#535353",
        },
        "&.Mui-focused fieldset": {
            borderColor: "#0166FF",
            borderWidth: "2px",
        },
    },
    "& .MuiInputBase-input::placeholder": {
        color: "rgba(255, 255, 255, 0.5)",
        opacity: 1,
    },
};

export const EditNombreStyle = {

    width: "100%",
    input: {
        fontFamily: '"Tactic Sans", sans-serif',
        fontWeight: 800,
        fontSize: {
            xs: "28px",
            sm: "42px",
            md: "56px",
            lg: "64px",
        },
        color: "#fff",
    }
}

export const InfoPerfilStyle = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "12px",
    color: "#fff",
    textTransform: "uppercase",
}

export const AvatarPerfilStye = {
    width: { xs: 100, sm: 140, md: 180 },
    height: { xs: 100, sm: 140, md: 180 },
    border: "4px solid #1A1C20",
    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.5)",
    cursor: "pointer",
    transition: "0.2s",
    "&:hover": {
        transform: "scale(1.03)",
    },
}

export const NombrePerfilStyle = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 800,
    fontSize: {
        xs: "20px",
        sm: "40px",
        md: "56px",
        lg: "64px",
    },
    color: "#FFFFFF",
    lineHeight: 1,
    textAlign:""
}

export const RolPerfilStyle = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: {xs:"10px",sm:"14px"},
    color: "rgba(255,255,255,0.7)",
}

export const buttonStyle = {
    backgroundColor: "#0166FF",
    color: "#FFFFFF",
    fontFamily: '"Tactic Sans", sans-serif',
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