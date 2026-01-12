import { CardStyle, StyleBoxTextCard, StyleTextCard } from "../../../styles/InicioStyles"
import type { JSX } from "react";
import { Typography, Grid, Box } from '@mui/material';
import GestionarActuaciones from "../assets-inicio/GestionarActuaciones.svg"
import VerDashboardLogo from "../assets-inicio/VerDashboardLogo.svg"
import VerMapaLogo from "../assets-inicio/VerMapaLogo.svg"
import VerInformeLogo from "../assets-inicio/VerInformeLogo.svg"
import { Link } from "react-router-dom";

const CardsInicio = (): JSX.Element => {

    return (
        <Grid container marginTop={"15px"} padding={5} spacing={8} >
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 3 }}>
                <Link to="/actuaciones">

                    <Grid sx={CardStyle}>
                        <Box component="img" src={GestionarActuaciones} alt="IMG-ACTUACIONES" />
                    </Grid>
                    
                    <Grid sx={StyleBoxTextCard}>
                        <Typography sx={StyleTextCard}>
                            Gestionar Expedientes
                        </Typography>
                    </Grid>

                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 3 }}>
                <Link to="/dashboard">

                    <Grid sx={CardStyle}>
                        <Box component="img" src={VerDashboardLogo} alt="IMG-DASHBOARD" />
                    </Grid>

                    <Grid sx={StyleBoxTextCard}>
                        <Typography sx={StyleTextCard}>
                            Ver Dashboard
                        </Typography>
                    </Grid>

                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 3 }}>
                <Link to="/mapa">

                    <Grid sx={CardStyle}>
                        <Box component="img" src={VerMapaLogo} alt="IMG-MAPA" />
                    </Grid>

                    <Grid sx={StyleBoxTextCard}>
                        <Typography sx={StyleTextCard}>
                            Ver Mapa
                        </Typography>
                    </Grid>

                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 3 }}>
                <Link to="/informe">

                    <Grid sx={CardStyle}>
                        <Box component="img" src={VerInformeLogo} alt="IMG-INFORME" />
                    </Grid>

                    <Grid sx={StyleBoxTextCard}>
                        <Typography sx={StyleTextCard}>
                            Ver Informe Mensual
                        </Typography>
                    </Grid>

                </Link>
            </Grid>

        </Grid>
    );

};

export default CardsInicio;