import { useCallback, useMemo, useRef, useState } from "react";
import DataEditor, {
    type GridCell,
    GridCellKind,
    type GridColumn,
    type Item,
    type EditableGridCell,
    type Theme,
    GridColumnIcon,
} from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import { Box, Typography, Button, Stack, Alert, CircularProgress } from "@mui/material";
import { TableGeneralStyles, TableTitleStyles } from "../../../styles/TablasStyle";
import {
    startBatch,
    validateRow,
    validateBatch,
    commitRow,
    commitBatch,
    type GridRow,
} from "../../../api/gridApi";

// Generador de IDs únicos para filas
const generateRowId = (() => {
    let counter = 0;
    return () => `row_${Date.now()}_${counter++}`;
})();

// Configuración de íconos y colores por grupo
const GROUP_CONFIG = {
    "Actuación": {
        icon: GridColumnIcon.HeaderArray,
        color: "#e3f2fd", // Azul claro
    },
    "Inspectores": {
        icon: GridColumnIcon.HeaderCode,
        color: "#f3e5f5", // Morado claro
    },
    "Establecimiento": {
        icon: GridColumnIcon.HeaderUri,
        color: "#fff3e0", // Naranja claro
    },
    "Actas": {
        icon: GridColumnIcon.HeaderString,
        color: "#e8f5e9", // Verde claro
    },
    "Reinspección": {
        icon: GridColumnIcon.HeaderReference,
        color: "#fff9c4", // Amarillo claro
    },
    "Expediente": {
        icon: GridColumnIcon.HeaderMarkdown,
        color: "#fce4ec", // Rosa claro
    },
};

// Definición de columnas agrupadas según el dominio
const COLUMN_DEFINITIONS = [
    // Grupo: Actuación
    { id: "ID", title: "ID", width: 80, editable: false, group: "Actuación", icon: GridColumnIcon.HeaderNumber },
    { id: "Fecha actuación", title: "Fecha actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderDate },
    { id: "Tipo actuación", title: "Tipo actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderString },
    { id: "Contraproducencia", title: "Contraproducencia", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderString },
    { id: "Orden de trabajo", title: "Orden de trabajo", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderNumber },
    
    // Grupo: Inspectores
    { id: "Inspector 1", title: "Inspector 1", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString },
    { id: "Inspector 2", title: "Inspector 2", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString },
    { id: "Inspector 3", title: "Inspector 3", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString },
    
    // Grupo: Establecimiento
    { id: "Calle", title: "Calle", width: 200, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString },
    { id: "Número", title: "Número", width: 100, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber },
    { id: "Rubro", title: "Rubro", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString },
    { id: "Apellido", title: "Apellido", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString },
    { id: "Nombre", title: "Nombre", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString },
    { id: "DNI", title: "DNI", width: 120, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber },
    
    // Grupo: Actas
    { id: "Acta inspección", title: "Acta inspección", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber },
    { id: "Acta notificación", title: "Acta notificación", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber },
    { id: "Motivo notif 1", title: "Motivo notif 1", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString },
    { id: "Motivo notif 2", title: "Motivo notif 2", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString },
    { id: "Motivo notif 3", title: "Motivo notif 3", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString },
    { id: "Acta comprobación", title: "Acta comprobación", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber },
    { id: "Motivo comprobación", title: "Motivo comprobación", width: 180, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString },
    { id: "Acta clausura", title: "Acta clausura", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber },
    { id: "Acta decomiso", title: "Acta decomiso", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber },
    { id: "Kilos decomiso", title: "Kilos decomiso", width: 120, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber },
    
    // Grupo: Reinspección
    { id: "Acta notificación previa", title: "Acta notificación previa", width: 180, editable: true, group: "Reinspección", icon: GridColumnIcon.HeaderReference },
    
    // Grupo: Expediente
    { id: "Acta comprobación previa", title: "Acta comprobación previa", width: 180, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderNumber },
    { id: "Expediente año", title: "Expediente año", width: 130, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderDate },
    { id: "Expediente número", title: "Expediente número", width: 150, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderNumber },
    { id: "Oficio año", title: "Oficio año", width: 120, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderDate },
    { id: "Oficio número", title: "Oficio número", width: 130, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderNumber },
    { id: "Oficio causa", title: "Oficio causa", width: 120, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderString },
];

const TablaCargarActuacionesGlideStyled = () => {
    // Inicializar con 5 filas vacías para empezar a cargar inmediatamente
    const initialRows = useMemo(() => {
        return Array.from({ length: 5 }, () => ({
            _rowId: generateRowId(),
            _state: "PENDIENTE" as const,
            _cellErrors: {},
        }));
    }, []);

    const [batchId, setBatchId] = useState<string | null>(null);
    const [data, setData] = useState<GridRow[]>(initialRows);
    const [isLoadingBatch, setIsLoadingBatch] = useState(false);
    const [isValidatingAll, setIsValidatingAll] = useState(false);
    const [isCommitting, setIsCommitting] = useState(false);
    const [globalError, setGlobalError] = useState<string | null>(null);

    const gridRef = useRef<any>(null);
    const debounceRef = useRef<Record<string, number>>({});

    // ============= BATCH OPERATIONS =============

    const handleStartBatch = async () => {
        try {
            setIsLoadingBatch(true);
            setGlobalError(null);
            const response = await startBatch();
            setBatchId(response.batch_id);
            
            console.log("✅ Batch iniciado:", response.batch_id);
            
            // No modificar las filas existentes, solo establecer el batch_id
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            const errorMsg = error?.response?.data?.message || error?.message || "Error al iniciar batch. Verifica que el backend esté corriendo en http://localhost:5000";
            setGlobalError(errorMsg);
        } finally {
            setIsLoadingBatch(false);
        }
    };

    const handleValidateAll = async () => {
        if (!batchId) {
            setGlobalError("Debes iniciar un batch primero");
            return;
        }

        try {
            setIsValidatingAll(true);
            setGlobalError(null);

            const rowsToValidate = data.map((row) => ({
                row_id: row._rowId!,
                row: extractDataColumns(row),
            }));

            const response = await validateBatch({
                batch_id: batchId,
                rows: rowsToValidate,
            });

            console.log("✅ Validación batch completada:", response);

            // Actualizar estado de cada fila con errores por celda
            setData((prev) =>
                prev.map((row) => {
                    const result = response.results.find((r) => r.row_id === row._rowId);
                    if (!result) return row;

                    return {
                        ...row,
                        _state: result.ok ? "OK" : "ERROR",
                        _cellErrors: result.errors || {},
                        _normalized: result.normalized,
                    };
                })
            );
        } catch (error: any) {
            console.error("❌ Error en validación batch:", error);
            setGlobalError(error?.response?.data?.message || "Error al validar batch");
        } finally {
            setIsValidatingAll(false);
        }
    };

    const handleCommitAll = async () => {
        if (!batchId) {
            setGlobalError("Debes iniciar un batch primero");
            return;
        }

        const okRows = data.filter((row) => row._state === "OK");

        if (okRows.length === 0) {
            setGlobalError("No hay filas válidas para confirmar. Valida primero.");
            return;
        }

        try {
            setIsCommitting(true);
            setGlobalError(null);

            const rowsToCommit = okRows.map((row) => ({
                row_id: row._rowId!,
                normalized: row._normalized || extractDataColumns(row),
            }));

            try {
                const response = await commitBatch({
                    batch_id: batchId,
                    rows: rowsToCommit,
                });

                console.log("✅ Commit batch completado:", response);
                processCommitResults(response.results);
            } catch (error: any) {
                if (error.message === "FALLBACK_TO_INDIVIDUAL") {
                    console.log("⚠️ Usando commit individual...");
                    await commitIndividual(rowsToCommit);
                } else {
                    throw error;
                }
            }
        } catch (error: any) {
            console.error("❌ Error en commit:", error);
            setGlobalError(error?.response?.data?.message || "Error al confirmar carga");
        } finally {
            setIsCommitting(false);
        }
    };

    const commitIndividual = async (rows: Array<{ row_id: string; normalized: GridRow }>) => {
        const results = [];
        for (const { row_id, normalized } of rows) {
            try {
                const result = await commitRow({ batch_id: batchId!, row_id, normalized });
                results.push(result);
            } catch (error: any) {
                results.push({
                    batch_id: batchId!,
                    row_id,
                    ok: false,
                    errors: { _global: error?.response?.data?.message || "Error al confirmar" },
                });
            }
        }
        processCommitResults(results);
    };

    const processCommitResults = (results: Array<any>) => {
        setData((prev) =>
            prev.map((row) => {
                const result = results.find((r) => r.row_id === row._rowId);
                if (!result) return row;

                if (result.ok && result.persisted?.id) {
                    return {
                        ...row,
                        ID: result.persisted.id,
                        _state: "OK",
                        _cellErrors: {},
                    };
                } else if (!result.ok) {
                    return {
                        ...row,
                        _state: "ERROR",
                        _cellErrors: result.errors || {},
                    };
                }
                return row;
            })
        );
    };

    // ============= ROW VALIDATION =============

    const handleValidateRow = async (row: GridRow) => {
        if (!batchId) {
            console.warn("⚠️ No hay batch iniciado, omitiendo validación");
            return;
        }

        try {
            const dataColumns = extractDataColumns(row);
            const response = await validateRow({
                batch_id: batchId,
                row_id: row._rowId!,
                row: dataColumns,
            });

            console.log("✅ Validación fila:", response);

            setData((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: response.ok ? "OK" : "ERROR",
                              _cellErrors: response.errors || {},
                              _normalized: response.normalized,
                          }
                        : r
                )
            );
        } catch (error: any) {
            console.error("❌ Error validando fila:", error);
            setData((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: "ERROR",
                              _cellErrors: { _global: error?.response?.data?.message || "Error en validación" },
                          }
                        : r
                )
            );
        }
    };

    const handleCellEdit = useCallback(
        ([col, row]: Item, newValue: EditableGridCell): void => {
            if (row >= data.length) return;

            const columnDef = COLUMN_DEFINITIONS[col];
            const columnId = columnDef.id;
            const rowData = data[row];

            // No editar columna ID
            if (columnId === "ID") {
                return;
            }

            // Extraer el valor según el tipo de celda
            let value: any;
            if (newValue.kind === GridCellKind.Text) {
                value = newValue.data;
            } else if (newValue.kind === GridCellKind.Number) {
                value = newValue.data;
            } else {
                value = (newValue as any).data;
            }

            // Actualizar datos
            const updatedRow = {
                ...rowData,
                [columnId]: value,
            };

            setData((prev) => {
                const newData = [...prev];
                newData[row] = updatedRow;
                return newData;
            });

            // Debounce validation
            const rowId = rowData._rowId;
            if (rowId && debounceRef.current[rowId] !== undefined) {
                clearTimeout(debounceRef.current[rowId]);
            }

            if (rowId) {
                debounceRef.current[rowId] = window.setTimeout(() => {
                    if (batchId) {
                        handleValidateRow(updatedRow);
                    }
                }, 500);
            }
        },
        [data, batchId]
    );

    // ============= HELPERS =============

    const extractDataColumns = (row: GridRow): GridRow => {
        const { _rowId, _state, _cellErrors, _normalized, _validation_history, ...dataColumns } = row;
        return dataColumns;
    };

    const handleAddRow = () => {
        const rowId = generateRowId();
        const newRow: GridRow = {
            _rowId: rowId,
            _state: "PENDIENTE",
            _cellErrors: {},
        };

        setData((prev) => [...prev, newRow]);
    };

    // ============= GLIDE DATA GRID CONFIGURATION =============

    const columns = useMemo<GridColumn[]>(
        () =>
            COLUMN_DEFINITIONS.map((col) => {
                const groupConfig = col.group ? GROUP_CONFIG[col.group as keyof typeof GROUP_CONFIG] : undefined;
                return {
                    title: col.title,
                    id: col.id,
                    width: col.width,
                    group: col.group,
                    icon: col.icon,
                    themeOverride: groupConfig ? {
                        bgHeader: groupConfig.color,
                        bgHeaderHovered: groupConfig.color,
                    } : undefined,
                };
            }),
        []
    );

    const getCellContent = useCallback(
        ([col, row]: Item): GridCell => {
            if (row >= data.length) {
                return {
                    kind: GridCellKind.Text,
                    data: "",
                    displayData: "",
                    allowOverlay: true,
                };
            }

            const rowData = data[row];
            const columnDef = COLUMN_DEFINITIONS[col];
            const columnId = columnDef.id;
            const value = rowData[columnId as keyof GridRow];
            const cellErrors = (rowData._cellErrors || {}) as Record<string, string>;
            const hasError = cellErrors[columnId] !== undefined;
            
            // Estado de la fila
            const rowState = rowData._state;

            // Columna ID (no editable, visible solo si tiene valor)
            if (columnId === "ID") {
                const strValue = value?.toString() || "";
                return {
                    kind: GridCellKind.Text,
                    data: strValue,
                    displayData: strValue,
                    allowOverlay: false,
                    readonly: true,
                    themeOverride: {
                        bgCell: "#f5f5f5",
                        textDark: "#9e9e9e",
                    },
                };
            }

            // Determinar color de fondo según estado y errores
            let bgColor = "#ffffff";
            let textColor = "#1a1a1a";
            
            if (hasError) {
                // Celda con error específico
                bgColor = "#ffebee";
                textColor = "#c62828";
            } else if (rowState === "OK") {
                // Fila validada OK
                bgColor = "#e8f5e9";
                textColor = "#2e7d32";
            } else if (rowState === "ERROR") {
                // Fila con error pero esta celda no tiene error específico
                bgColor = "#fff9c4";
                textColor = "#f57f17";
            }

            // Columnas normales editables
            const strValue = value?.toString() || "";

            return {
                kind: GridCellKind.Text,
                data: strValue,
                displayData: strValue,
                allowOverlay: true, // Permite abrir el editor overlay
                themeOverride: {
                    bgCell: bgColor,
                    textDark: textColor,
                },
            };
        },
        [data]
    );

    // Auto-crear fila al llegar al final con Tab
    const handleFinishedEditing = useCallback(
        (_newValue: GridCell | undefined, [col, row]: Item) => {
            // Si estamos en la última fila y última columna editable
            const isLastRow = row === data.length - 1;
            const isLastColumn = col === COLUMN_DEFINITIONS.length - 1;

            if (isLastRow && isLastColumn) {
                // Crear nueva fila automáticamente
                setTimeout(() => {
                    handleAddRow();
                }, 100);
            }
        },
        [data]
    );

    // Tema personalizado moderno
    const customTheme = useMemo<Partial<Theme>>(
        () => ({
            accentColor: "#1976d2",
            accentLight: "#42a5f5",
            textDark: "#1a1a1a",
            textMedium: "#606060",
            textLight: "#9e9e9e",
            textBubble: "#ffffff",
            bgIconHeader: "#1976d2",
            fgIconHeader: "#ffffff",
            textHeader: "#424242",
            textHeaderSelected: "#1976d2",
            bgCell: "#ffffff",
            bgCellMedium: "#fafafa",
            bgHeader: "#f5f5f5",
            bgHeaderHasFocus: "#eeeeee",
            bgHeaderHovered: "#e0e0e0",
            bgBubble: "#eeeeee",
            bgBubbleSelected: "#1976d2",
            bgSearchResult: "#fff9c4",
            borderColor: "#e0e0e0",
            drilldownBorder: "#1976d2",
            linkColor: "#1976d2",
            headerFontStyle: "600 14px",
            baseFontStyle: "13px",
            fontFamily: "Inter, Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }),
        []
    );

    // Contador de estados
    const okCount = data.filter((r) => r._state === "OK").length;
    const errorCount = data.filter((r) => r._state === "ERROR").length;
    const pendingCount = data.filter((r) => r._state === "PENDIENTE").length;

    return (
        <Box sx={{ width: "100%", height: "100%" }}>
            <Box sx={{ ...TableGeneralStyles }}>
                <Typography sx={TableTitleStyles}>
                    Creación de actuación (Batch Grid - Glide) 🎨
                </Typography>

                {globalError && (
                    <Alert severity="error" onClose={() => setGlobalError(null)} sx={{ mb: 2 }}>
                        {globalError}
                    </Alert>
                )}

                {!batchId && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        <strong>💡 Tip:</strong> Puedes empezar a cargar datos directamente. Haz click en "Iniciar Batch" cuando estés listo para validar.
                    </Alert>
                )}

                {batchId && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                        <strong>Batch activo:</strong> {batchId.slice(0, 13)}... | 
                        <strong style={{ color: "#2e7d32", marginLeft: 8 }}>{okCount} OK</strong> | 
                        <strong style={{ color: "#c62828", marginLeft: 8 }}>{errorCount} ERROR</strong> | 
                        <strong style={{ color: "#ef6c00", marginLeft: 8 }}>{pendingCount} PENDIENTE</strong>
                    </Alert>
                )}

                {/* Toolbar */}
                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleStartBatch}
                        disabled={isLoadingBatch || batchId !== null}
                        startIcon={isLoadingBatch ? <CircularProgress size={16} /> : undefined}
                        size="large"
                    >
                        {batchId ? `✓ Batch Activo` : "1. Iniciar Batch"}
                    </Button>

                    <Button
                        variant="outlined"
                        color="secondary"
                        onClick={handleValidateAll}
                        disabled={!batchId || isValidatingAll || data.length === 0}
                        startIcon={isValidatingAll ? <CircularProgress size={16} /> : undefined}
                        size="large"
                    >
                        2. Validar Todo ({data.length})
                    </Button>

                    <Button
                        variant="contained"
                        color="success"
                        onClick={handleCommitAll}
                        disabled={!batchId || isCommitting || okCount === 0}
                        startIcon={isCommitting ? <CircularProgress size={16} /> : undefined}
                        size="large"
                    >
                        3. Confirmar Carga ({okCount})
                    </Button>

                    <Box sx={{ flexGrow: 1 }} />

                    <Button 
                        variant="outlined" 
                        onClick={handleAddRow}
                        size="medium"
                    >
                        + Agregar Fila
                    </Button>
                </Stack>

                {/* Data Grid */}
                <Box
                    sx={{
                        height: "calc(100vh - 350px)",
                        minHeight: "500px",
                        border: "1px solid #e0e0e0",
                        borderRadius: "8px",
                        overflow: "hidden",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                    }}
                >
                    <DataEditor
                        ref={gridRef}
                        getCellContent={getCellContent}
                        columns={columns}
                        rows={data.length}
                        onCellEdited={handleCellEdit}
                        onFinishedEditing={handleFinishedEditing}
                        theme={customTheme}
                        smoothScrollX={true}
                        smoothScrollY={true}
                        rowMarkers="both"
                        rowHeight={40}
                        headerHeight={44}
                        getCellsForSelection={true}
                        freezeColumns={0}
                        keybindings={{
                            search: true,
                        }}
                        getGroupDetails={(groupName) => {
                            const config = GROUP_CONFIG[groupName as keyof typeof GROUP_CONFIG];
                            return config ? {
                                name: groupName,
                                icon: config.icon,
                            } : {
                                name: groupName,
                            };
                        }}
                        groupHeaderHeight={36}
                    />
                </Box>

                {/* Leyenda */}
                <Box sx={{ mt: 2, p: 2, bgcolor: "#e8f5e9", borderRadius: "4px", border: "1px solid #81c784" }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                        📝 Cómo usar:
                    </Typography>
                    <Typography variant="body2" component="div">
                        <strong>1.</strong> Empieza a cargar datos: <strong>Haz DOBLE CLICK</strong> en cualquier celda o presiona <kbd style={{ padding: "2px 6px", background: "#fff", border: "1px solid #ccc", borderRadius: "3px" }}>Enter</kbd> para editarla<br/>
                        <strong>2.</strong> Presiona <kbd style={{ padding: "2px 6px", background: "#fff", border: "1px solid #ccc", borderRadius: "3px" }}>Tab</kbd> para moverte entre celdas. Al llegar al final, se crea una nueva fila automáticamente<br/>
                        <strong>3.</strong> Click en "Iniciar Batch" cuando tengas datos cargados<br/>
                        <strong>4.</strong> Click en "Validar Todo" para validar todas las filas<br/>
                        <strong>5.</strong> Click en "Confirmar Carga" para guardar en la base de datos<br/>
                        <br/>
                        <strong>Colores:</strong> 🔴 Celda con error | 🟢 Fila OK | 🟡 Fila con error en otra celda | ⚪ Pendiente
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

export default TablaCargarActuacionesGlideStyled;
