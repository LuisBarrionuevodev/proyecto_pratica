/**
 * Componente principal de la tabla de carga de actuaciones
 * Orquesta los hooks y sub-componentes
 * 
 * Estilo: Neo-Brutalista con Tactic Sans (fuente pequeña)
 */

import { useCallback, useRef, useState, useEffect, useMemo } from "react";
import DataEditor, { 
    type GridCell, 
    type Item,
    type EditableGridCell,
    GridCellKind,
} from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import { allCells } from "@glideapps/glide-data-grid-cells";
import "@glideapps/glide-data-grid-cells/dist/index.css";
import { Box, Typography } from "@mui/material";

// Hooks
import { useCatalogs } from "../hooks/useCatalogs";
import { useBatchOperations } from "../hooks/useBatchOperations";

// Componentes
import { BatchAlerts } from "./BatchAlerts";
import { GridLegend } from "./GridLegend";

// Configuración
import { COLUMN_DEFINITIONS, getGridColumns, getColumnByIndex } from "../config/columnDefinitions";
import { getGroupDetails } from "../config/groupConfig";
import { getDropdownOptions } from "../config/dropdownOptions";

// Estilos
import {
    containerStyles,
    wrapperStyles,
    titleStyles,
    gridContainerStyles,
    gridTheme,
    GRID_DIMENSIONS,
    COLORS,
} from "../styles/cargarActuacionesStyles";

// Utils
import { 
    createEmptyRows, 
    createEmptyRow, 
    countRowsByState,
    parseDateValue,
    formatDateToISO,
} from "../utils/gridHelpers";

// Types
import type { GridRow } from "../../../api/gridApi";

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export function TablaCargarActuaciones() {
    // =========================================================================
    // REFS
    // =========================================================================
    const gridRef = useRef<any>(null);
    const debounceRef = useRef<Record<string, number>>({});

    // =========================================================================
    // ESTADO DE DATOS
    // =========================================================================
    const [data, setData] = useState<GridRow[]>(() => createEmptyRows(5));

    // =========================================================================
    // HOOKS
    // =========================================================================

    // Cargar catálogos del backend
    const catalogs = useCatalogs();

    // Operaciones de batch
    const batch = useBatchOperations(setData);

    // =========================================================================
    // CONTADORES
    // =========================================================================
    const counters = useMemo(() => countRowsByState(data), [data]);

    // =========================================================================
    // AGREGAR FILA
    // =========================================================================
    const addRow = useCallback(() => {
        const newRow = createEmptyRow();
        setData(prev => [...prev, newRow]);
    }, []);

    // =========================================================================
    // EDICIÓN DE CELDAS
    // =========================================================================
    const handleCellEdit = useCallback(
        async ([col, row]: Item, newValue: EditableGridCell): Promise<void> => {
            if (row >= data.length) return;

            // Auto-iniciar batch al editar
            await batch.ensureBatchStarted();

            const columnDef = getColumnByIndex(col);
            if (!columnDef) return;

            const columnId = columnDef.id;
            const rowData = data[row];

            // Extraer valor según tipo de celda
            let value: any;
            
            if (newValue.kind === GridCellKind.Custom) {
                const customData = (newValue as any).data;
                
                if (customData?.kind === "date-picker-cell") {
                    value = formatDateToISO(customData.date);
                } else if (customData?.kind === "dropdown-cell") {
                    value = customData.value ?? null;
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

            // Actualizar datos
            const updatedRow: GridRow = {
                ...rowData,
                [columnId]: value,
                _rowError: null,
            };

            setData(prev => {
                const newData = [...prev];
                newData[row] = updatedRow;
                return newData;
            });

            // Debounce validation
            const rowId = rowData._rowId;
            if (rowId && debounceRef.current[rowId] !== undefined) {
                clearTimeout(debounceRef.current[rowId]);
            }

            if (rowId && batch.batchId) {
                debounceRef.current[rowId] = window.setTimeout(() => {
                    batch.validateAndCommitRow(updatedRow);
                }, 500);
            }
        },
        [data, batch.ensureBatchStarted, batch.batchId, batch.validateAndCommitRow]
    );

    // =========================================================================
    // GET CELL CONTENT
    // =========================================================================
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
            const columnDef = getColumnByIndex(col);
            
            if (!columnDef) {
                return {
                    kind: GridCellKind.Text,
                    data: "",
                    displayData: "",
                    allowOverlay: true,
                };
            }

            const columnId = columnDef.id;
            const cellType = columnDef.cellType;
            const value = rowData[columnId as keyof GridRow];
            const cellErrors = (rowData._cellErrors || {}) as Record<string, string>;
            const hasError = cellErrors[columnId] !== undefined;
            const rowState = rowData._state;

            // Colores Neo-Brutalistas - Tabla OSCURA con texto BLANCO
            // Fondo oscuro alternado, texto blanco por defecto
            const isEvenRow = row % 2 === 0;
            let bgColor = isEvenRow ? COLORS.grayDark : "#1E2127";  // Filas alternadas oscuras
            let textColor = COLORS.white;  // Texto blanco por defecto
            
            if (hasError) {
                bgColor = "#5C2323";   // Rojo oscuro para error
                textColor = "#FF6B6B"; // Rojo claro para texto
            } else if (rowState === "OK") {
                bgColor = "#1E3D2F";   // Verde oscuro para OK
                textColor = "#4ADE80"; // Verde claro para texto
            } else if (rowState === "ERROR") {
                bgColor = "#3D2E1E";   // Naranja oscuro para advertencia
                textColor = "#FFB86C"; // Naranja claro para texto
            }

            const themeOverride = {
                bgCell: bgColor,
                textDark: textColor,
            };

            // Columna de error de fila - Oscura con texto de error
            if (columnId === "_rowError") {
                const rowError = rowData._rowError || "";
                return {
                    kind: GridCellKind.Text,
                    data: rowError,
                    displayData: rowError,
                    allowOverlay: false,
                    readonly: true,
                    themeOverride: rowError
                        ? { bgCell: "#5C2323", textDark: "#FF6B6B" }  // Rojo oscuro/claro
                        : { bgCell: "#1A1C20", textDark: "#666666" }, // Gris muy oscuro
                };
            }

            // Celda tipo DATE
            if (cellType === "date") {
                const { date, display } = parseDateValue(value);
                
                return {
                    kind: GridCellKind.Custom,
                    allowOverlay: true,
                    copyData: display,
                    data: {
                        kind: "date-picker-cell",
                        date,
                        displayDate: display,
                        format: "date" as const,
                    },
                    themeOverride,
                } as any;
            }

            // Celda tipo DROPDOWN
            if (cellType === "dropdown") {
                const options = getDropdownOptions(columnId, {
                    inspectores: catalogs.inspectores,
                    motivos: catalogs.motivos,
                    rubros: catalogs.rubros,
                });
                const dropdownValue = value ? String(value) : null;
                
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

            // Celda tipo TEXT (default)
            const strValue = value?.toString() || "";
            return {
                kind: GridCellKind.Text,
                data: strValue,
                displayData: strValue,
                allowOverlay: true,
                themeOverride,
            };
        },
        [data, catalogs.inspectores, catalogs.motivos, catalogs.rubros]
    );

    // =========================================================================
    // HANDLERS
    // =========================================================================

    const handleCellClicked = useCallback(() => {
        void batch.ensureBatchStarted();
    }, [batch.ensureBatchStarted]);

    const handleFinishedEditing = useCallback(
        (_newValue: GridCell | undefined, [col, row]: Item) => {
            const isLastRow = row === data.length - 1;
            const isLastColumn = col === COLUMN_DEFINITIONS.length - 1;

            if (isLastRow && isLastColumn) {
                setTimeout(() => addRow(), 100);
            }
        },
        [data.length, addRow]
    );

    const onRowAppended = useCallback(() => {
        addRow();
    }, [addRow]);

    // =========================================================================
    // CONFIGURACIÓN DE COLUMNAS
    // =========================================================================
    const columns = useMemo(() => getGridColumns(), []);

    // =========================================================================
    // ERROR COMBINADO
    // =========================================================================
    const combinedError = batch.error || catalogs.error;

    // =========================================================================
    // RENDER
    // =========================================================================
    return (
        <Box sx={containerStyles}>
            <Box sx={wrapperStyles}>
                {/* Título Neo-Brutalista */}
                <Typography sx={titleStyles}>
                    Carga de Actuaciones
                </Typography>

                {/* Alertas de estado */}
                <BatchAlerts
                    batchId={batch.batchId}
                    error={combinedError}
                    onCloseError={batch.clearError}
                    counters={counters}
                />

                {/* Grilla de datos - Altura dinámica basada en filas */}
                <Box sx={{
                    ...gridContainerStyles,
                    // Altura dinámica: header + groupHeader + (filas * rowHeight) + trailing row
                    height: Math.min(
                        GRID_DIMENSIONS.headerHeight + 
                        GRID_DIMENSIONS.groupHeaderHeight + 
                        (data.length * GRID_DIMENSIONS.rowHeight) + 
                        GRID_DIMENSIONS.rowHeight + 10, // +10 para padding
                        window.innerHeight - 380 // Máximo para no desbordar
                    ),
                }}>
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
                        groupHeaderHeight={GRID_DIMENSIONS.groupHeaderHeight}
                        overscrollY={0}
                        trailingRowOptions={{
                            sticky: true,
                            tint: true,
                            hint: "Presiona Enter o haz clic para agregar fila...",
                        }}
                        getCellsForSelection={true}
                        freezeColumns={0}
                        keybindings={{
                            search: true,
                        }}
                        getGroupDetails={getGroupDetails}
                    />
                </Box>

                {/* Leyenda de instrucciones */}
                <GridLegend />
            </Box>
        </Box>
    );
}

export default TablaCargarActuaciones;
