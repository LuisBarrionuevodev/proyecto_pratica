/**
 * Hook para manejo de datos de la grilla
 * Incluye: estado de datos, edición de celdas, getCellContent
 */

import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import {
    GridCellKind,
    type GridCell,
    type Item,
    type EditableGridCell,
} from "@glideapps/glide-data-grid";
import type { GridRow } from "../../../api/gridApi";
import { COLUMN_DEFINITIONS, getColumnByIndex } from "../config/columnDefinitions";
import { getDropdownOptions } from "../config/dropdownOptions";
import { COLORS } from "../styles/cargarActuacionesStyles";
import { 
    createEmptyRows, 
    createEmptyRow, 
    parseDateValue,
    formatDateToISO,
    countRowsByState,
} from "../utils/gridHelpers";

// =============================================================================
// TIPOS
// =============================================================================

interface UseGridDataOptions {
    initialRowCount?: number;
    catalogs: {
        inspectores: string[];
        motivos: string[];
        rubros: string[];
    };
    onCellEdit?: (row: GridRow) => void;
    batchId: string | null;
}

// =============================================================================
// HOOK
// =============================================================================

/**
 * Hook para manejar los datos de la grilla
 * Incluye: estado, edición, getCellContent, agregar filas
 */
export function useGridData({
    initialRowCount = 5,
    catalogs,
    onCellEdit,
    batchId,
}: UseGridDataOptions) {
    // Estado de datos
    const [data, setData] = useState<GridRow[]>(() => createEmptyRows(initialRowCount));
    
    // Referencias para debounce
    const debounceRef = useRef<Record<string, number>>({});
    const dataRef = useRef<GridRow[]>(data);
    const batchValidateRef = useRef<number | undefined>(undefined);

    // Mantener ref actualizada
    useEffect(() => {
        dataRef.current = data;
    }, [data]);

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

            const columnDef = getColumnByIndex(col);
            if (!columnDef) return;

            const columnId = columnDef.id;
            const rowData = data[row];

            // Extraer valor según tipo de celda
            let value: any;
            
            if (newValue.kind === GridCellKind.Custom) {
                const customData = (newValue as any).data;
                
                // Date picker cell
                if (customData?.kind === "date-picker-cell") {
                    value = formatDateToISO(customData.date);
                }
                // Dropdown cell
                else if (customData?.kind === "dropdown-cell") {
                    value = customData.value ?? null;
                }
                else {
                    value = customData?.value ?? customData;
                }
            } else if (newValue.kind === GridCellKind.Text) {
                value = newValue.data || null;
            } else if (newValue.kind === GridCellKind.Number) {
                value = newValue.data;
            } else {
                value = (newValue as any).data;
            }

            // Actualizar datos y limpiar error de fila al editar
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

            // Debounce validation por fila
            const rowId = rowData._rowId;
            if (rowId && debounceRef.current[rowId] !== undefined) {
                clearTimeout(debounceRef.current[rowId]);
            }

            if (rowId && onCellEdit) {
                debounceRef.current[rowId] = window.setTimeout(() => {
                    onCellEdit(updatedRow);
                }, 500);
            }
        },
        [data, onCellEdit]
    );

    // =========================================================================
    // GET CELL CONTENT
    // =========================================================================

    const getCellContent = useCallback(
        ([col, row]: Item): GridCell => {
            // Fila vacía
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

            // Colores Neo-Brutalistas según estado
            let bgColor = COLORS.white;
            let textColor = COLORS.grayDark;
            
            if (hasError) {
                bgColor = COLORS.errorLight;
                textColor = COLORS.error;
            } else if (rowState === "OK") {
                bgColor = COLORS.successLight;
                textColor = COLORS.success;
            } else if (rowState === "ERROR") {
                bgColor = COLORS.warningLight;
                textColor = COLORS.warning;
            }

            const themeOverride = {
                bgCell: bgColor,
                textDark: textColor,
            };

            // Columna de error de fila
            if (columnId === "_rowError") {
                const rowError = rowData._rowError || "";
                return {
                    kind: GridCellKind.Text,
                    data: rowError,
                    displayData: rowError,
                    allowOverlay: false,
                    readonly: true,
                    themeOverride: rowError
                        ? { bgCell: COLORS.errorLight, textDark: COLORS.error }
                        : { bgCell: COLORS.grayLighter, textDark: COLORS.grayMedium },
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
                const options = getDropdownOptions(columnId, catalogs);
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
        [data, catalogs]
    );

    // =========================================================================
    // HANDLERS DE NAVEGACIÓN
    // =========================================================================

    /**
     * Auto-crear fila al terminar de editar la última celda
     */
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

    /**
     * Callback para trailing row
     */
    const onRowAppended = useCallback(() => {
        addRow();
    }, [addRow]);

    // =========================================================================
    // RETURN
    // =========================================================================

    return {
        data,
        setData,
        dataRef,
        counters,
        addRow,
        handleCellEdit,
        getCellContent,
        handleFinishedEditing,
        onRowAppended,
    };
}

export default useGridData;
