import { Box, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

import { fetchTiposActuacion, fetchContraproducencias } from "../../../api/gridApi";
import { AppButton, AppSelect, AppTextField } from "../../../ui";

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
    /** Valores iniciales (p. ej. mes en curso al cargar la vista). */
    initialDesde?: string;
    initialHasta?: string;
    /** Tras limpiar campos, vacía grilla/meta en el padre (evita meta obsoleta). */
    onLimpiarLista?: () => void;
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
const FiltroFechas = ({
    onFiltrar,
    initialDesde = "",
    initialHasta = "",
    onLimpiarLista,
}: FiltroFechasProps) => {
    const [desde, setDesde] = useState<string>(initialDesde);
    const [hasta, setHasta] = useState<string>(initialHasta);
    const [tipo, setTipo] = useState<string>("");
    const [contraproducencia, setContraproducencia] = useState<string>("");
    const [ordenTrabajo, setOrdenTrabajo] = useState<string>("");
    const [catalogTipos, setCatalogTipos] = useState<string[]>([]);
    const [catalogContras, setCatalogContras] = useState<string[]>([]);

    useEffect(() => {
        const loadCatalogs = async () => {
            try {
                const [tipos, contras] = await Promise.all([
                    fetchTiposActuacion(),
                    fetchContraproducencias(),
                ]);
                setCatalogTipos([...new Set(tipos.items.map((t: any) => t.nombre))]);
                setCatalogContras([...new Set(contras.items.map((c: any) => c.nombre))]);
            } catch (error) {
                console.error("Error cargando catálogos de filtros:", error);
            }
        };
        loadCatalogs();
    }, []);

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
        setDesde(initialDesde);
        setHasta(initialHasta);
        setTipo("");
        setContraproducencia("");
        setOrdenTrabajo("");
        onLimpiarLista?.();
    };

    const tipoOptions = [
        { value: "", label: "Todos" },
        ...catalogTipos.map((t) => ({ value: t, label: t })),
    ];
    const contraproducenciaOptions = [
        { value: "", label: "Todas" },
        ...catalogContras.map((c) => ({ value: c, label: c })),
    ];

    return (
        <Box sx={filtroContainerStyles}>
            <Typography sx={filtroTitleStyles}>Filtros de búsqueda</Typography>
            <Typography sx={{ color: "rgba(255,255,255,0.75)", fontSize: "0.85rem", mb: 1, lineHeight: 1.45 }}>
                Vista documental: incluye actuaciones aunque tengan expediente u oficio pendiente. Sin fechas = todas
                las fechas. Si hay más resultados que la página, usá el pie de la tabla o filtrá por OT.
            </Typography>

            <Box sx={filtroGridStyles}>
                {/* Fecha Desde */}
                <Box sx={filtroItemStyles}>
                    <AppTextField
                        appearance="dense"
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
                    <AppTextField
                        appearance="dense"
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
                    <AppTextField
                        appearance="dense"
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
                    <AppSelect
                        appearance="dense"
                        fullWidth
                        label="Tipo de Actuación"
                        value={tipo}
                        onChange={(e) => setTipo(e.target.value)}
                        variant="outlined"
                        options={tipoOptions}
                    />
                </Box>

                {/* Contraproducencia */}
                <Box sx={filtroItemStyles}>
                    <AppSelect
                        appearance="dense"
                        fullWidth
                        label="Contraproducencia"
                        value={contraproducencia}
                        onChange={(e) => setContraproducencia(e.target.value)}
                        variant="outlined"
                        options={contraproducenciaOptions}
                    />
                </Box>
            </Box>

            <Box sx={filtroButtonsStyles}>
                <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    onClick={handleLimpiar}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                >
                    Limpiar
                </AppButton>

                <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={handleFiltrar}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                >
                    Filtrar
                </AppButton>
            </Box>
        </Box>
    );
};

export default FiltroFechas;
