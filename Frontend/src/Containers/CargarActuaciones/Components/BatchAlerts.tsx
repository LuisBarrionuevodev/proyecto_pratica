/**
 * Componente de alertas para el estado del batch
 * Muestra: error global, tip inicial, estado activo con contadores
 */

import { Alert } from "@mui/material";
import {
    alertErrorStyles,
    alertWarningStyles,
    alertSuccessStyles,
    COLORS,
} from "../styles/cargarActuacionesStyles";

// =============================================================================
// TIPOS
// =============================================================================

interface BatchAlertsProps {
    /** ID del batch activo (null si no hay batch) */
    batchId: string | null;
    /** Mensaje de error global */
    error: string | null;
    /** Callback para cerrar error */
    onCloseError: () => void;
    /** Contadores de filas por estado */
    counters: {
        ok: number;
        error: number;
        pending: number;
        total: number;
    };
}

// =============================================================================
// COMPONENTE
// =============================================================================

/**
 * Alertas de estado del batch
 * - Error global (si existe)
 * - Tip inicial (si no hay batch)
 * - Estado activo con contadores (si hay batch)
 */
export function BatchAlerts({
    batchId,
    error,
    onCloseError,
    counters,
}: BatchAlertsProps) {
    return (
        <>
            {/* Alerta de error global */}
            {error && (
                <Alert 
                    severity="error" 
                    onClose={onCloseError} 
                    sx={alertErrorStyles}
                >
                    {error}
                </Alert>
            )}

            {/* Tip cuando no hay batch activo */}
            {!batchId && !error && (
                <Alert severity="warning" sx={alertWarningStyles}>
                    <strong>💡 TIP:</strong> Empieza a cargar datos directamente. 
                    El batch se iniciará automáticamente al editar la primera celda.
                </Alert>
            )}

            {/* Estado del batch activo con contadores */}
            {batchId && (
                <Alert severity="success" sx={alertSuccessStyles}>
                    <strong>BATCH ACTIVO:</strong> {batchId.slice(0, 13)}... | 
                    <span style={{ 
                        color: COLORS.success, 
                        fontWeight: 700, 
                        marginLeft: 8 
                    }}>
                        {counters.ok} OK
                    </span> | 
                    <span style={{ 
                        color: COLORS.error, 
                        fontWeight: 700, 
                        marginLeft: 8 
                    }}>
                        {counters.error} ERROR
                    </span> | 
                    <span style={{ 
                        color: COLORS.warning, 
                        fontWeight: 700, 
                        marginLeft: 8 
                    }}>
                        {counters.pending} PENDIENTE
                    </span>
                </Alert>
            )}
        </>
    );
}

export default BatchAlerts;
