import { Box, Typography, IconButton, Tooltip } from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef, } from "material-react-table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { BASE_TABLE_CONFIG } from "../../../constants/tableConfig";
import type { IActuacion } from "../../../types/actuaciones";
import {
  TableGeneralStyles,
  TableLoadingStyles,
  TableTitleStyles,
} from "../../../styles/TablasStyle";
import { useGestionActuaciones } from "../../../hooks/useGestionActuaciones";
import { deleteActuacion, updateActuacion } from "../../../api/actuacionesApi";
import { TablaExportButtons } from "./TableButtons";
import CardsExpedientes from "./CardsExpedientes";

const TablaActuaciones = () => {

  const { actuaciones, setActuaciones, loading } = useGestionActuaciones();
  const [data, setData] = useState<IActuacion[]>([]);
  const [validationErrors] = useState<Record<number, Record<string, string>>>({});

  useEffect(() => {
    setData(actuaciones ?? []);
  }, [actuaciones]);

  const handleDeleteRow = useCallback(async (id: number) => {
    if (!window.confirm("¿Estás seguro de eliminar este registro?")) return;
    const prev = data;
    setData(prev => prev.filter(item => item.id !== id));
    setActuaciones(prev => prev.filter(item => item.id !== id)); // si querés sync local
    try {
      await deleteActuacion(id);
    } catch (error) {
      console.error("Error al eliminar:", error);
      alert("No se pudo eliminar el registro. Se restaurará la lista.");
      setData(prev);
      setActuaciones(prev);
    }
  }, [data, setActuaciones]);

  const handleEditCell = useCallback(
    async (id: number, key: keyof IActuacion, value: any) => {
      let updatedRow: IActuacion | undefined;
      setData((prev) => {
        const idx = prev.findIndex((r) => r.id === id);
        if (idx === -1) return prev;
        updatedRow = { ...prev[idx], [key]: value }; // guardamos fila actualizada
        const newData = [...prev];
        newData[idx] = updatedRow!;
        return newData;
      });

      if (!updatedRow) return;

      const payload: IActuacion = {
        ...updatedRow,
      };

      //  Validación 
      if (!payload.rubro_nombre || !payload.calle || !payload.numero) {
        alert("Algunos campos no son válidos. Corrigelos antes de guardar.");
        return;
      }

      // Llamada Axios
      try {
        await updateActuacion(id, payload);
      } catch (error) {
        console.error("Error al actualizar:", error);
        alert("No se pudo actualizar el registro.");
      }
    },
    []
  );


  const columns = useMemo<MRT_ColumnDef<IActuacion>[]>(() => [
    {
      accessorKey: "id",
      header: "ID",
      enableHiding: true,
      enableEditing: false,
      enableClickToCopy: true,
    },
    {
      accessorKey: "orden_trabajo_numero",
      header: "OT",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.orden_trabajo_numero,
        helperText: validationErrors[row.original.id]?.orden_trabajo_numero,
        onBlur: (e) => handleEditCell(row.original.id, "orden_trabajo_numero", e.target.value),
      })
    },
    {
      accessorKey: "fecha_actuacion",
      header: "Fecha",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.fecha_actuacion,
        helperText: validationErrors[row.original.id]?.fecha_actuacion,
        onBlur: (e) => handleEditCell(row.original.id, "fecha_actuacion", e.target.value),
      })
    },
    {
      accessorKey: "rubro_nombre",
      header: "Rubro",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.rubro,
        helperText: validationErrors[row.original.id]?.rubro,
        onBlur: (e) => handleEditCell(row.original.id, "rubro_nombre", e.target.value),
      })
    },
    {
      accessorKey: "inspector1",
      header: "Inspector 1",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.inspector1,
        helperText: validationErrors[row.original.id]?.inspector1,
        onBlur: (e) => handleEditCell(row.original.id, "inspector1", e.target.value),
      }),
    },
    {
      accessorKey: "inspector2",
      header: "Inspector 2",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.inspector2,
        helperText: validationErrors[row.original.id]?.inspector2,
        onBlur: (e) => handleEditCell(row.original.id, "inspector2", e.target.value),
      }),
    },
    {
      accessorKey: "inspector3",
      header: "Inspector 3",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.inspector3,
        helperText: validationErrors[row.original.id]?.inspector3,
        onBlur: (e) => handleEditCell(row.original.id, "inspector3", e.target.value),
      }),
    },
    {
      accessorKey: "calle",
      header: "Calle",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.calle,
        helperText: validationErrors[row.original.id]?.calle,
        onBlur: (e) => handleEditCell(row.original.id, "calle", e.target.value),
      }),
    },
    {
      accessorKey: "numero",
      header: "Numero",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.numero,
        helperText: validationErrors[row.original.id]?.numero,
        onBlur: (e) => handleEditCell(row.original.id, "numero", e.target.value),
      }),
    },
    {
      accessorKey: "tipo_actuacion",
      header: "Tipo de Actuacion",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.tipo_actuacion,
        helperText: validationErrors[row.original.id]?.tipo_actuacion,
        onBlur: (e) => handleEditCell(row.original.id, "tipo_actuacion", e.target.value),
      }),
    },
    {
      accessorKey: "contraproducencia",
      header: "Contraproducencia",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.contraproducencia,
        helperText: validationErrors[row.original.id]?.contraproducencia,
        onBlur: (e) => handleEditCell(row.original.id, "contraproducencia", e.target.value),
      }),
    },
    {
      accessorKey: "doc_tipo_codigo",
      header: "Tipo de Documento",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.doc_tipo_codigo,
        helperText: validationErrors[row.original.id]?.doc_tipo_codigo,
        onBlur: (e) => handleEditCell(row.original.id, "doc_tipo_codigo", e.target.value),
      }),
    },
    {
      accessorKey: "doc_nro",
      header: "Numero de Documento",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.doc_nro,
        helperText: validationErrors[row.original.id]?.doc_nro,
        onBlur: (e) => handleEditCell(row.original.id, "doc_nro", e.target.value),
      }),
    },
    {
      accessorKey: "contrib_apellido",
      header: "Apellido Contribuidor",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.contrib_apellido,
        helperText: validationErrors[row.original.id]?.contrib_apellido,
        onBlur: (e) => handleEditCell(row.original.id, "contrib_apellido", e.target.value),
      }),
    },
    {
      accessorKey: "contrib_nombre",
      header: "Nombre Contribuidor",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.contrib_nombre,
        helperText: validationErrors[row.original.id]?.contrib_nombre,
        onBlur: (e) => handleEditCell(row.original.id, "contrib_nombre", e.target.value),
      }),
    },
    {
      accessorKey: "acta_inspeccion_num",
      header: "Acta Inspeccion",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.acta_inspeccion_num,
        helperText: validationErrors[row.original.id]?.acta_inspeccion_num,
        onBlur: (e) => handleEditCell(row.original.id, "acta_inspeccion_num", e.target.value),
      }),
    },
    {
      accessorKey: "acta_notificacion_num",
      header: "Acta Notificacion",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.acta_notificacion_num,
        helperText: validationErrors[row.original.id]?.acta_notificacion_num,
        onBlur: (e) => handleEditCell(row.original.id, "acta_notificacion_num", e.target.value),
      }),
    },
    {
      accessorKey: "acta_notificacion_num",
      header: "Acta Notificacion",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.acta_notificacion_num,
        helperText: validationErrors[row.original.id]?.acta_notificacion_num,
        onBlur: (e) => handleEditCell(row.original.id, "acta_notificacion_num", e.target.value),
      }),
    },
    {
      accessorKey: "notificacion_motivo_1",
      header: "Motivo 1",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.notificacion_motivo_1,
        helperText: validationErrors[row.original.id]?.notificacion_motivo_1,
        onBlur: (e) => handleEditCell(row.original.id, "notificacion_motivo_1", e.target.value),
      }),
    },
    {
      accessorKey: "notificacion_motivo_2",
      header: "Motivo 2",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.notificacion_motivo_2,
        helperText: validationErrors[row.original.id]?.notificacion_motivo_2,
        onBlur: (e) => handleEditCell(row.original.id, "notificacion_motivo_2", e.target.value),
      }),
    },
    {
      accessorKey: "notificacion_motivo_3",
      header: "Motivo 3",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.notificacion_motivo_3,
        helperText: validationErrors[row.original.id]?.notificacion_motivo_3,
        onBlur: (e) => handleEditCell(row.original.id, "notificacion_motivo_3", e.target.value),
      }),
    },
    {
      accessorKey: "acta_comprobacion_num",
      header: "Acta Comprobacion",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.acta_comprobacion_num,
        helperText: validationErrors[row.original.id]?.acta_comprobacion_num,
        onBlur: (e) => handleEditCell(row.original.id, "acta_comprobacion_num", e.target.value),
      }),
    },
    {
      accessorKey: "comprobacion_motivo",
      header: "Comprobacion Motivo",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.comprobacion_motivo,
        helperText: validationErrors[row.original.id]?.comprobacion_motivo,
        onBlur: (e) => handleEditCell(row.original.id, "comprobacion_motivo", e.target.value),
      }),
    },
    {
      accessorKey: "acta_clausura_num",
      header: "Acta Clausura",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.acta_clausura_num,
        helperText: validationErrors[row.original.id]?.acta_clausura_num,
        onBlur: (e) => handleEditCell(row.original.id, "acta_clausura_num", e.target.value),
      }),
    },
    {
      accessorKey: "clausura_motivo",
      header: "Clausura Motivo",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.clausura_motivo,
        helperText: validationErrors[row.original.id]?.clausura_motivo,
        onBlur: (e) => handleEditCell(row.original.id, "clausura_motivo", e.target.value),
      }),
    },
    {
      accessorKey: "acta_decomiso_num",
      header: "Acta Decomiso",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.acta_decomiso_num,
        helperText: validationErrors[row.original.id]?.acta_decomiso_num,
        onBlur: (e) => handleEditCell(row.original.id, "acta_decomiso_num", e.target.value),
      }),
    },
    {
      accessorKey: "decomiso_kilos_total",
      header: "Kilos Decomisados",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.decomiso_kilos_total,
        helperText: validationErrors[row.original.id]?.decomiso_kilos_total,
        onBlur: (e) => handleEditCell(row.original.id, "decomiso_kilos_total", e.target.value),
      }),
    },
    {
      accessorKey: "expediente_numero",
      header: "Expediente",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.expediente_numero,
        helperText: validationErrors[row.original.id]?.expediente_numero,
        onBlur: (e) => handleEditCell(row.original.id, "expediente_numero", e.target.value),
      }),
    },
    {
      accessorKey: "expediente_anio",
      header: "Año de Expediente",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.expediente_anio,
        helperText: validationErrors[row.original.id]?.expediente_anio,
        onBlur: (e) => handleEditCell(row.original.id, "expediente_anio", e.target.value),
      }),
    },
    {
      accessorKey: "oficio_numero",
      header: "Oficio",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.oficio_numero,
        helperText: validationErrors[row.original.id]?.oficio_numero,
        onBlur: (e) => handleEditCell(row.original.id, "oficio_numero", e.target.value),
      }),
    },
    {
      accessorKey: "oficio_anio",
      header: "Año de Oficio",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.oficio_anio,
        helperText: validationErrors[row.original.id]?.oficio_anio,
        onBlur: (e) => handleEditCell(row.original.id, "oficio_anio", e.target.value),
      }),
    },
    {
      accessorKey: "oficio_causa",
      header: "Causa de Oficio",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.oficio_causa,
        helperText: validationErrors[row.original.id]?.oficio_causa,
        onBlur: (e) => handleEditCell(row.original.id, "oficio_causa", e.target.value),
      }),
    },
    {
      accessorKey: "notificacion_previa_num",
      header: "Notificacion Previa",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.notificacion_previa_num,
        helperText: validationErrors[row.original.id]?.notificacion_previa_num,
        onBlur: (e) => handleEditCell(row.original.id, "notificacion_previa_num", e.target.value),
      }),
    },
    {
      accessorKey: "comprobacion_previa_num",
      header: "Comprobacion Previa",
      muiEditTextFieldProps: ({ row }) => ({
        error: !!validationErrors[row.original.id]?.comprobacion_previa_num,
        helperText: validationErrors[row.original.id]?.comprobacion_previa_num,
        onBlur: (e) => handleEditCell(row.original.id, "comprobacion_previa_num", e.target.value),
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

  if (loading) return <Typography sx={TableLoadingStyles}>Cargando expedientes...</Typography>;

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
        <Typography sx={TableTitleStyles}>Gestión de Expedientes</Typography>
        <CardsExpedientes/>
        <MaterialReactTable table={table} />
      </Box>
    </Box>
  );
};

export default TablaActuaciones;