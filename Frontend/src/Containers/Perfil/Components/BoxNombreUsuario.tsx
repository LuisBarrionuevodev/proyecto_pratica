import { Box, Typography } from "@mui/material";
import FotoAvatar from "../../../assets/FotoAvatar.png"

const BoxNombreUsuario = () => {

    // const nombreUsuario = localStorage.getItem("Nombre de Usuario")

    return (
        <Box sx={{ bgcolor: "#1955CD", height: { xs: "220px", sm: "230px", md: "260px", lg: "270px", xl:"310px" }, boxShadow: "0px 4px 4px black" }}>

            <Box display={"flex"} justifyContent={"center"} >
                <Typography sx={{ color: "white", fontSize: {xs:"30px",sm:"50px"}, mt: "6%" }}>
                    Luis Barrionuevo
                    {/* {nombreUsuario} */}
                </Typography>
            </Box>

            <Box sx={{ display: "flex", justifyContent: { xs: "center", sm: "center", md: "end" }, mt: "5vh", mr: { xs: "0px", md: "50px" } }}>
                <Box
                    component={"img"}
                    src={FotoAvatar}
                    sx={{ borderRadius: "80px", width: "130px", border: "2px solid black" }}>
                </Box>
            </Box>

        </Box>
    )
}

export default BoxNombreUsuario;