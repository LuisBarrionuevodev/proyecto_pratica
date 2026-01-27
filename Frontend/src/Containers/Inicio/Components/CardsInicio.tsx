import { CardStyle, StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles"
import type { JSX } from "react";
import { Typography, Grid } from '@mui/material';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import NoteAddIcon from '@mui/icons-material/NoteAdd';
import DashboardIcon from "@mui/icons-material/Dashboard";
import BarChartIcon from "@mui/icons-material/BarChart";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from '@mui/icons-material/CreateNewFolder';
import ListAltIcon from '@mui/icons-material/ListAlt';
import BadgeIcon from '@mui/icons-material/Badge';
import SettingsIcon from '@mui/icons-material/Settings';
import { Link } from "react-router-dom";

const CardsInicio = (): JSX.Element => {

    return (
        <Grid container marginTop={{lg:"10px",xl:"60px"}} padding={5} spacing={4} >
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/cargarPersonasCapacitadas" >

                    <Grid sx={CardStyle}>
                        <PersonAddIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Agregar Persona Capacitada
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Agrega personas capacitadas para las inspecciones
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/cargarActuacion">

                    <Grid sx={CardStyle}>
                        <CreateNewFolderIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Cargar Actuacion
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Carga Actuaciones en el sistema
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/cargarRelevamiento">

                    <Grid sx={CardStyle}>
                        <NoteAddIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Cargar Relevamiento
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Carga Relevamientos en el sistema
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/actuaciones">

                    <Grid sx={CardStyle}>
                        <DashboardIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Gestionar Inspecciones
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza, Edita y Elimina Expedientes
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/relevamientos">

                    <Grid sx={CardStyle}>
                        <ListAltIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Gestionar Relevamientos
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza, Edita y Elimina Relevamientos
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/informe">

                    <Grid sx={CardStyle}>
                        <BadgeIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Gestionar Permisos
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Administra permisos en el sistema
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/dashboard">

                    <Grid sx={CardStyle}>
                        <BarChartIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Dashboard
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza estadisticas de expedientes
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/mapa">

                    <Grid sx={CardStyle}>
                        <MapIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Mapa
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza distritos y locales
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
                <Link to="/configuracion">

                    <Grid sx={CardStyle}>
                        <SettingsIcon sx={{ fontSize: "50px", color: "#0166FF" }} />
                        <Grid display={"flex"} flexDirection={"column"}>
                            <Typography sx={StyleTextCard}>
                                Configuracion
                            </Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Personaliza tus configuraciones
                            </Typography>
                        </Grid>
                    </Grid>

                </Link>
            </Grid>

        </Grid>
    );

};

export default CardsInicio;