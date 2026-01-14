import { useCallback, useMemo, useRef, useState } from "react";
import DataEditor, {
    type GridCell,
    GridCellKind,
    type GridColumn,
    type Item,
    type EditableGridCell,
    type Theme,
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

// Definición de columnas según los datos actuales
const COLUMN_DEFINITIONS = [
    { id: "_state", title: "Estado", width: 100, editable: false },
    { id: "_errors", title: "Errores", width: 250, editable: false },
    { id: "ID", title: "ID", width: 80, editable: false },
    { id: "Fecha actuación", title: "Fecha actuación", width: 150, editable: true },
    { id: "Tipo actuación", title: "Tipo actuación", width: 150, editable: true },
    { id: "Contraproducencia", title: "Contraproducencia", width: 150, editable: true },
    { id: "Orden de trabajo", title: "Orden de trabajo", width: 150, editable: true },
    { id: "Inspector 1", title: "Inspector 1", width: 150, editable: true },
    { id: "Inspector 2", title: "Inspector 2", width: 150, editable: true },
    { id: "Inspector 3", title: "Inspector 3", width: 150, editable: true },
    { id: "Calle", title: "Calle", width: 200, editable: true },
    { id: "Número", title: "Número", width: 100, editable: true },
    { id: "Rubro", title: "Rubro", width: 150, editable: true },
    { id: "Apellido", title: "Apellido", width: 150, editable: true },
    { id: "Nombre", title: "Nombre", width: 150, editable: true },
    { id: "DNI", title: "DNI", width: 120, editable: true },
    { id: "Acta inspección", title: "Acta inspección", width: 150, editable: true },
    { id: "Acta notificación", title: "Acta notificación", width: 150, editable: true },
    { id: "Motivo notif 1", title: "Motivo notif 1", width: 150, editable: true },
    { id: "Motivo notif 2", title: "Motivo notif 2", width: 150, editable: true },
    { id: "Motivo notif 3", title: "Motivo notif 3", width: 150, editable: true },
    { id: "Acta comprobación", title: "Acta comprobación", width: 150, editable: true },
    { id: "Motivo comprobación", title: "Motivo comprobación", width: 180, editable: true },
    { id: "Acta clausura", title: "Acta clausura", width: 150, editable: true },
    { id: "Acta decomiso", title: "Acta decomiso", width: 150, editable: true },
    { id: "Kilos decomiso", title: "Kilos decomiso", width: 120, editable: true },
    { id: "Acta notificación previa", title: "Acta notificación previa", width: 180, editable: true },
    { id: "Acta comprobación previa", title: "Acta comprobación previa", width: 180, editable: true },
    { id: "Expediente año", title: "Expediente año", width: 130, editable: true },
    { id: "Expediente número", title: "Expediente número", width: 150, editable: true },
    { id: "Oficio año", title: "Oficio año", width: 120, editable: true },
    { id: "Oficio número", title: "Oficio número", width: 130, editable: true },
    { id: "Oficio causa", title: "Oficio causa", width: 120, editable: true },
];

const TablaCargarActuacionesGlide = () => {
    const [batchId, setBatchId] = useState<string | null>(null);
    const [data, setData] = useState<GridRow[]>([]);
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
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            setGlobalError(error?.response?.data?.message || "Error al iniciar batch");
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

            // Actualizar estado de cada fila
            setData((prev) =>
                prev.map((row) => {
                    const result = response.results.find((r) => r.row_id === row._rowId);
                    if (!result) return row;

                    return {
                        ...row,
                        _state: result.ok ? "OK" : "ERROR",
                        _errors: result.errors
                            ? Object.entries(result.errors)
                                  .map(([col, msg]) => `${col}: ${msg}`)
                                  .join("; ")
                            : undefined,
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
                        _errors: undefined,
                    };
                } else if (!result.ok) {
                    return {
                        ...row,
                        _state: "ERROR",
                        _errors: result.errors
                            ? Object.entries(result.errors)
                                  .map(([col, msg]) => `${col}: ${msg}`)
                                  .join("; ")
                            : "Error desconocido",
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
                              _errors: response.errors
                                  ? Object.entries(response.errors)
                                        .map(([col, msg]) => `${col}: ${msg}`)
                                        .join("; ")
                                  : undefined,
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
                              _errors: error?.response?.data?.message || "Error en validación",
                          }
                        : r
                )
            );
        }
    };

    const handleCellEdit = useCallback(
        ([col, row]: Item, newValue: EditableGridCell): void => {
            if (row >= data.length) return;

            const columnId = COLUMN_DEFINITIONS[col].id;
            const rowData = data[row];

            // No editar columnas de sistema
            if (columnId === "_state" || columnId === "_errors" || columnId === "ID") {
                return;
            }

            // Extraer el valor según el tipo de celda
            let value: any;
            if (newValue.kind === GridCellKind.Text) {
                value = newValue.data;
            } else if (newValue.kind === GridCellKind.Number) {
                value = newValue.data;
            } else if (newValue.kind === GridCellKind.Boolean) {
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
                    handleValidateRow(updatedRow);
                }, 500);
            }
        },
        [data, batchId]
    );

    // ============= HELPERS =============

    const extractDataColumns = (row: GridRow): GridRow => {
        const { _rowId, _state, _errors, _normalized, ...dataColumns } = row;
        return dataColumns;
    };

    const handleAddRow = () => {
        const rowId = generateRowId();
        const newRow: GridRow = {
            _rowId: rowId,
            _state: "PENDIENTE",
        };

        setData((prev) => [...prev, newRow]);

        // Si hay batch iniciado, podemos validar automáticamente (opcional)
        // if (batchId) {
        //     handleValidateRow(newRow);
        // }
    };

    // ============= GLIDE DATA GRID CONFIGURATION =============

    const columns = useMemo<GridColumn[]>(
        () =>
            COLUMN_DEFINITIONS.map((col) => ({
                title: col.title,
                id: col.id,
                width: col.width,
            })),
        []
    );

    const getCellContent = useCallback(
        ([col, row]: Item): GridCell => {
            if (row >= data.length) {
                return {
                    kind: GridCellKind.Text,
                    data: "",
                    displayData: "",
                    allowOverlay: false,
                };
            }

            const rowData = data[row];
            const columnId = COLUMN_DEFINITIONS[col].id;
            const value = rowData[columnId as keyof GridRow];

            // Columna Estado
            if (columnId === "_state") {
                const state = value as string;
                let displayData = "PENDIENTE";
                let themeOverride: Partial<Theme> = {};

                if (state === "OK") {
                    displayData = "✓ OK";
                    themeOverride = {
                        bgCell: "#e8f5e9",
                        textDark: "#2e7d32",
                    };
                } else if (state === "ERROR") {
                    displayData = "✗ ERROR";
                    themeOverride = {
                        bgCell: "#ffebee",
                        textDark: "#c62828",
                    };
                } else {
                    themeOverride = {
                        bgCell: "#fff3e0",
                        textDark: "#ef6c00",
                    };
                }

                return {
                    kind: GridCellKind.Text,
                    data: displayData,
                    displayData: displayData,
                    allowOverlay: false,
                    readonly: true,
                    themeOverride,
                };
            }

            // Columna Errores
            if (columnId === "_errors") {
                const errors = value as string | undefined;
                return {
                    kind: GridCellKind.Text,
                    data: errors || "",
                    displayData: errors || "",
                    allowOverlay: true,
                    readonly: true,
                    themeOverride: errors
                        ? {
                              textDark: "#c62828",
                          }
                        : undefined,
                };
            }

            // Columnas normales editables
            const strValue = value?.toString() || "";
            const isEditable = COLUMN_DEFINITIONS[col].editable;

            return {
                kind: GridCellKind.Text,
                data: strValue,
                displayData: strValue,
                allowOverlay: isEditable,
                readonly: !isEditable,
            };
        },
        [data]
    );

    const onRowAppended = useCallback(() => {
        handleAddRow();
    }, [batchId]);

    // Tema personalizado para un estilo moderno
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

    return (
        <Box sx={{ width: "100%", height: "100%" }}>
            <Box sx={{ ...TableGeneralStyles }}>
                <Typography sx={TableTitleStyles}>
                    Creación de actuación (Batch Grid - Glide)
                </Typography>

                {globalError && (
                    <Alert severity="error" onClose={() => setGlobalError(null)} sx={{ mb: 2 }}>
                        {globalError}
                    </Alert>
                )}

                {batchId && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                        Batch activo: <strong>{batchId}</strong> | Filas:{" "}
                        {data.filter((r) => r._state === "OK").length} OK /{" "}
                        {data.filter((r) => r._state === "ERROR").length} ERROR /{" "}
                        {data.filter((r) => r._state === "PENDIENTE").length} PENDIENTE
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
                    >
                        {batchId ? `Batch: ${batchId.slice(0, 8)}...` : "Iniciar Batch"}
                    </Button>

                    <Button
                        variant="outlined"
                        color="secondary"
                        onClick={handleValidateAll}
                        disabled={!batchId || isValidatingAll || data.length === 0}
                        startIcon={isValidatingAll ? <CircularProgress size={16} /> : undefined}
                    >
                        Validar Todo
                    </Button>

                    <Button
                        variant="contained"
                        color="success"
                        onClick={handleCommitAll}
                        disabled={!batchId || isCommitting || data.length === 0}
                        startIcon={isCommitting ? <CircularProgress size={16} /> : undefined}
                    >
                        Confirmar Carga
                    </Button>

                    <Button
                        variant="outlined"
                        onClick={handleAddRow}
                        disabled={!batchId}
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
                        borderRadius: "4px",
                        overflow: "hidden",
                    }}
                >
                    <DataEditor
                        ref={gridRef}
                        getCellContent={getCellContent}
                        columns={columns}
                        rows={data.length}
                        onCellEdited={handleCellEdit}
                        onRowAppended={onRowAppended}
                        theme={customTheme}
                        smoothScrollX={true}
                        smoothScrollY={true}
                        rowMarkers="both"
                        rowHeight={40}
                        headerHeight={44}
                        trailingRowOptions={{
                            sticky: true,
                            tint: true,
                            hint: "Nueva fila...",
                        }}
                        getCellsForSelection={true}
                        freezeColumns={3}
                    />
                </Box>
            </Box>
        </Box>
    );
};

export default TablaCargarActuacionesGlide;
