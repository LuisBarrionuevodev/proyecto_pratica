import BackgroundInicio from "../assets/BackgroundInicio.png"

export const BoxInicio = {
    display: "flex",
    backgroundImage: `url(${BackgroundInicio})`,
    backgroundSize: "cover",
    backgroundPosition: "end",
    gap: 1,
    alignItems:"center",
    justifyContent:"center",
    paddingTop: "15px",
    paddingBottom: "15px",
    height: "350px"
}

export const BoxTitulo = {
    marginLeft: "10%",
    width: { xs: "300px", sm: "500px", md: "600px" },
}

export const TitleStyle = {
    color: "white",
    textShadow: '8px 8px 0px rgba(0, 0, 0, 1)',
    fontFamily: "Tactic Sans",
    fontWeight: 800,
    fontSize: { xs: "38px", sm: "60px", md: "65px", xl: "70px" }
}

export const BoxInputInicio = {
    justifyContent: { md: "space-evenly" },
    alignContent: "center",
}

export const ButtonStylesInicio = {
    width: { xs: "350px", sm: "500px", md: "500px" },
    height: "60px",
    borderRadius: "16px",
    backgroundColor: "white",
    fontFamily: "tactic sans",
    fontWeight: 600,
    fontSize: { xs: "20px", sm: "25px", md: "25px" },
    color: "#E6E6E6",
    WebkitTextStroke: '1px black',
    textShadow: "2px 2px 0 #000000",
    textTransform: 'none',
    transition: "box-shadow 0.4s ease, transform 0.4s ease",
    '&:hover': {
        boxShadow: { xs: "6px 4px 0px #000000", sm: "8px 6px 0px #000000", md: " 8px 6px 0px #000000" },
        transform: "scale(1.05)"
    }
}

export const LogoSumaStyle = {
    display: "flex",
    position: "absolute",
    width: { xs: "30px", sm: "40px", md: "40px" },
    marginRight: { xs: "300px", sm: "440px", md: "440px" },
    borderRadius: "12px",
    border: "3px solid black"
}


// Estilos de CARDS

export const CardStyle = {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    height: "150px",
    backgroundColor: "#DADADA",
    borderRadius: "12px",
    gap: 1,
    transition: "box-shadow 0.4s ease, transform 0.4s ease",
    "&:hover": {
        boxShadow: " 0px 0.5px 10px #000000",
        transform: "scale(1.05)"
    },
}

export const StyleBoxTextCard = {
    textAlign: "center",
    marginTop: "20px"
}

export const StyleTextCard = {
    color: "#000000",
    fontFamily: "Tactic Sans",
    fontWeight: 600,
    fontSize: "20px",
}

export const StyleTextCardSecondary = {
    color: "#9c9c9c",
    fontFamily: "Tactic Sans",
    fontWeight: 400,
    fontSize: "15px",
}








