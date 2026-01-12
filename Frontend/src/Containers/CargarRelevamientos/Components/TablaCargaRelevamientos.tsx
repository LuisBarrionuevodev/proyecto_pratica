import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_Row,
  type MRT_TableOptions,
} from "material-react-table";
import { Box, Typography } from "@mui/material";
import { useState } from "react";
import type { IRelevamiento } from "../../../types/relevamientos";
import { createRelevamiento } from "../../../api/relevamientosApi";
import { TABLE_CREAR_RELEVAMIENTOS } from "../../../constants/tableConfig";
import { TableGeneralStyles, TableTitleStyles } from "../../../styles/TablasStyle";
import { validateRelevamiento } from "../../../utils/validations";
import { TableButtonCreate } from "./TableButtonCreate";



const TablaCargaRelevamientos = () => {
  const [validationErrors, setValidationErrors] = useState<Record<string, string | undefined>>({});
  const [data, setData] = useState<IRelevamiento[]>([]);

  const validateRow = (row: MRT_Row<IRelevamiento>) => {
    setValidationErrors(validateRelevamiento(row._valuesCache));
  };


  const handleCreateNewRow: MRT_TableOptions<IRelevamiento>["onCreatingRowSave"] =
    async ({ values, table }) => {
      const errors = validateRelevamiento(values);
      if (Object.values(errors).some((e) => e)) {
        setValidationErrors(errors);
        return;
      }

      try {
        const nuevoRelevamiento = await createRelevamiento(values as IRelevamiento);

        table.setCreatingRow(null);
        setValidationErrors({});
        setData(prev => [...prev, nuevoRelevamiento]);
        setTimeout(() => {
          table.setCreatingRow(true);
        }, 50);

      } catch (error) {
        console.error("Error al crear relevamiento:", error);
      }
    };

  const columns: MRT_ColumnDef<IRelevamiento>[] = [
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
        onBlur: () => validateRow(row),
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
        onBlur: () => validateRow(row),
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
        onBlur: () => validateRow(row),
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
        onBlur: () => validateRow(row),
        onKeyDown: (e) => {
          if (e.key === "Enter") {
            table.options.onCreatingRowSave?.({
              values: row.getAllCells().reduce((acc, c) => {
                acc[c.column.id] = row._valuesCache[c.column.id];
                return acc;
              }, {} as any),
              table,
            } as any);
          }
        },
      }),
    },
  ];

  const table = useMaterialReactTable({
    ...TABLE_CREAR_RELEVAMIENTOS,
    columns,
    data: data,
    initialState: {
      columnVisibility: { id: false },
    },
    editDisplayMode: "row",
    enableEditing: true,
    onCreatingRowSave: handleCreateNewRow,
    renderTopToolbarCustomActions: ({ table }) => (
      <TableButtonCreate table={table} />
    ),
  });

  return (
    <Box sx={{ width: "100%" }}>
      <Box sx={{...TableGeneralStyles, }}>
        <Typography sx={TableTitleStyles}>Creación de relevamiento</Typography>
        <MaterialReactTable table={table} />
      </Box>
    </Box>
  );
};

export default TablaCargaRelevamientos;