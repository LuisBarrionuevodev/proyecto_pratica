import { Box, TextField } from "@mui/material";
import type { JSX } from "react";
import { BoxInicio} from "../../../styles/InicioStyles";

const CargaDeDatos = (): JSX.Element => {

    return (
        <Box sx={BoxInicio}>

            <Box sx={{}}>
                <TextField placeholder="Actuaciones, Relevamientos, Inspectores" sx={{
                    width: { sm: "550px", md: "800px", lg: "1000px" }, bgcolor: "white", borderRadius: "40px",
                    "& .MuiInputBase-input": {
                        fontFamily: "Tactic Sans",
                        fontWeight: 500,
                        zIndex: 1,
                        
                    },

                    '& .MuiOutlinedInput-root': {
                        borderRadius: "40px",
                        "&::after": {
                            content: '""',
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "100%",
                            height: "100%",
                            boxShadow: " 0px 4px 8px #000000",
                            borderRadius: "40px",
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
                } />
            </Box>

            {/* Codigo Viejo */}

            {/* <Box sx={BoxTitulo}>
                <Typography sx={TitleStyle}>
                    Gestion de expedientes
                </Typography>
            </Box> */}

            {/* <Grid container
                direction={{ xs: "column", md: "row" }}
                rowSpacing={2}
                sx={BoxInputInicio}>
                <Grid>
                    <Link to="/cargarActuacion">
                        <Button sx={ButtonStylesInicio}>

                            <Box component={"img"}
                                src={LogoSuma}
                                sx={LogoSumaStyle} />

                            Cargar Actuacion

                        </Button>
                    </Link>
                </Grid>

                <Grid>
                    <Link to="/cargarRelevamiento">
                        <Button sx={ButtonStylesInicio}>

                            <Box component={"img"}
                                src={LogoSuma}
                                sx={LogoSumaStyle} />

                            Cargar Relevamiento
                        </Button>
                    </Link>
                </Grid>
            </Grid> */}
        </Box>
    )

}

export default CargaDeDatos;