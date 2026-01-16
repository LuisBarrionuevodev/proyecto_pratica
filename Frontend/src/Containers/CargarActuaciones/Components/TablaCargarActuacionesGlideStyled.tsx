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
import { Box, Typography, Button, Stack, Alert, CircularProgress } from "@mui/material";
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
// Basado en el sistema de diseño "Neo Amidst" con estética Neo-Brutalismo
// =============================================================================

// Paleta de colores Neo-Brutalista
const COLORS = {
    // Colores primarios
    primary: "#0166FF",          // Azul principal (acento)
    black: "#000000",            // Negro puro para bordes y sombras
    white: "#FFFFFF",            // Blanco puro para fondos
    
    // Grises
    grayDark: "#2B2E34",         // Gris oscuro (navbar)
    grayMedium: "#353535",       // Gris medio (bordes)
    grayLight: "#D9D9D9",        // Gris claro (inputs)
    grayLighter: "#F5F5F5",      // Gris muy claro (fondos secundarios)
    
    // Estados
    success: "#2D9F4B",          // Verde éxito
    successLight: "#E8F5E9",     // Verde claro fondo
    error: "#E53935",            // Rojo error
    errorLight: "#FFEBEE",       // Rojo claro fondo
    warning: "#FF9800",          // Naranja advertencia
    warningLight: "#FFF3E0",     // Naranja claro fondo
    
    // Grupos de columnas (tonos sólidos Neo-Brutalistas)
    groupBlue: "#B3D4FF",        // Azul pastel para grupo Actuación
    groupPurple: "#E1BEE7",      // Púrpura para grupo Inspectores
    groupOrange: "#FFE0B2",      // Naranja para grupo Establecimiento
    groupGreen: "#C8E6C9",       // Verde para grupo Actas
    groupYellow: "#FFF9C4",      // Amarillo para grupo Reinspección
    groupPink: "#F8BBD9",        // Rosa para grupo Expediente
};

// Estilos de sombras Neo-Brutalistas (sin blur, offset directo)
const SHADOWS = {
    hard: "6px 6px 0px #000000",
    hardSmall: "4px 4px 0px #000000",
    hardHover: "8px 8px 0px #000000",
    pressed: "2px 2px 0px #000000",
    none: "none",
};

// Estilos generales del contenedor principal
const containerStyles = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

// Estilos del wrapper principal con diseño Neo-Brutalista
const wrapperStyles = {
    width: { xs: "280px", sm: "520px", md: "920px", lg: "920px", xl: "1220px" },
    display: "flex",
    position: "absolute",
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "8%" },
    marginLeft: { xs: "90px", sm: "100px", md: "100px", lg: "120px", xl: "100px" },
    textAlign: "center",
    justifySelf: "center",
    flexDirection: "column",
    paddingBottom: "20px",
};

// Estilos del título con efecto Neo-Brutalista (stroke + shadow)
const titleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 800,
    fontSize: { xs: "22px", sm: "38px", md: "52px" },
    color: COLORS.white,
    textShadow: `
        -1px -1px 0 ${COLORS.black},
        1px -1px 0 ${COLORS.black},
        -1px 1px 0 ${COLORS.black},
        1px 1px 0 ${COLORS.black},
        3px 3px 0 ${COLORS.black}
    `,
    letterSpacing: "2px",
    marginBottom: "16px",
};

// Estilos de botones Neo-Brutalistas
// Basado en el estilo del LoginStyles.ts con sombras duras y transiciones
const buttonBaseStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "14px",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
    border: `2px solid ${COLORS.black}`,
    borderRadius: "8px",
    padding: "12px 24px",
    position: "relative" as const,
    transition: "all 0.15s ease-in-out",
    boxShadow: SHADOWS.hardSmall,
    minWidth: "180px",
    "&:hover": {
        transform: "translate(-2px, -2px)",
        boxShadow: SHADOWS.hard,
    },
    "&:active": {
        transform: "translate(2px, 2px)",
        boxShadow: SHADOWS.pressed,
    },
    "&:disabled": {
        opacity: 0.7,
        boxShadow: SHADOWS.none,
        transform: "none",
        cursor: "not-allowed",
    },
    // Asegurar que el texto sea visible en MUI
    "& .MuiButton-startIcon": {
        marginRight: "8px",
    },
};

// Variantes de botones con colores sólidos Neo-Brutalistas
const buttonPrimaryStyles = {
    ...buttonBaseStyles,
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    "&:hover": {
        ...buttonBaseStyles["&:hover"],
        backgroundColor: COLORS.primary,
        color: COLORS.white,
    },
    "&:disabled": {
        ...buttonBaseStyles["&:disabled"],
        backgroundColor: COLORS.grayLight,
        color: COLORS.grayMedium,
        border: `2px solid ${COLORS.grayMedium}`,
    },
};

const buttonSecondaryStyles = {
    ...buttonBaseStyles,
    backgroundColor: COLORS.white,
    color: COLORS.grayDark,
    "&:hover": {
        ...buttonBaseStyles["&:hover"],
        backgroundColor: COLORS.grayLighter,
        color: COLORS.grayDark,
    },
    "&:disabled": {
        ...buttonBaseStyles["&:disabled"],
        backgroundColor: COLORS.grayLighter,
        color: COLORS.grayMedium,
        border: `2px solid ${COLORS.grayMedium}`,
    },
};

const buttonSuccessStyles = {
    ...buttonBaseStyles,
    backgroundColor: COLORS.success,
    color: COLORS.white,
    "&:hover": {
        ...buttonBaseStyles["&:hover"],
        backgroundColor: COLORS.success,
        color: COLORS.white,
    },
    "&:disabled": {
        ...buttonBaseStyles["&:disabled"],
        backgroundColor: COLORS.grayLight,
        color: COLORS.grayMedium,
        border: `2px solid ${COLORS.grayMedium}`,
    },
};

// Estilos de alertas Neo-Brutalistas
const alertBaseStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    border: `2px solid ${COLORS.black}`,
    borderRadius: "8px",
    boxShadow: SHADOWS.hardSmall,
    marginBottom: "16px",
    "& .MuiAlert-message": {
        fontFamily: '"Tactic Sans", sans-serif',
        fontWeight: 400,
    },
    "& .MuiAlert-icon": {
        alignItems: "center",
    },
};

const alertErrorStyles = {
    ...alertBaseStyles,
    backgroundColor: COLORS.errorLight,
    color: COLORS.error,
    "& .MuiAlert-icon": {
        color: COLORS.error,
    },
};

const alertWarningStyles = {
    ...alertBaseStyles,
    backgroundColor: COLORS.warningLight,
    color: COLORS.grayDark,
    "& .MuiAlert-icon": {
        color: COLORS.warning,
    },
};

const alertSuccessStyles = {
    ...alertBaseStyles,
    backgroundColor: COLORS.successLight,
    color: COLORS.grayDark,
    "& .MuiAlert-icon": {
        color: COLORS.success,
    },
};

// Estilos del contenedor de la grilla Neo-Brutalista
const gridContainerStyles = {
    height: "calc(100vh - 380px)",
    minHeight: "480px",
    border: `3px solid ${COLORS.black}`,
    borderRadius: "12px",
    overflow: "hidden",
    boxShadow: SHADOWS.hard,
    backgroundColor: COLORS.white,
};

// Estilos de la leyenda Neo-Brutalista
const legendStyles = {
    marginTop: "20px",
    padding: "20px",
    backgroundColor: COLORS.grayLighter,
    borderRadius: "12px",
    border: `2px solid ${COLORS.black}`,
    boxShadow: SHADOWS.hardSmall,
};

const legendTitleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "16px",
    marginBottom: "12px",
    color: COLORS.grayDark,
};

const legendTextStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 400,
    fontSize: "14px",
    color: COLORS.grayDark,
    lineHeight: 1.8,
};

// Estilos para las teclas en la leyenda
const kbdStyles = {
    padding: "3px 8px",
    backgroundColor: COLORS.white,
    border: `2px solid ${COLORS.black}`,
    borderRadius: "4px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    boxShadow: "2px 2px 0 #000",
    display: "inline-block",
    marginLeft: "4px",
    marginRight: "4px",
};

// =============================================================================
// GENERADOR DE IDs ÚNICOS
// =============================================================================
const generateRowId = (() => {
    let counter = 0;
    return () => `row_${Date.now()}_${counter++}`;
})();

// =============================================================================
// OPCIONES DE DROPDOWNS (Enums alineados al backend)
// =============================================================================

// Tipos de actuación disponibles
const DROPDOWN_ENUMS = {
    "Tipo actuación": [
        "INSPECCION",
        "REINSPECCION",
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
        "TRANSPORTE",
    ],
    // Tipos de contraproducencia
    "Contraproducencia": [
        "LOCAL CERRADO",
        "NO EXISTE/NO ES EL RUBRO",
        "CLIMA",
        "ZONA ROJA",
        "NO_HUBO",
        "OTROS",
    ],
};

// Motivos de comprobación disponibles
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
// CONFIGURACIÓN DE GRUPOS DE COLUMNAS (Diseño Neo-Brutalista)
// Cada grupo tiene un ícono y color distintivo con alto contraste
// =============================================================================
const GROUP_CONFIG = {
    "Actuación": {
        icon: GridColumnIcon.HeaderArray,
        color: COLORS.groupBlue,      // Azul pastel
    },
    "Inspectores": {
        icon: GridColumnIcon.HeaderCode,
        color: COLORS.groupPurple,    // Púrpura
    },
    "Establecimiento": {
        icon: GridColumnIcon.HeaderUri,
        color: COLORS.groupOrange,    // Naranja
    },
    "Actas": {
        icon: GridColumnIcon.HeaderString,
        color: COLORS.groupGreen,     // Verde
    },
    "Reinspección": {
        icon: GridColumnIcon.HeaderReference,
        color: COLORS.groupYellow,    // Amarillo
    },
    "Expediente": {
        icon: GridColumnIcon.HeaderMarkdown,
        color: COLORS.groupPink,      // Rosa
    },
};

// =============================================================================
// DEFINICIÓN DE COLUMNAS
// Estructura de la grilla organizada por dominios funcionales
// =============================================================================
const COLUMN_DEFINITIONS = [
    // Grupo: Actuación - Datos principales de la actuación
    { id: "_rowError", title: "Errores fila", width: 260, editable: false, group: "Actuación", icon: GridColumnIcon.HeaderString, cellType: "rowError" },
    { id: "Fecha actuación", title: "Fecha actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderDate, cellType: "date" },
    { id: "Tipo actuación", title: "Tipo actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Contraproducencia", title: "Contraproducencia", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Orden de trabajo", title: "Orden de trabajo", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    
    // Grupo: Inspectores - Personal asignado
    { id: "Inspector 1", title: "Inspector 1", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Inspector 2", title: "Inspector 2", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Inspector 3", title: "Inspector 3", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    
    // Grupo: Establecimiento - Datos del lugar y contribuyente
    { id: "Calle", title: "Calle", width: 200, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "Número", title: "Número", width: 100, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Rubro", title: "Rubro", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Apellido", title: "Apellido", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "Nombre", title: "Nombre", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "DNI", title: "DNI", width: 120, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    
    // Grupo: Actas - Documentos generados
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
    
    // Grupo: Reinspección - Referencia a actas previas
    { id: "Acta notificación previa", title: "Acta notificación previa", width: 180, editable: true, group: "Reinspección", icon: GridColumnIcon.HeaderReference, cellType: "text" },
    
    // Grupo: Expediente - Datos administrativos
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
    // =========================================================================
    // ESTADO INICIAL - Crear 5 filas vacías para carga inmediata
    // =========================================================================
    const initialRows = useMemo(() => {
        return Array.from({ length: 5 }, () => ({
            _rowId: generateRowId(),
            _state: "PENDIENTE" as const,
            _cellErrors: {},
        }));
    }, []);

    // =========================================================================
    // ESTADOS DEL COMPONENTE
    // =========================================================================
    const [batchId, setBatchId] = useState<string | null>(null);
    const [data, setData] = useState<GridRow[]>(initialRows);
    const [isLoadingBatch, setIsLoadingBatch] = useState(false);
    const [isValidatingAll, setIsValidatingAll] = useState(false);
    const [isCommitting, setIsCommitting] = useState(false);
    const [globalError, setGlobalError] = useState<string | null>(null);
    
    // Catálogos cargados desde el backend
    const [catalogInspectores, setCatalogInspectores] = useState<string[]>([]);
    const [catalogMotivos, setCatalogMotivos] = useState<string[]>([]);
    const [catalogRubros, setCatalogRubros] = useState<string[]>([]);

    // =========================================================================
    // REFERENCIAS
    // =========================================================================
    const gridRef = useRef<any>(null);
    const debounceRef = useRef<Record<string, number>>({});
    const dataRef = useRef<GridRow[]>(initialRows);
    const batchValidateRef = useRef<number | undefined>(undefined);
    const startingBatchRef = useRef<boolean>(false);

    // =========================================================================
    // OPERACIONES DE BATCH
    // =========================================================================

    // Auto-iniciar batch al primer foco/click (sin depender de botón)
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
            const errorMsg =
                error?.response?.data?.message ||
                error?.message ||
                "Error al iniciar batch. Verifica que el backend esté corriendo en http://localhost:5000";
            setGlobalError(errorMsg);
        } finally {
            setIsLoadingBatch(false);
            startingBatchRef.current = false;
        }
    }, [batchId]);

    // Mantener data actualizada en ref para batch validation
    useEffect(() => {
        dataRef.current = data;
    }, [data]);

    // Cargar catálogos desde el backend al montar componente
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

    // Iniciar batch manualmente (botón)
    const handleStartBatch = async () => {
        try {
            setIsLoadingBatch(true);
            setGlobalError(null);
            const response = await startBatch();
            setBatchId(response.batch_id);
            console.log("✅ Batch iniciado:", response.batch_id);
        } catch (error: any) {
            console.error("❌ Error al iniciar batch:", error);
            const errorMsg = error?.response?.data?.message || error?.message || "Error al iniciar batch. Verifica que el backend esté corriendo en http://localhost:5000";
            setGlobalError(errorMsg);
        } finally {
            setIsLoadingBatch(false);
        }
    };

    // Validar todas las filas del batch
    const validateBatchRows = async (rows: GridRow[]) => {
        if (!batchId) return;
        
        const rowsToValidate = rows.map((row) => ({
            row_id: row._rowId!,
            row: extractDataColumns(row),
        }));

        const response = await validateBatch({
            batch_id: batchId!,
            rows: rowsToValidate,
        });

        console.log("✅ Validación batch completada:", response);

        // Actualizar estado de cada fila con errores por celda y por fila
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

        // Auto-confirmar filas OK con normalized disponible
        const okRows = response.results
            .filter((r) => r.ok && r.normalized)
            .map((r) => ({ row_id: r.row_id, normalized: r.normalized! }));

        if (okRows.length > 0) {
            try {
                setIsCommitting(true);
                const commitResp = await commitBatch({ batch_id: batchId!, rows: okRows });
                processCommitResults(commitResp.results);
            } catch (error: any) {
                console.error("❌ Error en commit batch automático:", error);
                setGlobalError(error?.response?.data?.message || "Error en commit batch automático");
            } finally {
                setIsCommitting(false);
            }
        }
    };

    // Handler para validar todas las filas
    const handleValidateAll = async () => {
        if (!batchId) {
            setGlobalError("Debes iniciar un batch primero");
            return;
        }

        try {
            setIsValidatingAll(true);
            setGlobalError(null);
            await validateBatchRows(data);
        } catch (error: any) {
            console.error("❌ Error en validación batch:", error);
            setGlobalError(error?.response?.data?.message || "Error al validar batch");
        } finally {
            setIsValidatingAll(false);
        }
    };

    // Confirmar todas las filas válidas
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

    // Commit individual como fallback
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

    // Procesar resultados del commit
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

    // =========================================================================
    // VALIDACIÓN DE FILAS INDIVIDUALES
    // =========================================================================

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
                              _rowError: response.errors?._row || response.errors?.detail || null,
                              _normalized: response.normalized,
                          }
                        : r
                )
            );

            // Auto-confirmar fila si quedó OK
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
                    console.error("❌ Error en commit automático (fila):", error);
                    setGlobalError(error?.response?.data?.message || "Error en commit automático");
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
    };

    // =========================================================================
    // EDICIÓN DE CELDAS
    // =========================================================================

    const handleCellEdit = useCallback(
        async ([col, row]: Item, newValue: EditableGridCell): Promise<void> => {
            if (row >= data.length) return;

            // Auto-iniciar batch al editar
            await ensureBatchStarted();

            const columnDef = COLUMN_DEFINITIONS[col];
            const columnId = columnDef.id;
            const rowData = data[row];

            // Extraer valor según tipo de celda
            let value: any;
            
            if (newValue.kind === GridCellKind.Custom) {
                const customData = (newValue as any).data;
                
                // Date picker cell
                if (customData?.kind === "date-picker-cell") {
                    const date = customData.date;
                    value = date && !isNaN(date.getTime()) ? date.toISOString().split('T')[0] : null;
                }
                // Dropdown cell
                else if (customData?.kind === "dropdown-cell") {
                    value = customData.value !== undefined && customData.value !== null ? customData.value : null;
                }
                else {
                    value = customData?.value !== undefined ? customData.value : customData;
                }
            } else if (newValue.kind === GridCellKind.Text) {
                value = newValue.data || null;
            } else if (newValue.kind === GridCellKind.Number) {
                value = newValue.data;
            } else {
                value = (newValue as any).data;
            }

            // Actualizar datos y limpiar error de fila al editar
            const updatedRow = {
                ...rowData,
                [columnId]: value,
                _rowError: null,
            };

            setData((prev) => {
                const newData = [...prev];
                newData[row] = updatedRow;
                return newData;
            });

            // Debounce validation por fila
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

            // Debounce batch validation (útil para pegado masivo)
            if (batchId) {
                if (batchValidateRef.current) {
                    clearTimeout(batchValidateRef.current);
                }
                batchValidateRef.current = window.setTimeout(() => {
                    validateBatchRows(dataRef.current);
                }, 900);
            }
        },
        [data, batchId, ensureBatchStarted, validateBatchRows]
    );

    // =========================================================================
    // FUNCIONES AUXILIARES
    // =========================================================================

    // Extraer solo columnas de datos (sin metadatos internos)
    const extractDataColumns = (row: GridRow): GridRow => {
        const { _rowId, _state, _cellErrors, _rowError, _normalized, _validation_history, ...dataColumns } = row;
        return dataColumns;
    };

    // Agregar nueva fila vacía
    const handleAddRow = () => {
        const rowId = generateRowId();
        const newRow: GridRow = {
            _rowId: rowId,
            _state: "PENDIENTE",
            _cellErrors: {},
        };

        setData((prev) => [...prev, newRow]);
    };

    // =========================================================================
    // CONFIGURACIÓN DE GLIDE DATA GRID
    // =========================================================================

    // Definición de columnas con estilos Neo-Brutalistas por grupo
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
                    // Override de tema por grupo con colores Neo-Brutalistas
                    themeOverride: groupConfig ? {
                        bgHeader: groupConfig.color,
                        bgHeaderHovered: groupConfig.color,
                        textHeader: COLORS.grayDark,
                    } : undefined,
                };
            }),
        []
    );

    // Obtener contenido de celda con estilos Neo-Brutalistas
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
            const cellType = (columnDef as any).cellType || "text";
            const value = rowData[columnId as keyof GridRow];
            const cellErrors = (rowData._cellErrors || {}) as Record<string, string>;
            const hasError = cellErrors[columnId] !== undefined;
            const rowState = rowData._state;

            // Colores Neo-Brutalistas según estado y errores
            let bgColor = COLORS.white;
            let textColor = COLORS.grayDark;
            
            if (hasError) {
                // Celda con error específico - Rojo con alto contraste
                bgColor = COLORS.errorLight;
                textColor = COLORS.error;
            } else if (rowState === "OK") {
                // Fila validada OK - Verde sólido
                bgColor = COLORS.successLight;
                textColor = COLORS.success;
            } else if (rowState === "ERROR") {
                // Fila con error pero esta celda no tiene error específico - Amarillo advertencia
                bgColor = COLORS.warningLight;
                textColor = COLORS.warning;
            }

            const themeOverride = {
                bgCell: bgColor,
                textDark: textColor,
            };

            // Columna de error de fila (no editable) - Estilo Neo-Brutalista
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
                    } catch (e) {
                        dateValue = null;
                        displayDate = value.toString();
                    }
                }
                
                return {
                    kind: GridCellKind.Custom,
                    allowOverlay: true,
                    copyData: displayDate,
                    data: {
                        kind: "date-picker-cell",
                        date: dateValue,
                        displayDate: displayDate,
                        format: "date" as const,
                    },
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

                // Seleccionar opciones según tipo de columna
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
        [data, catalogInspectores, catalogMotivos, catalogRubros]
    );

    // Auto-iniciar batch al primer click en la grilla
    const handleCellClicked = useCallback(() => {
        void ensureBatchStarted();
    }, [ensureBatchStarted]);

    // Auto-crear fila al llegar al final con Tab
    const handleFinishedEditing = useCallback(
        (_newValue: GridCell | undefined, [col, row]: Item) => {
            const isLastRow = row === data.length - 1;
            const isLastColumn = col === COLUMN_DEFINITIONS.length - 1;

            if (isLastRow && isLastColumn) {
                setTimeout(() => {
                    handleAddRow();
                }, 100);
            }
        },
        [data]
    );

    // Callback para agregar fila al presionar Enter en trailing row
    const onRowAppended = useCallback(() => {
        handleAddRow();
    }, []);

    // =========================================================================
    // TEMA PERSONALIZADO NEO-BRUTALISTA PARA GLIDE DATA GRID
    // Alto contraste, bordes definidos, tipografía Tactic Sans
    // =========================================================================
    const customTheme = useMemo<Partial<Theme>>(
        () => ({
            // Colores de acento
            accentColor: COLORS.primary,
            accentLight: "#4D94FF",
            
            // Colores de texto con alto contraste
            textDark: COLORS.grayDark,
            textMedium: COLORS.grayMedium,
            textLight: "#757575",
            textBubble: COLORS.white,
            
            // Iconos de header
            bgIconHeader: COLORS.primary,
            fgIconHeader: COLORS.white,
            
            // Headers con estilo Neo-Brutalista
            textHeader: COLORS.grayDark,
            textHeaderSelected: COLORS.primary,
            
            // Celdas
            bgCell: COLORS.white,
            bgCellMedium: COLORS.grayLighter,
            
            // Headers
            bgHeader: COLORS.grayLight,
            bgHeaderHasFocus: "#BDBDBD",
            bgHeaderHovered: "#C9C9C9",
            
            // Burbujas y selección
            bgBubble: COLORS.grayLight,
            bgBubbleSelected: COLORS.primary,
            bgSearchResult: COLORS.warningLight,
            
            // Bordes más definidos para estética Neo-Brutalista
            borderColor: COLORS.grayMedium,
            drilldownBorder: COLORS.primary,
            
            // Links
            linkColor: COLORS.primary,
            
            // Tipografía Tactic Sans - Bold para headers, medium para contenido
            headerFontStyle: "700 14px",
            baseFontStyle: "500 13px",
            fontFamily: '"Tactic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        }),
        []
    );

    // =========================================================================
    // CONTADORES DE ESTADOS
    // =========================================================================
    const okCount = data.filter((r) => r._state === "OK").length;
    const errorCount = data.filter((r) => r._state === "ERROR").length;
    const pendingCount = data.filter((r) => r._state === "PENDIENTE").length;

    // =========================================================================
    // RENDER
    // =========================================================================
    return (
        <Box sx={containerStyles}>
            <Box sx={wrapperStyles}>
                {/* Título con estilo Neo-Brutalista (stroke + shadow) */}
                <Typography sx={titleStyles}>
                    Carga de Actuaciones
                </Typography>

                {/* Alerta de error global - Estilo Neo-Brutalista */}
                {globalError && (
                    <Alert 
                        severity="error" 
                        onClose={() => setGlobalError(null)} 
                        sx={alertErrorStyles}
                    >
                        {globalError}
                    </Alert>
                )}

                {/* Alerta de tip cuando no hay batch - Estilo Neo-Brutalista */}
                {!batchId && (
                    <Alert severity="warning" sx={alertWarningStyles}>
                        <strong>💡 TIP:</strong> Puedes empezar a cargar datos directamente. 
                        Haz click en "INICIAR BATCH" cuando estés listo para validar.
                    </Alert>
                )}

                {/* Alerta de batch activo con contadores - Estilo Neo-Brutalista */}
                {batchId && (
                    <Alert severity="success" sx={alertSuccessStyles}>
                        <strong>BATCH ACTIVO:</strong> {batchId.slice(0, 13)}... | 
                        <span style={{ color: COLORS.success, fontWeight: 700, marginLeft: 8 }}>
                            {okCount} OK
                        </span> | 
                        <span style={{ color: COLORS.error, fontWeight: 700, marginLeft: 8 }}>
                            {errorCount} ERROR
                        </span> | 
                        <span style={{ color: COLORS.warning, fontWeight: 700, marginLeft: 8 }}>
                            {pendingCount} PENDIENTE
                        </span>
                    </Alert>
                )}

                {/* Toolbar con botones Neo-Brutalistas */}
                <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
                    {/* Botón Iniciar Batch */}
                    <Button
                        variant="contained"
                        onClick={handleStartBatch}
                        disabled={isLoadingBatch || batchId !== null}
                        startIcon={isLoadingBatch ? <CircularProgress size={16} color="inherit" /> : undefined}
                        size="large"
                        sx={buttonPrimaryStyles}
                    >
                        {batchId ? "✓ BATCH ACTIVO" : "1. INICIAR BATCH"}
                    </Button>

                    {/* Botón Validar Todo */}
                    <Button
                        variant="outlined"
                        onClick={handleValidateAll}
                        disabled={!batchId || isValidatingAll || data.length === 0}
                        startIcon={isValidatingAll ? <CircularProgress size={16} color="inherit" /> : undefined}
                        size="large"
                        sx={buttonSecondaryStyles}
                    >
                        2. VALIDAR TODO ({data.length})
                    </Button>

                    {/* Botón Confirmar Carga */}
                    <Button
                        variant="contained"
                        onClick={handleCommitAll}
                        disabled={!batchId || isCommitting || okCount === 0}
                        startIcon={isCommitting ? <CircularProgress size={16} color="inherit" /> : undefined}
                        size="large"
                        sx={buttonSuccessStyles}
                    >
                        3. CONFIRMAR CARGA ({okCount})
                    </Button>
                </Stack>

                {/* Contenedor de la grilla con estilo Neo-Brutalista */}
                <Box sx={gridContainerStyles}>
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
                        rowHeight={42}
                        headerHeight={48}
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
                        getGroupDetails={(groupName) => {
                            const config = GROUP_CONFIG[groupName as keyof typeof GROUP_CONFIG];
                            return config ? {
                                name: groupName,
                                icon: config.icon,
                            } : {
                                name: groupName,
                            };
                        }}
                        groupHeaderHeight={40}
                    />
                </Box>

                {/* Leyenda con estilo Neo-Brutalista */}
                <Box sx={legendStyles}>
                    <Typography sx={legendTitleStyles}>
                        📝 CÓMO USAR:
                    </Typography>
                    <Typography sx={legendTextStyles} component="div">
                        <strong>1.</strong> Empieza a cargar datos: <strong>DOBLE CLICK</strong> en cualquier celda o presiona 
                        <span style={kbdStyles}>Enter</span> para editarla<br/>
                        <strong>2.</strong> Presiona <span style={kbdStyles}>Tab</span> para moverte entre celdas<br/>
                        <strong>3.</strong> Para agregar filas: presiona <span style={kbdStyles}>Enter</span> o haz clic en la fila inferior<br/>
                        <strong>4.</strong> Click en "INICIAR BATCH" cuando tengas datos cargados<br/>
                        <strong>5.</strong> Click en "VALIDAR TODO" para validar todas las filas<br/>
                        <strong>6.</strong> Click en "CONFIRMAR CARGA" para guardar en la base de datos<br/>
                        <br/>
                        <strong>COLORES:</strong>{" "}
                        <span style={{ 
                            display: "inline-block", 
                            padding: "2px 8px", 
                            backgroundColor: COLORS.errorLight, 
                            color: COLORS.error, 
                            border: `2px solid ${COLORS.black}`,
                            borderRadius: "4px",
                            marginRight: "8px",
                            fontWeight: 600,
                        }}>ERROR</span>
                        <span style={{ 
                            display: "inline-block", 
                            padding: "2px 8px", 
                            backgroundColor: COLORS.successLight, 
                            color: COLORS.success, 
                            border: `2px solid ${COLORS.black}`,
                            borderRadius: "4px",
                            marginRight: "8px",
                            fontWeight: 600,
                        }}>OK</span>
                        <span style={{ 
                            display: "inline-block", 
                            padding: "2px 8px", 
                            backgroundColor: COLORS.warningLight, 
                            color: COLORS.warning, 
                            border: `2px solid ${COLORS.black}`,
                            borderRadius: "4px",
                            marginRight: "8px",
                            fontWeight: 600,
                        }}>ADVERTENCIA</span>
                        <span style={{ 
                            display: "inline-block", 
                            padding: "2px 8px", 
                            backgroundColor: COLORS.white, 
                            color: COLORS.grayDark, 
                            border: `2px solid ${COLORS.black}`,
                            borderRadius: "4px",
                            fontWeight: 600,
                        }}>PENDIENTE</span>
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
};

export default TablaCargarActuacionesGlideStyled;
