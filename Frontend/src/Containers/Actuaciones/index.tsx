import type { JSX } from "react";
import TablaActuaciones from "./Components/TableActuaciones";
import FiltroFechas from "./Components/FiltroFechas";
import { ThemeProvider, Box, Alert, Typography, CircularProgress } from "@mui/material";
import { darkTheme } from "../../configs/theme";
import { useActuacionesFiltradas } from "./hooks/useActuacionesFiltradas";
import {
    wrapperStyles,
    titleStyles,
    metaInfoStyles,
    metaItemStyles,
    errorAlertStyles,
} from "./styles/filtroStyles";

/**
 * Vista principal de Actuaciones.
 * 
 * Orquesta:
 * - Estado de filtros (desde, hasta, tipo, contraproducencia, orden_trabajo)
 * - Hook de datos (useActuacionesFiltradas)
 * - Componentes modulares (FiltroFechas, TablaActuaciones)
 * 
 * Flujo:
 * 1. Al entrar: solo muestra filtro
 * 2. Al filtrar: muestra filtro + tabla + metadata
 */
const Actuaciones = (): JSX.Element => {
    const { actuaciones, meta, loading, error, hasSearched, buscar } = useActuacionesFiltradas();

    const handleFiltrar = (filtros: {
        desde: string | null;
        hasta: string | null;
        tipo: string | null;
        contraproducencia: string | null;
        orden_trabajo: string | null;
    }) => {
        // Llamar a buscar con los filtros (todos son opcionales)
        buscar(filtros);
    };

    return (
        <ThemeProvider theme={darkTheme}>
                <Box sx={wrapperStyles}>
                    {/* Título */}
                    <Typography sx={titleStyles}>Actuaciones</Typography>

                    {/* Componente de filtro modular (siempre visible) */}
                    <FiltroFechas onFiltrar={handleFiltrar} />

                    {/* Mostrar error si existe */}
                    {error && hasSearched && (
                        <Alert severity="error" sx={errorAlertStyles} onClose={() => {}}>
                            <strong>Error:</strong> {error}
                        </Alert>
                    )}

                    {/* Loading state */}
                    {loading && (
                        <Box sx={{ display: "flex", justifyContent: "center", padding: "40px" }}>
                            <CircularProgress sx={{ color: "#0166FF" }} />
                        </Box>
                    )}

                    {/* Mostrar metadata solo si ya se buscó y hay datos */}
                    {hasSearched && !loading && meta && (
                        <Box sx={metaInfoStyles}>
                            <Typography sx={metaItemStyles}>
                                <strong>Total:</strong> {meta.total}
                            </Typography>
                            <Typography sx={metaItemStyles}>
                                <strong>Mostrando:</strong> {actuaciones.length} de {meta.total}
                            </Typography>
                            <Typography sx={metaItemStyles}>
                                <strong>Página:</strong> {meta.page}
                            </Typography>
                            {meta.desde && meta.hasta && (
                                <Typography sx={metaItemStyles}>
                                    <strong>Rango:</strong> {meta.desde} - {meta.hasta}
                                </Typography>
                            )}
                            {meta.tipo && (
                                <Typography sx={metaItemStyles}>
                                    <strong>Tipo:</strong> {meta.tipo}
                                </Typography>
                            )}
                            {meta.contraproducencia && (
                                <Typography sx={metaItemStyles}>
                                    <strong>Contraproducencia:</strong> {meta.contraproducencia}
                                </Typography>
                            )}
                            {meta.orden_trabajo && (
                                <Typography sx={metaItemStyles}>
                                    <strong>OT:</strong> {meta.orden_trabajo}
                                </Typography>
                            )}
                        </Box>
                    )}

                    {/* Tabla solo visible después de buscar */}
                    {hasSearched && !loading && (
                        <TablaActuaciones 
                            data={actuaciones}
                            loading={loading}
                            onRefresh={() => handleFiltrar({
                                desde: meta?.desde || null,
                                hasta: meta?.hasta || null,
                                tipo: meta?.tipo || null,
                                contraproducencia: meta?.contraproducencia || null,
                                orden_trabajo: meta?.orden_trabajo || null,
                            })}
                        />
                    )}
                </Box>
            </ThemeProvider>
    );
};

export default Actuaciones;
