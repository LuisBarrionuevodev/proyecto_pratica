export const BoxInicio = {
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#2B2E34",
    boxShadow: "0px 4px 4 px #000000",
    gap: 5,
    paddingTop: "15px",
    paddingBottom: "15px",
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
        boxShadow: {xs:"6px 4px 0px #000000", sm: "8px 6px 0px #000000" ,md:" 8px 6px 0px #000000"},
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
    height: "250px",
    backgroundColor: "#DADADA",
    border: "4px solid black",
    borderRadius: "12px",
    transition: "box-shadow 0.4s ease, transform 0.4s ease",
    "&:hover": {
        boxShadow: " 8px 6px 0px #000000",
        transform: "scale(1.05)"
    },
}

export const StyleBoxTextCard = {
    textAlign: "center",
    marginTop: "20px"
}

export const StyleTextCard = {
    WebkitTextStroke: '1px black',
    textShadow: "2px 2px 0 #000000",
    color: "#E6E6E6",
    fontFamily: "Tactic Sans",
    fontWeight: 600,
    fontSize: "20px",
}








