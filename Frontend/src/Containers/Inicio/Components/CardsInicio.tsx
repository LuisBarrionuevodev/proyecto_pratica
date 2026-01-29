import { CardStyle, StyleTextCard, StyleTextCardSecondary } from "../../../styles/InicioStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { JSX } from "react";
import { Typography, Grid, Box } from "@mui/material";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import NoteAddIcon from "@mui/icons-material/NoteAdd";
import DashboardIcon from "@mui/icons-material/Dashboard";
import BarChartIcon from "@mui/icons-material/BarChart";
import MapIcon from "@mui/icons-material/Map";
import CreateNewFolderIcon from "@mui/icons-material/CreateNewFolder";
import ListAltIcon from "@mui/icons-material/ListAlt";
import BadgeIcon from "@mui/icons-material/Badge";
import SettingsIcon from "@mui/icons-material/Settings";
import { Link } from "react-router-dom";

const CardsInicio = (): JSX.Element => {
    const iconStyles = { fontSize: "36px", color: GLASS_COLORS.primary };

    // Cards en grid de 4 columnas (como Early Bird)
    return (
        <Grid container padding={{ xs: 2, sm: 3, md: 4 }} spacing={2}>
            {/* Fila 1: 4 cards */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/cargarPersonasCapacitadas" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <PersonAddIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Agregar Persona</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Personas capacitadas para inspecciones
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/cargarActuacion" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <CreateNewFolderIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Cargar Actuación</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Carga actuaciones en el sistema
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/cargarRelevamiento" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <NoteAddIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Cargar Relevamiento</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Carga relevamientos en el sistema
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/actuaciones" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <DashboardIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Gestionar Expedientes</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza, edita y elimina expedientes
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            {/* Fila 2: 4 cards */}
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/relevamientos" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <ListAltIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Gestionar Relevamientos</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza, edita y elimina relevamientos
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/gestionPersonasBpm" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <BadgeIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Personas BPM</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Gestiona personas con BPM
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/dashboard" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <BarChartIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Dashboard</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Estadísticas de expedientes
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/mapa" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <MapIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Mapa</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Visualiza distritos y locales
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid>

            {/* Fila 3: Última card centrada con "Configuración" si se desea, o comentar */}
            {/* <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Link to="/gestionSistema" style={{ textDecoration: "none" }}>
                    <Box sx={CardStyle}>
                        <SettingsIcon sx={iconStyles} />
                        <Box>
                            <Typography sx={StyleTextCard}>Configuración</Typography>
                            <Typography sx={StyleTextCardSecondary}>
                                Personaliza el sistema
                            </Typography>
                        </Box>
                    </Box>
                </Link>
            </Grid> */}
        </Grid>
    );
};

export default CardsInicio;