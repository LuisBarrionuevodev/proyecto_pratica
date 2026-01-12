import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef, type MRT_Row, } from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { BASE_TABLE_CONFIG } from "../../../../../constants/tableConfig";
import type { IRelevamiento } from "../../../../../types/relevamientos";
import {
  TableGeneralStyles,
  TableLoadingStyles,
  TableTitleStyles,
} from "../../../../../styles/TablasStyle";
import { useRelevamientos } from "../../../../../hooks/useRelevamientos";
import { deleteRelevamiento, updateRelevamiento } from "../../../../../api/relevamientosApi";
import { TablaExportButtons } from "../../../Components/TableButtons";
import CardsExpedientes from "../../../Components/CardsExpedientes";
import { validateRelevamiento } from "../../../../../utils/validations";

const TablaRelevamientos = () => {

  const { relevamientos, setRelevamientos, loading } = useRelevamientos();
  const [validationErrors, setValidationErrors] = useState<Record<string, string | undefined>>({});
  const [data, setData] = useState<IRelevamiento[]>([]);

  const validateRow = (row: MRT_Row<IRelevamiento>) => {
    setValidationErrors(validateRelevamiento(row._valuesCache));
  };

  useEffect(() => {
    setData(relevamientos ?? []);
  }, [relevamientos]);

  const handleDeleteRow = useCallback(async (id: number) => {
    if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;
    const prev = data;
    setData(prev => prev.filter(item => item.id !== id));
    try {
      await deleteRelevamiento(id);
    } catch (error) {
      console.error("Error al eliminar:", error);
      alert("No se pudo eliminar el registro. Se restaurará la lista.");
      setData(prev);
      setRelevamientos(prev);
    }
  }, [data, setRelevamientos]);

  const handleEditCell = useCallback(
    async (id: number, key: keyof IRelevamiento, value: any) => {
      let updatedRow: IRelevamiento | undefined;
      setData((prev) => {
        const idx = prev.findIndex((r) => r.id === id);
        if (idx === -1) return prev;
        updatedRow = { ...prev[idx], [key]: value }; // guardamos fila actualizada
        const newData = [...prev];
        newData[idx] = updatedRow!;
        return newData;
      });

      if (!updatedRow) return;

      const payload: IRelevamiento = {
        id: updatedRow.id!,
        fecha: updatedRow.fecha.trim() || "",
        inspector: updatedRow.inspector?.trim() || "",
        direccion: updatedRow.direccion?.trim() || "",
        rubro: updatedRow.rubro,
      };

      //  Validación 
      if (!payload.rubro || !payload.direccion || !payload.fecha || !payload.inspector) {
        alert("Algunos campos no son válidos. Corrigelos antes de guardar.");
        return;
      }

      // Llamada Axios
      try {
        await updateRelevamiento(id, payload);
      } catch (error) {
        console.error("Error al actualizar:", error);
        alert("No se pudo actualizar el registro.");
      }
    },
    []
  );


  const columns = useMemo<MRT_ColumnDef<IRelevamiento>[]>(() => [
    {
      accessorKey: "id",
      header: "ID",
      enableEditing: false,
    },
    {
      accessorKey: "fecha",
      header: "Fecha",
      muiEditTextFieldProps: ({ cell, row }) => ({
        type: "date",
        autoFocus: cell.column.id === "fecha",
        error: !!validationErrors[cell.column.id],
        helperText: validationErrors[cell.column.id],
        onChange: (e) => {
          row._valuesCache[cell.column.id] = e.target.value;
        },
        onBlur: (e) => {
          validateRow(row);
          handleEditCell(row.original.id, "fecha", e.target.value);
        }
      }),
    },
    {
      accessorKey: "inspector",
      header: "Inspector",
      muiEditTextFieldProps: ({ cell, row }) => ({
        error: !!validationErrors[cell.column.id],
        helperText: validationErrors[cell.column.id],
        onChange: (e) => {
          row._valuesCache[cell.column.id] = e.target.value;
        },
        onBlur: (e) => {
          validateRow(row);
          handleEditCell(row.original.id, "inspector", e.target.value);
        }
      }),
    },
    {
      accessorKey: "direccion",
      header: "Dirección",
      muiEditTextFieldProps: ({ cell, row }) => ({
        error: !!validationErrors[cell.column.id],
        helperText: validationErrors[cell.column.id],
        onChange: (e) => {
          row._valuesCache[cell.column.id] = e.target.value;
        },
        onBlur: (e) => {
          validateRow(row);
          handleEditCell(row.original.id, "direccion", e.target.value);
        }
      }),
    },
    {
      accessorKey: "rubro",
      header: "Rubro",
      muiEditTextFieldProps: ({ cell, row }) => ({
        error: !!validationErrors[cell.column.id],
        helperText: validationErrors[cell.column.id],
        onChange: (e) => {
          row._valuesCache[cell.column.id] = e.target.value;
        },
        onBlur: (e) => {
          validateRow(row);
          handleEditCell(row.original.id, "rubro", e.target.value);
        },
      }),
    },
  ], [validationErrors])

  const table = useMaterialReactTable({
    ...BASE_TABLE_CONFIG,
    columns,
    data,
    enableRowActions: true,
    initialState: {
      columnVisibility: { id: false },
    },
    renderRowActions: ({ row }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title="Eliminar">
          <IconButton color="error" onClick={() => handleDeleteRow(Number(row.original.id))}>
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </Box>
    ),
    renderTopToolbarCustomActions: ({ table }) => (
      <TablaExportButtons data={data} table={table} />
    ),
  });

  if (loading) return <Typography sx={TableLoadingStyles}>Cargando relevamientos...</Typography>;

  return (
    <Box sx={{ width: "100%" }}>
      <Box
        sx={{
          ...TableGeneralStyles,
          "& .MuiBox-root.css-wsew38": {
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: 2,
          },
        }}
      >
        <Typography sx={TableTitleStyles}>Gestión de Relevamientos</Typography>
        <CardsExpedientes />
        <MaterialReactTable table={table} />
      </Box>
    </Box>
  );
};

export default TablaRelevamientos;