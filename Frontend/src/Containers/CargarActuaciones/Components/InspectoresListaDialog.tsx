import { useCallback, useEffect, useMemo, useState } from "react";
import {
    Autocomplete,
    Box,
    Button,
    Chip,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    TextField,
    Typography,
} from "@mui/material";

import { dedupeInspectoresPreserveOrder } from "../utils/inspectoresGridHelpers";

export type InspectoresListaDialogProps = {
    open: boolean;
    /** Nombres iniciales (orden conservado). */
    initialNames: string[];
    /** Catálogo desde GET /grid/catalogs/inspectores (solo nombres). */
    catalogNames: string[];
    onClose: () => void;
    /** Lista final deduplicada en orden. */
    onSave: (names: string[]) => void;
};

/**
 * Editor modal para la lista de inspectores de una fila (sin columnas fijas 1–3).
 * Solo permite valores presentes en el catálogo del backend.
 */
export function InspectoresListaDialog({
    open,
    initialNames,
    catalogNames,
    onClose,
    onSave,
}: InspectoresListaDialogProps) {
    const [selected, setSelected] = useState<string[]>([]);

    useEffect(() => {
        if (open) {
            setSelected(dedupeInspectoresPreserveOrder(initialNames));
        }
    }, [open, initialNames]);

    const options = useMemo(
        () => [...catalogNames].sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" })),
        [catalogNames]
    );

    const availableToAdd = useMemo(
        () => options.filter((o) => !selected.includes(o)),
        [options, selected]
    );

    const handleAdd = useCallback(
        (_: unknown, value: string | null) => {
            if (!value || selected.includes(value)) return;
            setSelected((prev) => dedupeInspectoresPreserveOrder([...prev, value]));
        },
        [selected]
    );

    const handleRemove = useCallback((name: string) => {
        setSelected((prev) => prev.filter((x) => x !== name));
    }, []);

    const handleSave = useCallback(() => {
        onSave(dedupeInspectoresPreserveOrder(selected));
    }, [onSave, selected]);

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>Inspectores</DialogTitle>
            <DialogContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    Elegí del catálogo. Podés sumar varios y quitar con la X. Doble clic en la celda de la
                    grilla para volver a abrir este editor.
                </Typography>
                <Autocomplete
                    options={availableToAdd}
                    value={null}
                    onChange={handleAdd}
                    renderInput={(params) => (
                        <TextField {...params} label="Agregar inspector" placeholder="Buscar…" size="small" />
                    )}
                    disabled={availableToAdd.length === 0}
                />
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 2, minHeight: 40 }}>
                    {selected.length === 0 ? (
                        <Typography variant="body2" color="text.disabled">
                            Ninguno seleccionado
                        </Typography>
                    ) : (
                        selected.map((name) => (
                            <Chip key={name} label={name} onDelete={() => handleRemove(name)} size="small" />
                        ))
                    )}
                </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
                <Button onClick={onClose}>Cancelar</Button>
                <Button variant="contained" onClick={handleSave}>
                    Guardar
                </Button>
            </DialogActions>
        </Dialog>
    );
}
