import { Box, TextField, Button, MenuItem, Typography } from "@mui/material";
import { useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import {
    filtroContainerStyles,
    filtroTitleStyles,
    filtroGridStyles,
    filtroItemStyles,
    filtroButtonsStyles,
    filtroButtonPrimaryStyles,
    filtroButtonSecondaryStyles,
} from "../styles/filtroStyles";

interface FiltroFechasProps {
    onFiltrar: (filtros: {
        desde: string | null;
        hasta: string | null;
        tipo: string | null;
        contraproducencia: string | null;
        orden_trabajo: string | null;
    }) => void;
}

/**
 * Componente de filtro para búsqueda de actuaciones.
 * 
 * Filtros disponibles:
 * - Rango de fechas (desde/hasta)
 * - Tipo de actuación
 * - Contraproducencia
 * - Orden de Trabajo
 */
const FiltroFechas = ({ onFiltrar }: FiltroFechasProps) => {
    const [desde, setDesde] = useState<string>("");
    const [hasta, setHasta] = useState<string>("");
    const [tipo, setTipo] = useState<string>("");
    const [contraproducencia, setContraproducencia] = useState<string>("");
    const [ordenTrabajo, setOrdenTrabajo] = useState<string>("");

    const handleFiltrar = () => {
        onFiltrar({
            desde: desde || null,
            hasta: hasta || null,
            tipo: tipo || null,
            contraproducencia: contraproducencia || null,
            orden_trabajo: ordenTrabajo || null,
        });
    };

    const handleLimpiar = () => {
        setDesde("");
        setHasta("");
        setTipo("");
        setContraproducencia("");
        setOrdenTrabajo("");
        // NO llamar a onFiltrar - solo limpiar inputs
    };

    return (
        <Box sx={filtroContainerStyles}>
            <Typography sx={filtroTitleStyles}>Filtros de Búsqueda</Typography>

            <Box sx={filtroGridStyles}>
                {/* Fecha Desde */}
                <Box sx={filtroItemStyles}>
                    <TextField
                        fullWidth
                        type="date"
                        label="Desde"
                        value={desde}
                        onChange={(e) => setDesde(e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        variant="outlined"
                    />
                </Box>

                {/* Fecha Hasta */}
                <Box sx={filtroItemStyles}>
                    <TextField
                        fullWidth
                        type="date"
                        label="Hasta"
                        value={hasta}
                        onChange={(e) => setHasta(e.target.value)}
                        InputLabelProps={{ shrink: true }}
                        variant="outlined"
                    />
                </Box>

                {/* Orden de Trabajo */}
                <Box sx={filtroItemStyles}>
                    <TextField
                        fullWidth
                        label="Orden de Trabajo"
                        value={ordenTrabajo}
                        onChange={(e) => setOrdenTrabajo(e.target.value)}
                        placeholder="123"
                        variant="outlined"
                    />
                </Box>

                {/* Tipo de Actuación */}
                <Box sx={filtroItemStyles}>
                    <TextField
                        fullWidth
                        select
                        label="Tipo de Actuación"
                        value={tipo}
                        onChange={(e) => setTipo(e.target.value)}
                        variant="outlined"
                    >
                        <MenuItem value="">Todos</MenuItem>
                        <MenuItem value="INSPECCION">Inspección</MenuItem>
                        <MenuItem value="REINSPECCION">Reinspección</MenuItem>
                        <MenuItem value="RATIFICACION DE CLAUSURA">Ratificación de Clausura</MenuItem>
                        <MenuItem value="RATIFICACION DE DECOMISO">Ratificación de Decomiso</MenuItem>
                        <MenuItem value="VERIFICAR E INFORMAR">Verificar e Informar</MenuItem>
                        <MenuItem value="TRANSPORTE">Transporte</MenuItem>
                    </TextField>
                </Box>

                {/* Contraproducencia */}
                <Box sx={filtroItemStyles}>
                    <TextField
                        fullWidth
                        select
                        label="Contraproducencia"
                        value={contraproducencia}
                        onChange={(e) => setContraproducencia(e.target.value)}
                        variant="outlined"
                    >
                        <MenuItem value="">Todas</MenuItem>
                        <MenuItem value="LOCAL CERRADO">Local Cerrado</MenuItem>
                        <MenuItem value="NO EXISTE/NO ES EL RUBRO">No Existe/No es el Rubro</MenuItem>
                        <MenuItem value="CLIMA">Clima</MenuItem>
                        <MenuItem value="ZONA ROJA">Zona Roja</MenuItem>
                        <MenuItem value="OTROS">Otros</MenuItem>
                    </TextField>
                </Box>
            </Box>

            <Box sx={filtroButtonsStyles}>
                <Button
                    onClick={handleLimpiar}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                >
                    Limpiar
                </Button>

                <Button
                    onClick={handleFiltrar}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                    variant="contained"
                >
                    Filtrar
                </Button>
            </Box>
        </Box>
    );
};

export default FiltroFechas;
