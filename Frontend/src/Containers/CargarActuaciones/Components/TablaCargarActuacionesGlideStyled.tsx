import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DataEditor, {
    type GridCell,
    GridCellKind,
    type GridColumn,
    type Item,
    type EditableGridCell,
} from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import { allCells } from "@glideapps/glide-data-grid-cells";
import "@glideapps/glide-data-grid-cells/dist/index.css";
import { Box, Typography, Alert, Button, CircularProgress } from "@mui/material";
import {
    startBatch,
    validateRow,
    validateBatch,
    commitBatch,
    type GridRow,
    fetchInspectores,
    fetchMotivos,
    fetchRubros,
    fetchTiposActuacion,
    fetchContraproducencias,
    fetchMotivosComprobacion,
} from "../../../api/gridApi";

// Imports modulares
import {
    COLORS,
    containerStyles,
    wrapperStyles,
    titleStyles,
    alertBaseStyles,
    gridContainerStyles,
    legendStyles,
    legendTitleStyles,
    legendTextStyles,
    kbdStyles,
    getStatusBadgeStyles,
} from "../styles/cargarActuacionesStyles";
import { COLUMN_DEFINITIONS, GROUP_CONFIG } from "../config/columnDefinitions";
import { getDropdownOptions } from "../config/dropdownOptions";
import { gridTheme, calculateTableHeight, GRID_DIMENSIONS } from "../config/gridTheme";
import {
    extractDataColumns,
    rowHasData,
    createEmptyRow,
    createEmptyRows,
    parseDateValue,
    formatDateToISO,
} from "../utils/gridHelpers";

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================
const TablaCargarActuacionesGlideStyled = () => {
    // Estado inicial con 5 filas vacías
    const initialRows = useMemo(() => createEmptyRows(5), []);

    // Estados
    const [batchId, setBatchId] = useState<string | null>(null);
    const [data, setData] = useState<GridRow[]>(initialRows);
    const [isLoadingBatch, setIsLoadingBatch] = useState(false);
    const [isValidatingAll, setIsValidatingAll] = useState(false); // estado para validar/mandar todo
    const [isCommitting, setIsCommitting] = useState(false);
    const [globalError, setGlobalError] = useState<string | null>(null);
    const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
    const [catalogMotivos, setCatalogMotivos] = useState<string[]>([]);
    const [catalogRubros, setCatalogRubros] = useState<string[]>([]);
    const [catalogTipos, setCatalogTipos] = useState<string[]>([]);
    const [catalogContras, setCatalogContras] = useState<string[]>([]);
    const [catalogMotivosComprobacion, setCatalogMotivosComprobacion] = useState<string[]>([]);

    // Referencias
    const gridRef = useRef<any>(null);
    const debounceRef = useRef<Record<string, number>>({});
    const dataRef = useRef<GridRow[]>(initialRows);
    const batchValidateRef = useRef<number | undefined>(undefined);
    const startingBatchRef = useRef<boolean>(false);

    // Catálogos combinados para dropdowns
    const catalogs = useMemo(() => ({
        inspectores: catalogInspectores,
        motivos: catalogMotivos,
        rubros: catalogRubros,
        tipos: catalogTipos,
        contraproducencias: catalogContras,
        motivosComprobacion: catalogMotivosComprobacion,
    }), [catalogInspectores, catalogMotivos, catalogRubros, catalogTipos, catalogContras, catalogMotivosComprobacion]);

    // Auto-iniciar batch
    const ensureBatchStarted = useCallback(async (): Promise<string | null> => {
        if (batchId) return batchId;
        if (startingBatchRef.current) return null;
        startingBatchRef.current = true;
        try {
            setIsLoadingBatch(true);
            setGlobalError(null);
            const response = await startBatch("actuaciones");
            setBatchId(response.batch_id);
            console.log("✅ Batch iniciado (auto):", response.batch_id);
            return response.batch_id;
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            setGlobalError(error?.response?.data?.message || error?.message || "Error al iniciar batch");
            return null;
        } finally {
            setIsLoadingBatch(false);
            startingBatchRef.current = false;
        }
    }, [batchId]);

    useEffect(() => {
        dataRef.current = data;
    }, [data]);

    // Cargar catálogos
    useEffect(() => {
        const loadCatalogs = async () => {
            try {
                const [inspectoresResp, motivosResp, rubrosResp, tiposResp, contrasResp, motivosCompResp] = await Promise.all([
                    fetchInspectores(),
                    fetchMotivos(),
                    fetchRubros(),
                    fetchTiposActuacion(),
                    fetchContraproducencias(),
                    fetchMotivosComprobacion(),
                ]);
                // Deduplicar catálogos para evitar nombres repetidos
                setCatalogInspectores([...new Set(inspectoresResp.items.map((i) => i.nombre))]);
                setCatalogMotivos([...new Set(motivosResp.items.map((m) => m.nombre))]);
                setCatalogRubros([...new Set(rubrosResp.items.map((r) => r.nombre))]);
                setCatalogTipos([...new Set(tiposResp.items.map((t) => t.nombre))]);
                setCatalogContras([...new Set(contrasResp.items.map((c) => c.nombre))]);
                setCatalogMotivosComprobacion([...new Set(motivosCompResp.items.map((m) => m.nombre))]);
            } catch (error: any) {
                console.error("❌ Error cargando catálogos:", error);
                setGlobalError("Error cargando catálogos (inspectores/motivos/rubros/tipos/contraproducencia).");
            }
        };
        loadCatalogs();
    }, []);

    const buildRowErrorSummary = (errors?: Record<string, string>) => {
        if (!errors) return null;
        const messages: string[] = [];

        const topLevel = errors._row || errors.detail || errors._global;
        if (topLevel) {
            messages.push(topLevel);
        }

        Object.entries(errors)
            .filter(([key]) => !["_row", "detail", "_global"].includes(key))
            .forEach(([key, value]) => {
                if (value) {
                    messages.push(`${key}: ${value}`);
                }
            });

        if (messages.length === 0) return null;
        return messages.join(" | ");
    };

    // Validar batch de filas - SOLO las que tienen datos
    const validateBatchRows = useCallback(async (rows: GridRow[], batchIdValue?: string) => {
        const effectiveBatchId = batchIdValue || batchId;
        if (!effectiveBatchId) return null;
        
        // Solo validar filas que tienen datos cargados y fueron editadas o no están OK
        const rowsWithData = rows.filter(
            (row) => rowHasData(row) && (row._touched || row._state !== "OK")
        );
        if (rowsWithData.length === 0) return null;

        // Marcar filas como VALIDANDO mientras se ejecuta la validación
            setData((prev) =>
                prev.map((row) =>
                    rowsWithData.some((r) => r._rowId === row._rowId)
                        ? { ...row, _state: "VALIDANDO" }
                        : row
                )
            );

        const rowsToValidate = rowsWithData.map((row) => ({
            row_id: row._rowId!,
            row: extractDataColumns(row),
        }));

        try {
            const response = await validateBatch({
                batch_id: effectiveBatchId,
                rows: rowsToValidate,
            });

            setData((prev) =>
                prev.map((row) => {
                    const result = response.results.find((r) => r.row_id === row._rowId);
                    if (!result) return row;
                    return {
                        ...row,
                        _state: result.ok ? "OK" : "ERROR",
                        _cellErrors: result.errors || {},
                        _rowError: buildRowErrorSummary(result.errors),
                        _normalized: result.normalized,
                        _touched: result.ok ? false : row._touched,
                    };
                })
            );

            return response;
        } catch (error: any) {
            console.error("❌ Error en validación batch:", error);
            return null;
        }
    }, [batchId]);

    // Validar fila individual
    const handleValidateRow = useCallback(async (row: GridRow) => {
        if (!batchId) return;
        
        // Solo validar si la fila tiene datos
        if (!rowHasData(row)) return;

        // Marcar fila como VALIDANDO mientras se valida
        setData((prev) =>
            prev.map((r) =>
                r._rowId === row._rowId ? { ...r, _state: "VALIDANDO" } : r
            )
        );

        try {
            const dataColumns = extractDataColumns(row);
            const response = await validateRow({
                batch_id: batchId,
                row_id: row._rowId!,
                row: dataColumns,
            });

            setData((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: response.ok ? "OK" : "ERROR",
                              _cellErrors: response.errors || {},
                              _rowError: buildRowErrorSummary(response.errors),
                              _normalized: response.normalized,
                              _touched: response.ok ? false : r._touched,
                          }
                        : r
                )
            );

            // Nota: no se hace commit automático por fila (solo validate)
        } catch (error: any) {
            console.error("❌ Error validando fila:", error);
            setData((prev) =>
                prev.map((r) =>
                    r._rowId === row._rowId
                        ? {
                              ...r,
                              _state: "ERROR",
                              _cellErrors: { _global: error?.response?.data?.message || "Error en validación" },
                              _rowError: error?.response?.data?.message || "Error en validación",
                          }
                        : r
                )
            );
        }
    }, [batchId]);

    const handleCommitBatch = useCallback(async () => {
        // Botón único: valida batch y luego confirma (commit batch)
        const startedBatchId = await ensureBatchStarted();
        if (!startedBatchId) return;

        try {
            setIsValidatingAll(true);
            setGlobalError(null);

            const response = await validateBatchRows(dataRef.current, startedBatchId);

            let okRows =
                response?.results
                    .filter((r) => r.ok && r.normalized)
                    .map((r) => ({ row_id: r.row_id, normalized: r.normalized! })) || [];

            if (!response) {
                okRows = dataRef.current
                    .filter((row) => rowHasData(row) && row._state === "OK" && row._normalized)
                    .map((row) => ({ row_id: row._rowId!, normalized: row._normalized! }));
            }

            if (okRows.length === 0) {
                setGlobalError(response ? "No hay filas válidas para confirmar." : "No hay filas para validar.");
                return;
            }

            setIsCommitting(true);
            const commitResp = await commitBatch({ batch_id: startedBatchId, rows: okRows });
            processCommitResults(commitResp.results);
        } catch (error: any) {
            console.error("❌ Error en commit batch:", error);
            setGlobalError(error?.response?.data?.message || "Error en commit batch");
        } finally {
            setIsValidatingAll(false);
            setIsCommitting(false);
        }
    }, [ensureBatchStarted, validateBatchRows]);

    // Procesar resultados de commit
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
                        _rowError: null,
                    };
                } else if (!result.ok) {
                    return {
                        ...row,
                        _state: "ERROR",
                        _cellErrors: result.errors || {},
                        _rowError: buildRowErrorSummary(result.errors) || "Error en commit",
                    };
                }
                return row;
            })
        );
    };

    // Editar celda
    const handleCellEdit = useCallback(
        async ([col, row]: Item, newValue: EditableGridCell): Promise<void> => {
            if (row >= data.length) return;

            await ensureBatchStarted();

            const columnDef = COLUMN_DEFINITIONS[col];
            const columnId = columnDef.id;
            const rowData = data[row];

            let value: any;
            
            if (newValue.kind === GridCellKind.Custom) {
                const customData = (newValue as any).data;
                if (customData?.kind === "date-picker-cell") {
                    value = formatDateToISO(customData.date);
                } else if (customData?.kind === "dropdown-cell") {
                    // Permitir borrar dropdown: valor vacío o null
                    const dropdownVal = customData.value;
                    value = (dropdownVal === "" || dropdownVal === null || dropdownVal === undefined) 
                        ? null 
                        : dropdownVal;
                } else {
                    value = customData?.value ?? customData;
                }
            } else if (newValue.kind === GridCellKind.Text) {
                value = newValue.data || null;
            } else if (newValue.kind === GridCellKind.Number) {
                value = newValue.data;
            } else {
                value = (newValue as any).data;
            }

            // Marcar fila como tocada y actualizar valor
            let updatedRow = { 
                ...rowData, 
                [columnId]: value, 
                _rowError: null,
                _touched: true, // Marcar que la fila ha sido editada
            };

            // Si la fila quedó vacía, limpiar errores/estado y pedir limpieza de batch
            if (!rowHasData(updatedRow)) {
                updatedRow = {
                    ...updatedRow,
                    _state: undefined,
                    _cellErrors: {},
                    _rowError: null,
                    _normalized: undefined,
                    _touched: false,
                };
            } else if (updatedRow._state === "OK") {
                // Si estaba OK y se edita, volver a pendiente
                updatedRow = {
                    ...updatedRow,
                    _state: "PENDIENTE",
                    _normalized: undefined,
                };
            }

            setData((prev) => {
                const newData = [...prev];
                newData[row] = updatedRow;
                return newData;
            });

            // Debounce validación - solo si la fila tiene datos
            const rowId = rowData._rowId;
            if (rowId && debounceRef.current[rowId] !== undefined) {
                clearTimeout(debounceRef.current[rowId]);
            }

            if (rowId) {
                debounceRef.current[rowId] = window.setTimeout(() => {
                    if (batchId) {
                        if (rowHasData(updatedRow)) {
                            handleValidateRow(updatedRow);
                        } else {
                            validateRow({
                                batch_id: batchId,
                                row_id: rowId,
                                row: {},
                            }).catch(() => {
                                // no-op: limpieza de batch
                            });
                        }
                    }
                }, 500);
            }

            if (batchId) {
                if (batchValidateRef.current) clearTimeout(batchValidateRef.current);
                batchValidateRef.current = window.setTimeout(() => {
                    validateBatchRows(dataRef.current);
                }, 900);
            }
        },
        [data, batchId, ensureBatchStarted, handleValidateRow, validateBatchRows]
    );

    const handleAddRow = () => {
        setData((prev) => [...prev, createEmptyRow()]);
    };

    // Columnas con estilos Neo-Brutalistas - iconos blancos
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
                        bgHeaderHovered: "#3a3d44",
                        textHeader: COLORS.white,
                        fgIconHeader: COLORS.white,
                        bgIconHeader: "transparent",
                    } : undefined,
                };
            }),
        []
    );

    // Contenido de celda con colores Neo-Brutalistas
    const getCellContent = useCallback(
        ([col, row]: Item): GridCell => {
            if (row >= data.length) {
                return { kind: GridCellKind.Text, data: "", displayData: "", allowOverlay: true };
            }

            const rowData = data[row];
            const columnDef = COLUMN_DEFINITIONS[col];
            const columnId = columnDef.id;
            const cellType = (columnDef as any).cellType || "text";
            const value = rowData[columnId as keyof GridRow];
            const cellErrors = (rowData._cellErrors || {}) as Record<string, string>;
            const hasError = cellErrors[columnId] !== undefined;
            const rowState = rowData._state;
            const hasData = rowHasData(rowData);

            // Colores según estado - solo mostrar errores si la fila tiene datos
            let bgColor = COLORS.grayDark;
            let textColor = COLORS.white;
            
            if (hasData) {
            if (hasError) {
                bgColor = COLORS.errorLight;
                textColor = COLORS.errorText;
            } else if (rowState === "OK") {
                bgColor = COLORS.successLight;
                textColor = COLORS.successText;
            } else if (rowState === "PENDIENTE") {
                bgColor = COLORS.warningLight;
                textColor = COLORS.warningText;
            } else if (rowState === "VALIDANDO") {
                // Estado visual: validando (neutral, sin azul)
                bgColor = COLORS.grayMedium;
                textColor = COLORS.white;
            }
            }

            const themeOverride = { bgCell: bgColor, textDark: textColor };

            // Columna de error de fila - solo mostrar si tiene datos
            if (columnId === "_rowError") {
                const rowError = hasData ? (rowData._rowError || "") : "";
                return {
                    kind: GridCellKind.Text,
                    data: rowError,
                    displayData: rowError,
                    allowOverlay: false,
                    readonly: true,
                    themeOverride: rowError
                        ? { bgCell: COLORS.errorLight, textDark: COLORS.errorText }
                        : { bgCell: "#1A1C20", textDark: "#666666" },
                };
            }

            // Celda tipo DATE
            if (cellType === "date") {
                const { date, displayDate } = parseDateValue(value);
                
                return {
                    kind: GridCellKind.Custom,
                    allowOverlay: true,
                    copyData: displayDate,
                    data: { kind: "date-picker-cell", date, displayDate, format: "date" as const },
                    themeOverride,
                } as any;
            }

            // Celda tipo DROPDOWN - opciones sin duplicados y con opción vacía
            if (cellType === "dropdown") {
                const options = getDropdownOptions(columnId, catalogs);
                const dropdownValue = value ? value.toString() : null;
                
                return {
                    kind: GridCellKind.Custom,
                    allowOverlay: true,
                    copyData: dropdownValue || "",
                    data: { 
                        kind: "dropdown-cell", 
                        allowedValues: options, 
                        value: dropdownValue,
                    },
                    themeOverride,
                } as any;
            }

            // Celda tipo TEXT
            const strValue = value?.toString() || "";
            const errorMsg = hasError ? (cellErrors[columnId] || "") : "";
            const displayData = errorMsg
                ? (strValue ? `${strValue} (${errorMsg})` : errorMsg)
                : strValue;
            return {
                kind: GridCellKind.Text,
                data: strValue,
                displayData: displayData,
                allowOverlay: true,
                themeOverride,
            };
        },
        [data, catalogs]
    );

    const handleCellClicked = useCallback(() => {
        void ensureBatchStarted();
    }, [ensureBatchStarted]);

    const handleFinishedEditing = useCallback(
        (_newValue: GridCell | undefined, [col, row]: Item) => {
            if (row === data.length - 1 && col === COLUMN_DEFINITIONS.length - 1) {
                setTimeout(() => handleAddRow(), 100);
            }
        },
        [data]
    );

    const onRowAppended = useCallback(() => handleAddRow(), []);

    // Contadores - solo contar filas con datos
    const rowsWithData = data.filter(rowHasData);
    const okCount = rowsWithData.filter((r) => r._state === "OK").length;
    const errorCount = rowsWithData.filter((r) => r._state === "ERROR").length;
    const pendingCount = rowsWithData.filter((r) => r._state === "PENDIENTE").length;
    const validatingCount = rowsWithData.filter((r) => r._state === "VALIDANDO").length;
    const rowErrorText = data
        .map((row, index) => {
            if (!rowHasData(row) || !row._rowError) return null;
            return `Fila ${index + 1}: ${row._rowError}`;
        })
        .filter(Boolean)
        .filter((value, idx, arr) => arr.indexOf(value) === idx)
        .join(" | ") || null;

    // Altura dinámica
    const tableHeight = useMemo(() => calculateTableHeight(data.length), [data.length]);

    return (
        <Box sx={containerStyles}>
            <Box sx={wrapperStyles}>
                <Typography sx={titleStyles}>
                    Carga de Actuaciones
                </Typography>

                {globalError && (
                    <Alert severity="error" onClose={() => setGlobalError(null)} sx={alertBaseStyles}>
                        {globalError}
                    </Alert>
                )}

                {!batchId && (
                    <Alert severity="warning" sx={alertBaseStyles}>
                        <strong>💡 TIP:</strong> Empieza a cargar datos directamente. El batch se iniciará automáticamente al editar la primera celda.
                    </Alert>
                )}

                {batchId && (
                    <Alert severity="success" sx={alertBaseStyles}>
                        <strong>BATCH ACTIVO:</strong> {batchId.slice(0, 13)}...
                        {okCount > 0 && (
                            <span style={{ color: COLORS.successText, fontWeight: 700, marginLeft: 8 }}>
                                {okCount} OK
                            </span>
                        )}
                        {errorCount > 0 && (
                            <span style={{ color: COLORS.errorText, fontWeight: 700, marginLeft: 8 }}>
                                {errorCount} ERROR
                            </span>
                        )}
                        {validatingCount > 0 && (
                            <span style={{ color: COLORS.white, fontWeight: 700, marginLeft: 8 }}>
                                {validatingCount} Validando...
                            </span>
                        )}
                        {pendingCount > 0 && (
                            <span style={{ color: COLORS.warningText, fontWeight: 700, marginLeft: 8 }}>
                                {pendingCount} Pendiente
                            </span>
                        )}
                        {isLoadingBatch && <span style={{ marginLeft: 8 }}>⏳ Iniciando...</span>}
                        {isCommitting && <span style={{ marginLeft: 8 }}>💾 Guardando...</span>}
                        {rowErrorText && (
                            <div style={{ color: COLORS.errorText, textAlign: "center", marginTop: 8 }}>
                                {rowErrorText}
                            </div>
                        )}
                    </Alert>
                )}

                <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
                    <Button
                        variant="contained"
                        color="success"
                        onClick={handleCommitBatch}
                        disabled={isValidatingAll || isCommitting || rowsWithData.length === 0}
                        startIcon={(isValidatingAll || isCommitting) ? <CircularProgress size={16} /> : undefined}
                    >
                        Mandar todo (validar + confirmar)
                    </Button>
                </Box>

                <Box sx={{ ...gridContainerStyles, height: tableHeight }}>
                    <DataEditor
                        ref={gridRef}
                        getCellContent={getCellContent}
                        columns={columns}
                        rows={data.length}
                        onCellEdited={handleCellEdit}
                        onCellClicked={handleCellClicked}
                        onFinishedEditing={handleFinishedEditing}
                        onRowAppended={onRowAppended}
                        customRenderers={allCells}
                        theme={gridTheme}
                        smoothScrollX={true}
                        smoothScrollY={true}
                        rowMarkers="both"
                        rowHeight={GRID_DIMENSIONS.rowHeight}
                        headerHeight={GRID_DIMENSIONS.headerHeight}
                        overscrollY={0}
                        overscrollX={0}
                        trailingRowOptions={{
                            sticky: false,
                            tint: true,
                            hint: "Presiona Enter o haz clic para agregar fila...",
                        }}
                        getCellsForSelection={true}
                        freezeColumns={0}
                        keybindings={{ search: true }}
                        getGroupDetails={(groupName) => {
                            const config = GROUP_CONFIG[groupName as keyof typeof GROUP_CONFIG];
                            return config ? { 
                                name: groupName, 
                                icon: config.icon,
                                // Iconos de grupo blancos
                                overrideTheme: {
                                    bgIconHeader: "transparent",
                                    fgIconHeader: COLORS.white,
                                    textGroupHeader: COLORS.white,
                                },
                            } : { name: groupName };
                        }}
                        groupHeaderHeight={GRID_DIMENSIONS.groupHeaderHeight}
                    />
                </Box>

                <Box sx={legendStyles}>
                    <Typography sx={legendTitleStyles}>
                         CÓMO USAR:
                    </Typography>
                    <Typography sx={legendTextStyles} component="div">
                        <strong>1.</strong> Empieza a cargar datos: <strong>DOBLE CLICK</strong> en cualquier celda o presiona 
                        <span style={kbdStyles}>Enter</span> para editarla<br/>
                        <strong>2.</strong> Presiona <span style={kbdStyles}>Tab</span> para moverte entre celdas<br/>
                        <strong>3.</strong> Para agregar filas: presiona <span style={kbdStyles}>Enter</span> o haz clic en la fila inferior<br/>
                        <strong>4.</strong> La validación por fila es <strong>automática</strong> al editar<br/>
                        <strong>5.</strong> Para confirmar todo: usa el botón <strong>“Mandar todo”</strong><br/>
                        <strong>6.</strong> Para borrar un dropdown: selecciona la opción vacía al inicio de la lista<br/>
                        <br/>
                        <strong>COLORES:</strong>{" "}
                        <span style={getStatusBadgeStyles(COLORS.errorLight, COLORS.errorText)}>ERROR</span>
                        <span style={getStatusBadgeStyles(COLORS.successLight, COLORS.successText)}>OK</span>
                        <span style={getStatusBadgeStyles(COLORS.warningLight, COLORS.warningText)}>ADVERTENCIA</span>
                        <span style={getStatusBadgeStyles("#1E2127", COLORS.white)}>PENDIENTE</span>
                        <span style={getStatusBadgeStyles(COLORS.primary, COLORS.white)}>VALIDANDO</span>
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

export default TablaCargarActuacionesGlideStyled;
