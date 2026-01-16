import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { allCells } from "@glideapps/glide-data-grid-cells";
import "@glideapps/glide-data-grid-cells/dist/index.css";
import { Box, Typography, Alert } from "@mui/material";
import {
    startBatch,
    validateRow,
    validateBatch,
    commitRow,
    commitBatch,
    type GridRow,
    fetchInspectores,
    fetchMotivos,
    fetchRubros,
} from "../../../api/gridApi";

// =============================================================================
// ESTILOS NEO-BRUTALISTAS - Paleta de colores y constantes de diseño
// =============================================================================

const COLORS = {
    primary: "#0166FF",
    black: "#000000",
    white: "#FFFFFF",
    grayDark: "#2B2E34",
    grayMedium: "#353535",
    grayLight: "#D9D9D9",
    grayLighter: "#F5F5F5",
    success: "#2D9F4B",
    successLight: "#1E3D2F",
    successText: "#6BFF6B",
    error: "#E53935",
    errorLight: "#5C2323",
    errorText: "#FF6B6B",
    warning: "#FF9800",
    warningLight: "#3D2E1E",
    warningText: "#FFD700",
    rowEven: "#2B2E34",
    rowOdd: "#1E2127",
    border: "#3a3d44",
};

// Removidas las sombras - usando solo bordes como en Actuaciones

// Estilos del contenedor principal
const containerStyles = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

// Estilos del wrapper
const wrapperStyles = {
    width: { xs: "280px", sm: "520px", md: "920px", lg: "920px", xl: "1220px" },
    display: "flex",
    position: "absolute" as const,
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "8%" },
    marginLeft: { xs: "90px", sm: "100px", md: "100px", lg: "120px", xl: "100px" },
    textAlign: "center" as const,
    justifySelf: "center",
    flexDirection: "column" as const,
};

// Título con sombra sutil
const titleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 800,
    fontSize: { xs: "22px", sm: "38px", md: "52px" },
    color: COLORS.white,
    textShadow: `2px 2px 4px rgba(0, 0, 0, 0.5)`,
    letterSpacing: "2px",
    marginBottom: "16px",
};

// Alertas con borde y sombra sutil (igual que Actuaciones)
const alertBaseStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    marginBottom: "16px",
    backgroundColor: COLORS.grayDark,
    color: COLORS.white,
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
    "& .MuiAlert-icon": { color: COLORS.white },
    "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
};

// Contenedor de la grilla - con borde y sombra sutil (igual que Actuaciones)
const gridContainerStyles = {
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    overflow: "hidden",
    boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
    backgroundImage: "linear-gradient(rgba(255, 255, 255, 0.069), rgba(255, 255, 255, 0.069))",
    backgroundColor: COLORS.grayDark,
};

// Leyenda con borde y sombra sutil (igual que Actuaciones)
const legendStyles = {
    marginTop: "16px",
    marginBottom: "8px",
    padding: "20px",
    backgroundColor: COLORS.grayDark,
    borderRadius: "8px",
    border: `1px solid #1A1C20`,
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
};

const legendTitleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "16px",
    marginBottom: "12px",
    color: COLORS.white,
};

const legendTextStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 400,
    fontSize: "14px",
    color: COLORS.white,
    lineHeight: 1.8,
};

const kbdStyles: React.CSSProperties = {
    padding: "3px 8px",
    backgroundColor: "#1A1C20",
    border: `1px solid #555`,
    borderRadius: "4px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    boxShadow: "1px 1px 0 #000",
    display: "inline-block",
    marginLeft: "4px",
    marginRight: "4px",
    color: COLORS.white,
};

const getStatusBadgeStyles = (bgColor: string, textColor: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "2px 8px",
    backgroundColor: bgColor,
    color: textColor,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "4px",
    marginRight: "8px",
    fontWeight: 600,
});

// =============================================================================
// GENERADOR DE IDs ÚNICOS
// =============================================================================
const generateRowId = (() => {
    let counter = 0;
    return () => `row_${Date.now()}_${counter++}`;
})();

// =============================================================================
// OPCIONES DE DROPDOWNS
// =============================================================================
const DROPDOWN_ENUMS = {
    "Tipo actuación": [
        "INSPECCION",
        "REINSPECCION",
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
        "TRANSPORTE",
    ],
    "Contraproducencia": [
        "LOCAL CERRADO",
        "NO EXISTE/NO ES EL RUBRO",
        "CLIMA",
        "ZONA ROJA",
        "NO_HUBO",
        "OTROS",
    ],
};

const COMPROBACION_MOTIVOS = [
    "Falta de Higiene",
    "Condiciones Edilicias Inadecuadas",
    "No Permite la Inspección",
    "Incumplimiento",
    "Incumplimiento de Notificación",
    "Sin Certificado de Desinfección",
    "Sin Carnet de Sanidad",
    "Sin Certificado de Sanidad",
    "Mercadería Vencida",
    "Productos Sin Rotulación",
];

// =============================================================================
// CONFIGURACIÓN DE GRUPOS
// =============================================================================
const GROUP_CONFIG = {
    "Actuación": { icon: GridColumnIcon.HeaderArray, color: COLORS.grayDark },
    "Inspectores": { icon: GridColumnIcon.HeaderCode, color: COLORS.grayDark },
    "Establecimiento": { icon: GridColumnIcon.HeaderUri, color: COLORS.grayDark },
    "Actas": { icon: GridColumnIcon.HeaderString, color: COLORS.grayDark },
    "Reinspección": { icon: GridColumnIcon.HeaderReference, color: COLORS.grayDark },
    "Expediente": { icon: GridColumnIcon.HeaderMarkdown, color: COLORS.grayDark },
};

// =============================================================================
// DEFINICIÓN DE COLUMNAS
// =============================================================================
const COLUMN_DEFINITIONS = [
    { id: "_rowError", title: "Errores fila", width: 260, editable: false, group: "Actuación", icon: GridColumnIcon.HeaderString, cellType: "rowError" },
    { id: "Fecha actuación", title: "Fecha actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderDate, cellType: "date" },
    { id: "Tipo actuación", title: "Tipo actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Contraproducencia", title: "Contraproducencia", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Orden de trabajo", title: "Orden de trabajo", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Inspector 1", title: "Inspector 1", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Inspector 2", title: "Inspector 2", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Inspector 3", title: "Inspector 3", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Calle", title: "Calle", width: 200, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "Número", title: "Número", width: 100, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Rubro", title: "Rubro", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Apellido", title: "Apellido", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "Nombre", title: "Nombre", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "DNI", title: "DNI", width: 120, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta inspección", title: "Acta inspección", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta notificación", title: "Acta notificación", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Motivo notif 1", title: "Motivo notif 1", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Motivo notif 2", title: "Motivo notif 2", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Motivo notif 3", title: "Motivo notif 3", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Acta comprobación", title: "Acta comprobación", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Motivo comprobación", title: "Motivo comprobación", width: 180, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Acta clausura", title: "Acta clausura", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta decomiso", title: "Acta decomiso", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Kilos decomiso", title: "Kilos decomiso", width: 120, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta notificación previa", title: "Acta notificación previa", width: 180, editable: true, group: "Reinspección", icon: GridColumnIcon.HeaderReference, cellType: "text" },
    { id: "Acta comprobación previa", title: "Acta comprobación previa", width: 180, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Expediente año", title: "Expediente año", width: 130, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderDate, cellType: "text" },
    { id: "Expediente número", title: "Expediente número", width: 150, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Oficio año", title: "Oficio año", width: 120, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderDate, cellType: "text" },
    { id: "Oficio número", title: "Oficio número", width: 130, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Oficio causa", title: "Oficio causa", width: 120, editable: true, group: "Expediente", icon: GridColumnIcon.HeaderString, cellType: "text" },
];

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================
const TablaCargarActuacionesGlideStyled = () => {
    // Estado inicial con 5 filas vacías
    const initialRows = useMemo(() => {
        return Array.from({ length: 5 }, () => ({
            _rowId: generateRowId(),
            _state: "PENDIENTE" as const,
            _cellErrors: {},
        }));
    }, []);

    // Estados
    const [batchId, setBatchId] = useState<string | null>(null);
    const [data, setData] = useState<GridRow[]>(initialRows);
    const [isLoadingBatch, setIsLoadingBatch] = useState(false);
    const [isCommitting, setIsCommitting] = useState(false);
    const [globalError, setGlobalError] = useState<string | null>(null);
    const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
    const [catalogMotivos, setCatalogMotivos] = useState<string[]>([]);
    const [catalogRubros, setCatalogRubros] = useState<string[]>([]);

    // Referencias
    const gridRef = useRef<any>(null);
    const debounceRef = useRef<Record<string, number>>({});
    const dataRef = useRef<GridRow[]>(initialRows);
    const batchValidateRef = useRef<number | undefined>(undefined);
    const startingBatchRef = useRef<boolean>(false);

    // Auto-iniciar batch
    const ensureBatchStarted = useCallback(async () => {
        if (batchId || startingBatchRef.current) return;
        startingBatchRef.current = true;
        try {
            setIsLoadingBatch(true);
            setGlobalError(null);
            const response = await startBatch();
            setBatchId(response.batch_id);
            console.log("✅ Batch iniciado (auto):", response.batch_id);
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            setGlobalError(error?.response?.data?.message || error?.message || "Error al iniciar batch");
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
                const [inspectoresResp, motivosResp, rubrosResp] = await Promise.all([
                    fetchInspectores(),
                    fetchMotivos(),
                    fetchRubros(),
                ]);
                setCatalogInspectores(inspectoresResp.items.map((i) => i.nombre));
                setCatalogMotivos(motivosResp.items.map((m) => m.nombre));
                setCatalogRubros(rubrosResp.items.map((r) => r.nombre));
            } catch (error: any) {
                console.error("❌ Error cargando catálogos:", error);
                setGlobalError("Error cargando catálogos (inspectores/motivos/rubros).");
            }
        };
        loadCatalogs();
    }, []);

    // Validar batch de filas
    const validateBatchRows = useCallback(async (rows: GridRow[]) => {
        if (!batchId) return;
        
        const rowsToValidate = rows.map((row) => ({
            row_id: row._rowId!,
            row: extractDataColumns(row),
        }));

        const response = await validateBatch({
            batch_id: batchId,
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
                    _rowError: result.errors?._row || result.errors?.detail || null,
                    _normalized: result.normalized,
                };
            })
        );

        // Auto-confirmar filas OK
        const okRows = response.results
            .filter((r) => r.ok && r.normalized)
            .map((r) => ({ row_id: r.row_id, normalized: r.normalized! }));

        if (okRows.length > 0) {
            try {
                setIsCommitting(true);
                const commitResp = await commitBatch({ batch_id: batchId, rows: okRows });
                processCommitResults(commitResp.results);
            } catch (error: any) {
                console.error("❌ Error en commit batch automático:", error);
            } finally {
                setIsCommitting(false);
            }
        }
    }, [batchId]);

    // Validar fila individual
    const handleValidateRow = useCallback(async (row: GridRow) => {
        if (!batchId) return;

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
                              _rowError: response.errors?._row || response.errors?.detail || null,
                              _normalized: response.normalized,
                          }
                        : r
                )
            );

            // Auto-confirmar si OK
            if (response.ok && response.normalized) {
                try {
                    setIsCommitting(true);
                    const commitResp = await commitRow({
                        batch_id: batchId,
                        row_id: row._rowId!,
                        normalized: response.normalized,
                    });
                    processCommitResults([commitResp]);
                } catch (error: any) {
                    console.error("❌ Error en commit automático:", error);
                } finally {
                    setIsCommitting(false);
                }
            }
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
                        _rowError: result.errors?.detail || result.errors?._row || "Error en commit",
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
                    const date = customData.date;
                    value = date && !isNaN(date.getTime()) ? date.toISOString().split('T')[0] : null;
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

            const updatedRow = { ...rowData, [columnId]: value, _rowError: null };

            setData((prev) => {
                const newData = [...prev];
                newData[row] = updatedRow;
                return newData;
            });

            // Debounce validación
            const rowId = rowData._rowId;
            if (rowId && debounceRef.current[rowId] !== undefined) {
                clearTimeout(debounceRef.current[rowId]);
            }

            if (rowId) {
                debounceRef.current[rowId] = window.setTimeout(() => {
                    if (batchId) handleValidateRow(updatedRow);
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

    // Helpers
    const extractDataColumns = (row: GridRow): GridRow => {
        const { _rowId, _state, _cellErrors, _rowError, _normalized, _validation_history, ...dataColumns } = row;
        return dataColumns;
    };

    const handleAddRow = () => {
        const rowId = generateRowId();
        setData((prev) => [...prev, { _rowId: rowId, _state: "PENDIENTE", _cellErrors: {} }]);
    };

    // Columnas con estilos Neo-Brutalistas
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

            // Colores según estado
            let bgColor = COLORS.grayDark;
            let textColor = COLORS.white;
            
            if (hasError) {
                bgColor = COLORS.errorLight;
                textColor = COLORS.errorText;
            } else if (rowState === "OK") {
                bgColor = COLORS.successLight;
                textColor = COLORS.successText;
            } else if (rowState === "ERROR") {
                bgColor = COLORS.warningLight;
                textColor = COLORS.warningText;
            }

            const themeOverride = { bgCell: bgColor, textDark: textColor };

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
                        ? { bgCell: COLORS.errorLight, textDark: COLORS.errorText }
                        : { bgCell: "#1A1C20", textDark: "#666666" },
                };
            }

            // Celda tipo DATE
            if (cellType === "date") {
                let dateValue: Date | null = null;
                let displayDate = "";
                
                if (value) {
                    try {
                        dateValue = new Date(value as string);
                        if (!isNaN(dateValue.getTime())) {
                            displayDate = dateValue.toISOString().split('T')[0];
                        } else {
                            dateValue = null;
                            displayDate = value.toString();
                        }
                    } catch {
                        dateValue = null;
                        displayDate = value.toString();
                    }
                }
                
                return {
                    kind: GridCellKind.Custom,
                    allowOverlay: true,
                    copyData: displayDate,
                    data: { kind: "date-picker-cell", date: dateValue, displayDate, format: "date" as const },
                    themeOverride,
                } as any;
            }

            // Celda tipo DROPDOWN
            if (cellType === "dropdown") {
                const enumOptions = (DROPDOWN_ENUMS as any)[columnId] || [];
                const isInspector = columnId.startsWith("Inspector");
                const isMotivoNotif = columnId.startsWith("Motivo notif");
                const isMotivoComprobacion = columnId === "Motivo comprobación";
                const isRubro = columnId === "Rubro";

                const options = enumOptions.length > 0
                    ? enumOptions
                    : isMotivoComprobacion
                        ? COMPROBACION_MOTIVOS
                        : isInspector
                            ? catalogInspectores
                            : isMotivoNotif
                                ? catalogMotivos
                                : isRubro
                                    ? catalogRubros
                                    : [];
                                    
                const dropdownValue = value ? value.toString() : null;
                
                return {
                    kind: GridCellKind.Custom,
                    allowOverlay: true,
                    copyData: dropdownValue || "",
                    data: { kind: "dropdown-cell", allowedValues: options, value: dropdownValue },
                    themeOverride,
                } as any;
            }

            // Celda tipo TEXT
            const strValue = value?.toString() || "";
            return {
                kind: GridCellKind.Text,
                data: strValue,
                displayData: strValue,
                allowOverlay: true,
                themeOverride,
            };
        },
        [data, catalogInspectores, catalogMotivos, catalogRubros]
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

    // Tema Neo-Brutalista oscuro
    const customTheme = useMemo<Partial<Theme>>(
        () => ({
            accentColor: COLORS.primary,
            accentLight: "#4D94FF",
            textDark: COLORS.white,
            textMedium: "#CCCCCC",
            textLight: "#999999",
            textBubble: COLORS.white,
            textHeader: COLORS.white,
            textGroupHeader: COLORS.white,
            bgIconHeader: COLORS.primary,
            fgIconHeader: COLORS.white,
            textHeaderSelected: COLORS.primary,
            bgCell: COLORS.grayDark,
            bgCellMedium: COLORS.rowOdd,
            bgHeader: COLORS.grayDark,
            bgHeaderHasFocus: "#3a3d44",
            bgHeaderHovered: "#3a3d44",
            bgBubble: COLORS.grayDark,
            bgBubbleSelected: COLORS.primary,
            bgSearchResult: COLORS.warningLight,
            borderColor: COLORS.border,
            horizontalBorderColor: COLORS.border,
            drilldownBorder: COLORS.primary,
            linkColor: COLORS.primary,
            headerFontStyle: "600 12px",
            baseFontStyle: "11px",
            fontFamily: '"Tactic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        }),
        []
    );

    // Contadores
    const okCount = data.filter((r) => r._state === "OK").length;
    const errorCount = data.filter((r) => r._state === "ERROR").length;
    const pendingCount = data.filter((r) => r._state === "PENDIENTE").length;

    // Altura dinámica - ajustada al contenido real sin espacio extra
    const tableHeight = useMemo(() => {
        const rowHeight = 36;
        const headerHeight = 42;
        const groupHeaderHeight = 36;
        const trailingRowHeight = 36; // Fila para agregar nueva
        
        // Altura exacta del contenido visible
        const contentHeight = 
            groupHeaderHeight + 
            headerHeight + 
            (data.length * rowHeight) + 
            trailingRowHeight;
        
        const minHeight = 400;
        const maxHeight = window.innerHeight - 280;
        
        return Math.min(Math.max(contentHeight, minHeight), maxHeight);
    }, [data.length]);

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
                        <strong>BATCH ACTIVO:</strong> {batchId.slice(0, 13)}... | 
                        <span style={{ color: COLORS.successText, fontWeight: 700, marginLeft: 8 }}>{okCount} OK</span> | 
                        <span style={{ color: COLORS.errorText, fontWeight: 700, marginLeft: 8 }}>{errorCount} ERROR</span> | 
                        <span style={{ color: COLORS.warningText, fontWeight: 700, marginLeft: 8 }}>{pendingCount} PENDIENTE</span>
                        {isLoadingBatch && <span style={{ marginLeft: 8 }}>⏳ Iniciando...</span>}
                        {isCommitting && <span style={{ marginLeft: 8 }}>💾 Guardando...</span>}
                    </Alert>
                )}

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
                        theme={customTheme}
                        smoothScrollX={true}
                        smoothScrollY={true}
                        rowMarkers="both"
                        rowHeight={36}
                        headerHeight={42}
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
                            return config ? { name: groupName, icon: config.icon } : { name: groupName };
                        }}
                        groupHeaderHeight={36}
                    />
                </Box>

                <Box sx={legendStyles}>
                    <Typography sx={legendTitleStyles}>
                        📝 CÓMO USAR:
                    </Typography>
                    <Typography sx={legendTextStyles} component="div">
                        <strong>1.</strong> Empieza a cargar datos: <strong>DOBLE CLICK</strong> en cualquier celda o presiona 
                        <span style={kbdStyles}>Enter</span> para editarla<br/>
                        <strong>2.</strong> Presiona <span style={kbdStyles}>Tab</span> para moverte entre celdas<br/>
                        <strong>3.</strong> Para agregar filas: presiona <span style={kbdStyles}>Enter</span> o haz clic en la fila inferior<br/>
                        <strong>4.</strong> La validación y guardado es <strong>automático</strong> al editar<br/>
                        <br/>
                        <strong>COLORES:</strong>{" "}
                        <span style={getStatusBadgeStyles(COLORS.errorLight, COLORS.errorText)}>ERROR</span>
                        <span style={getStatusBadgeStyles(COLORS.successLight, COLORS.successText)}>OK</span>
                        <span style={getStatusBadgeStyles(COLORS.warningLight, COLORS.warningText)}>ADVERTENCIA</span>
                        <span style={getStatusBadgeStyles("#1E2127", COLORS.white)}>PENDIENTE</span>
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

export default TablaCargarActuacionesGlideStyled;
