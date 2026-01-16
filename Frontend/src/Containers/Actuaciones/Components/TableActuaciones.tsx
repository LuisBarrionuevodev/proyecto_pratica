/**
 * Tabla de Gestión de Actuaciones
 * Estilo Neo-Brutalista oscuro (coherente con CargarActuaciones)
 * Librería: Material React Table
 */

import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { IActuacion } from "../../../types/actuaciones";
import { useGestionActuaciones } from "../../../hooks/useGestionActuaciones";
import { deleteActuacion, updateActuacion } from "../../../api/actuacionesApi";
import { TablaExportButtons } from "./TableButtons";

// Estilos Neo-Brutalistas
import {
    containerStyles,
    wrapperStyles,
    titleStyles,
    loadingStyles,
    DARK_TABLE_CONFIG,
    COLORS,
    legendStyles,
    legendTitleStyles,
    legendTextStyles,
    legendIconStyles,
} from "../styles/actuacionesTableStyles";

// Iconos para la leyenda
import SearchIcon from "@mui/icons-material/Search";
import FilterListIcon from "@mui/icons-material/FilterList";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import EditIcon from "@mui/icons-material/Edit";
import WarningIcon from "@mui/icons-material/Warning";

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

const TablaActuaciones = () => {
    const { actuaciones, setActuaciones, loading } = useGestionActuaciones();
    const [data, setData] = useState<IActuacion[]>([]);
    const [validationErrors] = useState<Record<number, Record<string, string>>>({});

    useEffect(() => {
        setData(actuaciones ?? []);
    }, [actuaciones]);

    // =========================================================================
    // HANDLERS
    // =========================================================================

    const handleDeleteRow = useCallback(async (id: number) => {
        if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;
        const prev = data;
        setData(prev => prev.filter(item => item.id !== id));
        setActuaciones(prev => prev.filter(item => item.id !== id));
        try {
            await deleteActuacion(id);
        } catch (error) {
            console.error("Error al eliminar:", error);
            alert("No se pudo eliminar el registro. Se restaurará la lista.");
            setData(prev);
            setActuaciones(prev);
        }
    }, [data, setActuaciones]);

    const handleEditCell = useCallback(
        async (id: number, key: keyof IActuacion, value: any) => {
            let updatedRow: IActuacion | undefined;
            setData((prev) => {
                const idx = prev.findIndex((r) => r.id === id);
                if (idx === -1) return prev;
                updatedRow = { ...prev[idx], [key]: value };
                const newData = [...prev];
                newData[idx] = updatedRow!;
                return newData;
            });

            if (!updatedRow) return;

            const payload: IActuacion = { ...updatedRow };

            if (!payload.rubro_nombre || !payload.calle || !payload.numero) {
                alert("Algunos campos no son válidos. Corrigelos antes de guardar.");
                return;
            }

            try {
                await updateActuacion(id, payload);
            } catch (error) {
                console.error("Error al actualizar:", error);
                alert("No se pudo actualizar el registro.");
            }
        },
        []
    );

    // =========================================================================
    // DEFINICIÓN DE COLUMNAS
    // =========================================================================

    const columns = useMemo<MRT_ColumnDef<IActuacion>[]>(() => [
        {
            accessorKey: "id",
            header: "ID",
            enableHiding: true,
            enableEditing: false,
            enableClickToCopy: true,
            size: 60,
        },
        {
            accessorKey: "orden_trabajo_numero",
            header: "OT",
            size: 80,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.orden_trabajo_numero,
                helperText: validationErrors[row.original.id]?.orden_trabajo_numero,
                onBlur: (e) => handleEditCell(row.original.id, "orden_trabajo_numero", e.target.value),
            })
        },
        {
            accessorKey: "fecha_actuacion",
            header: "Fecha",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.fecha_actuacion,
                helperText: validationErrors[row.original.id]?.fecha_actuacion,
                onBlur: (e) => handleEditCell(row.original.id, "fecha_actuacion", e.target.value),
            })
        },
        {
            accessorKey: "rubro_nombre",
            header: "Rubro",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.rubro,
                helperText: validationErrors[row.original.id]?.rubro,
                onBlur: (e) => handleEditCell(row.original.id, "rubro_nombre", e.target.value),
            })
        },
        {
            accessorKey: "inspector1",
            header: "Inspector 1",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.inspector1,
                helperText: validationErrors[row.original.id]?.inspector1,
                onBlur: (e) => handleEditCell(row.original.id, "inspector1", e.target.value),
            }),
        },
        {
            accessorKey: "inspector2",
            header: "Inspector 2",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.inspector2,
                helperText: validationErrors[row.original.id]?.inspector2,
                onBlur: (e) => handleEditCell(row.original.id, "inspector2", e.target.value),
            }),
        },
        {
            accessorKey: "inspector3",
            header: "Inspector 3",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.inspector3,
                helperText: validationErrors[row.original.id]?.inspector3,
                onBlur: (e) => handleEditCell(row.original.id, "inspector3", e.target.value),
            }),
        },
        {
            accessorKey: "calle",
            header: "Calle",
            size: 150,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.calle,
                helperText: validationErrors[row.original.id]?.calle,
                onBlur: (e) => handleEditCell(row.original.id, "calle", e.target.value),
            }),
        },
        {
            accessorKey: "numero",
            header: "Número",
            size: 80,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.numero,
                helperText: validationErrors[row.original.id]?.numero,
                onBlur: (e) => handleEditCell(row.original.id, "numero", e.target.value),
            }),
        },
        {
            accessorKey: "tipo_actuacion",
            header: "Tipo",
            size: 130,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.tipo_actuacion,
                helperText: validationErrors[row.original.id]?.tipo_actuacion,
                onBlur: (e) => handleEditCell(row.original.id, "tipo_actuacion", e.target.value),
            }),
        },
        {
            accessorKey: "contraproducencia",
            header: "Contraprod.",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.contraproducencia,
                helperText: validationErrors[row.original.id]?.contraproducencia,
                onBlur: (e) => handleEditCell(row.original.id, "contraproducencia", e.target.value),
            }),
        },
        {
            accessorKey: "doc_tipo_codigo",
            header: "Tipo Doc.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.doc_tipo_codigo,
                helperText: validationErrors[row.original.id]?.doc_tipo_codigo,
                onBlur: (e) => handleEditCell(row.original.id, "doc_tipo_codigo", e.target.value),
            }),
        },
        {
            accessorKey: "doc_nro",
            header: "Nro Doc.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.doc_nro,
                helperText: validationErrors[row.original.id]?.doc_nro,
                onBlur: (e) => handleEditCell(row.original.id, "doc_nro", e.target.value),
            }),
        },
        {
            accessorKey: "contrib_apellido",
            header: "Apellido",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.contrib_apellido,
                helperText: validationErrors[row.original.id]?.contrib_apellido,
                onBlur: (e) => handleEditCell(row.original.id, "contrib_apellido", e.target.value),
            }),
        },
        {
            accessorKey: "contrib_nombre",
            header: "Nombre",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.contrib_nombre,
                helperText: validationErrors[row.original.id]?.contrib_nombre,
                onBlur: (e) => handleEditCell(row.original.id, "contrib_nombre", e.target.value),
            }),
        },
        {
            accessorKey: "acta_inspeccion_num",
            header: "Acta Insp.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.acta_inspeccion_num,
                helperText: validationErrors[row.original.id]?.acta_inspeccion_num,
                onBlur: (e) => handleEditCell(row.original.id, "acta_inspeccion_num", e.target.value),
            }),
        },
        {
            accessorKey: "acta_notificacion_num",
            header: "Acta Notif.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.acta_notificacion_num,
                helperText: validationErrors[row.original.id]?.acta_notificacion_num,
                onBlur: (e) => handleEditCell(row.original.id, "acta_notificacion_num", e.target.value),
            }),
        },
        {
            accessorKey: "notificacion_motivo_1",
            header: "Motivo 1",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.notificacion_motivo_1,
                helperText: validationErrors[row.original.id]?.notificacion_motivo_1,
                onBlur: (e) => handleEditCell(row.original.id, "notificacion_motivo_1", e.target.value),
            }),
        },
        {
            accessorKey: "notificacion_motivo_2",
            header: "Motivo 2",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.notificacion_motivo_2,
                helperText: validationErrors[row.original.id]?.notificacion_motivo_2,
                onBlur: (e) => handleEditCell(row.original.id, "notificacion_motivo_2", e.target.value),
            }),
        },
        {
            accessorKey: "notificacion_motivo_3",
            header: "Motivo 3",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.notificacion_motivo_3,
                helperText: validationErrors[row.original.id]?.notificacion_motivo_3,
                onBlur: (e) => handleEditCell(row.original.id, "notificacion_motivo_3", e.target.value),
            }),
        },
        {
            accessorKey: "acta_comprobacion_num",
            header: "Acta Comp.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.acta_comprobacion_num,
                helperText: validationErrors[row.original.id]?.acta_comprobacion_num,
                onBlur: (e) => handleEditCell(row.original.id, "acta_comprobacion_num", e.target.value),
            }),
        },
        {
            accessorKey: "comprobacion_motivo",
            header: "Motivo Comp.",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.comprobacion_motivo,
                helperText: validationErrors[row.original.id]?.comprobacion_motivo,
                onBlur: (e) => handleEditCell(row.original.id, "comprobacion_motivo", e.target.value),
            }),
        },
        {
            accessorKey: "acta_clausura_num",
            header: "Acta Claus.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.acta_clausura_num,
                helperText: validationErrors[row.original.id]?.acta_clausura_num,
                onBlur: (e) => handleEditCell(row.original.id, "acta_clausura_num", e.target.value),
            }),
        },
        {
            accessorKey: "clausura_motivo",
            header: "Motivo Claus.",
            size: 120,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.clausura_motivo,
                helperText: validationErrors[row.original.id]?.clausura_motivo,
                onBlur: (e) => handleEditCell(row.original.id, "clausura_motivo", e.target.value),
            }),
        },
        {
            accessorKey: "acta_decomiso_num",
            header: "Acta Dec.",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.acta_decomiso_num,
                helperText: validationErrors[row.original.id]?.acta_decomiso_num,
                onBlur: (e) => handleEditCell(row.original.id, "acta_decomiso_num", e.target.value),
            }),
        },
        {
            accessorKey: "decomiso_kilos_total",
            header: "Kilos",
            size: 80,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.decomiso_kilos_total,
                helperText: validationErrors[row.original.id]?.decomiso_kilos_total,
                onBlur: (e) => handleEditCell(row.original.id, "decomiso_kilos_total", e.target.value),
            }),
        },
        {
            accessorKey: "expediente_numero",
            header: "Exp. Nro",
            size: 90,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.expediente_numero,
                helperText: validationErrors[row.original.id]?.expediente_numero,
                onBlur: (e) => handleEditCell(row.original.id, "expediente_numero", e.target.value),
            }),
        },
        {
            accessorKey: "expediente_anio",
            header: "Exp. Año",
            size: 80,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.expediente_anio,
                helperText: validationErrors[row.original.id]?.expediente_anio,
                onBlur: (e) => handleEditCell(row.original.id, "expediente_anio", e.target.value),
            }),
        },
        {
            accessorKey: "oficio_numero",
            header: "Oficio Nro",
            size: 90,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.oficio_numero,
                helperText: validationErrors[row.original.id]?.oficio_numero,
                onBlur: (e) => handleEditCell(row.original.id, "oficio_numero", e.target.value),
            }),
        },
        {
            accessorKey: "oficio_anio",
            header: "Oficio Año",
            size: 80,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.oficio_anio,
                helperText: validationErrors[row.original.id]?.oficio_anio,
                onBlur: (e) => handleEditCell(row.original.id, "oficio_anio", e.target.value),
            }),
        },
        {
            accessorKey: "oficio_causa",
            header: "Causa",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.oficio_causa,
                helperText: validationErrors[row.original.id]?.oficio_causa,
                onBlur: (e) => handleEditCell(row.original.id, "oficio_causa", e.target.value),
            }),
        },
        {
            accessorKey: "notificacion_previa_num",
            header: "Notif. Previa",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.notificacion_previa_num,
                helperText: validationErrors[row.original.id]?.notificacion_previa_num,
                onBlur: (e) => handleEditCell(row.original.id, "notificacion_previa_num", e.target.value),
            }),
        },
        {
            accessorKey: "comprobacion_previa_num",
            header: "Comp. Previa",
            size: 100,
            muiEditTextFieldProps: ({ row }) => ({
                error: !!validationErrors[row.original.id]?.comprobacion_previa_num,
                helperText: validationErrors[row.original.id]?.comprobacion_previa_num,
                onBlur: (e) => handleEditCell(row.original.id, "comprobacion_previa_num", e.target.value),
            }),
        },
    ], [validationErrors, handleEditCell]);

    // =========================================================================
    // CONFIGURACIÓN DE LA TABLA
    // =========================================================================

    const table = useMaterialReactTable({
        ...DARK_TABLE_CONFIG,
        columns,
        data,
        enableRowActions: true,
        initialState: {
            columnVisibility: { id: false },
            density: "compact",
        },
        renderRowActions: ({ row }) => (
            <Box sx={{ display: "flex", gap: "0.5rem" }}>
                <Tooltip title="Eliminar">
                    <IconButton
                        sx={{ 
                            color: COLORS.white,
                            transition: "none",
                            "&:hover": {
                                color: COLORS.primary,
                                backgroundColor: "rgba(1, 102, 255, 0.15)",
                            },
                        }}
                        onClick={() => handleDeleteRow(Number(row.original.id))}
                    >
                        <DeleteIcon />
                    </IconButton>
                </Tooltip>
            </Box>
        ),
        renderTopToolbarCustomActions: ({ table }) => (
            <TablaExportButtons data={data} table={table} />
        ),
    });

    // =========================================================================
    // RENDER
    // =========================================================================

    if (loading) {
        return (
            <Box sx={containerStyles}>
                <Box sx={wrapperStyles}>
                    <Typography sx={loadingStyles}>
                        Cargando actuaciones...
                    </Typography>
                </Box>
            </Box>
        );
    }

    return (
        <Box sx={containerStyles}>
            <Box sx={wrapperStyles}>
                {/* Título Neo-Brutalista */}
                <Typography sx={titleStyles}>
                    Gestión de Actuaciones
                </Typography>

                {/* Tabla Material React Table con tema oscuro */}
                <MaterialReactTable table={table} />

                {/* Leyenda "Cómo usar" */}
                <Box sx={legendStyles}>
                    <Typography sx={legendTitleStyles}>
                        📝 CÓMO USAR ESTA VISTA
                    </Typography>
                    <Typography sx={legendTextStyles} component="div">
                        <Box sx={{ mb: 1 }}>
                            <strong>Esta vista está destinada a la gestión de actuaciones</strong> donde puedes 
                            <span style={legendIconStyles}><EditIcon sx={{ fontSize: 14, mr: 0.5 }} />Editar</span> y 
                            <span style={{ ...legendIconStyles, color: "#FF6B6B" }}><DeleteIcon sx={{ fontSize: 14, mr: 0.5 }} />Eliminar</span> 
                            actuaciones existentes.
                        </Box>
                        
                        <Box sx={{ mb: 1.5 }}>
                            <WarningIcon sx={{ fontSize: 14, color: "#FFD700", verticalAlign: "middle", mr: 0.5 }} />
                            <strong style={{ color: "#FFD700" }}>PRECAUCIÓN:</strong> Las eliminaciones son permanentes. Usa esta función con cuidado.
                        </Box>

                        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, mt: 1 }}>
                            <Box sx={{ minWidth: 200 }}>
                                <strong>🔍 BUSCAR:</strong><br/>
                                <span style={legendIconStyles}><SearchIcon sx={{ fontSize: 14 }} /></span>
                                Busca en todas las actuaciones por cualquier campo.
                            </Box>
                            
                            <Box sx={{ minWidth: 200 }}>
                                <strong>🔽 FILTRAR:</strong><br/>
                                <span style={legendIconStyles}><FilterListIcon sx={{ fontSize: 14 }} /></span>
                                Filtra de manera personalizada por cada columna.
                            </Box>
                            
                            <Box sx={{ minWidth: 200 }}>
                                <strong>👁️ COLUMNAS:</strong><br/>
                                <span style={legendIconStyles}><ViewColumnIcon sx={{ fontSize: 14 }} /></span>
                                Oculta o muestra columnas según necesites.
                            </Box>
                        </Box>

                        <Box sx={{ mt: 1.5 }}>
                            <strong>📥 EXPORTAR:</strong><br/>
                            <span style={legendIconStyles}><FileDownloadIcon sx={{ fontSize: 14, mr: 0.5 }} />Exportar todo</span>
                            Exporta todas las actuaciones a Excel.
                            <span style={legendIconStyles}><FileDownloadIcon sx={{ fontSize: 14, mr: 0.5 }} />Exportar seleccionados</span>
                            Solo las filas seleccionadas.
                            <span style={legendIconStyles}><FileDownloadIcon sx={{ fontSize: 14, mr: 0.5 }} />Exportar página</span>
                            Solo la página actual.
                        </Box>
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

export default TablaActuaciones;
