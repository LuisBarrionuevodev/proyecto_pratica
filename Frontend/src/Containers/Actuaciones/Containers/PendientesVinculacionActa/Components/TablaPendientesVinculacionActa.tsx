import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Typography } from "@mui/material";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import type { IActuacion } from "../../../../../types/actuaciones";
import { updateActuacion } from "../../../../../api/actuacionesApi";
import { usePendientes } from "../../../../../hooks/usePendientes";
import { DARK_TABLE_CONFIG, MRT_READ_ONLY_BANDEJA } from "../../../styles/actuacionesTableStyles";
import { formDialogContentStackSx } from "../../../../../styles/formDialogStyles";
import { TableGeneralStyles, TableLoadingStyles } from "../../../../../styles/TablasStyle";
import CardsExpedientes from "../../../Components/CardsExpedientes";
import { AppButton, AppDialog, AppTextField } from "../../../../../ui";

const TablaPendientesVinculacionActa = () => {
  const { pendientes, setPendientes, loading } = usePendientes();
  const [data, setData] = useState<IActuacion[]>([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<IActuacion | null>(null);
  const [expNumero, setExpNumero] = useState("");
  const [expAnio, setExpAnio] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [modalApiError, setModalApiError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setData(pendientes ?? []);
  }, [pendientes]);

  const openModal = (row: IActuacion) => {
    setSelected(row);
    setExpNumero(String(row.expediente_numero ?? "").trim());
    setExpAnio(String(row.expediente_anio ?? "").trim());
    setFieldErrors({});
    setModalApiError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setSelected(null);
    setFieldErrors({});
    setModalApiError(null);
  };

  const handleSaveExpediente = useCallback(async () => {
    if (!selected) return;
    const next: Record<string, string> = {};
    if (!expNumero.trim()) next.expNumero = "Completá el número de expediente.";
    if (!expAnio.trim()) next.expAnio = "Completá el año de expediente.";
    setFieldErrors(next);
    if (Object.keys(next).length > 0) return;

    setSaving(true);
    setModalApiError(null);
    try {
      const payload: IActuacion = {
        ...selected,
        expediente_numero: expNumero.trim(),
        expediente_anio: expAnio.trim(),
      };
      await updateActuacion(selected.id, payload);
      setData((prev) => prev.map((r) => (r.id === selected.id ? payload : r)));
      setPendientes((prev) => prev.map((r) => (r.id === selected.id ? payload : r)));
      setModalOpen(false);
      setSelected(null);
      setFieldErrors({});
      setModalApiError(null);
    } catch (error: unknown) {
      const detail =
        error && typeof error === "object" && "response" in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setModalApiError(detail || "No se pudo actualizar el registro.");
    } finally {
      setSaving(false);
    }
  }, [selected, expNumero, expAnio, setPendientes]);

  const columns: MRT_ColumnDef<IActuacion>[] = [
    {
      accessorKey: "id",
      header: "ID",
      enableHiding: true,
      enableEditing: false,
      enableClickToCopy: true,
    },
    { accessorKey: "orden_trabajo_numero", header: "OT", enableEditing: false },
    { accessorKey: "fecha_actuacion", header: "Fecha", enableEditing: false },
    { accessorKey: "rubro_nombre", header: "Rubro", enableEditing: false },
    { accessorKey: "inspector1", header: "Inspector 1", enableEditing: false },
    { accessorKey: "inspector2", header: "Inspector 2", enableEditing: false },
    { accessorKey: "inspector3", header: "Inspector 3", enableEditing: false },
    { accessorKey: "calle", header: "Calle", enableEditing: false },
    { accessorKey: "numero", header: "Numero", enableEditing: false },
    { accessorKey: "tipo_actuacion", header: "Tipo de Actuacion", enableEditing: false },
    { accessorKey: "contraproducencia", header: "Contraproducencia", enableEditing: false },
    { accessorKey: "doc_tipo_codigo", header: "Tipo de Documento", enableEditing: false },
    { accessorKey: "doc_nro", header: "Numero de Documento", enableEditing: false },
    { accessorKey: "contrib_apellido", header: "Apellido Contribuidor", enableEditing: false },
    { accessorKey: "contrib_nombre", header: "Nombre Contribuidor", enableEditing: false },
    { accessorKey: "acta_inspeccion_num", header: "Acta Inspeccion", enableEditing: false },
    { accessorKey: "acta_notificacion_num", header: "Acta Notificacion", enableEditing: false },
    { accessorKey: "notificacion_motivo_1", header: "Motivo 1", enableEditing: false },
    { accessorKey: "notificacion_motivo_2", header: "Motivo 2", enableEditing: false },
    { accessorKey: "notificacion_motivo_3", header: "Motivo 3", enableEditing: false },
    { accessorKey: "acta_comprobacion_num", header: "Acta Comprobacion", enableEditing: false },
    { accessorKey: "comprobacion_motivo", header: "Comprobacion Motivo", enableEditing: false },
    { accessorKey: "acta_clausura_num", header: "Acta Clausura", enableEditing: false },
    { accessorKey: "clausura_motivo", header: "Clausura Motivo", enableEditing: false },
    { accessorKey: "acta_decomiso_num", header: "Acta Decomiso", enableEditing: false },
    { accessorKey: "decomiso_kilos_total", header: "Kilos Decomisados", enableEditing: false },
    { accessorKey: "expediente_numero", header: "Expediente", enableEditing: false },
    { accessorKey: "expediente_anio", header: "Año de Expediente", enableEditing: false },
    { accessorKey: "oficio_numero", header: "Oficio", enableEditing: false },
    { accessorKey: "oficio_anio", header: "Año de Oficio", enableEditing: false },
    { accessorKey: "oficio_causa", header: "Causa de Oficio", enableEditing: false },
    { accessorKey: "notificacion_previa_num", header: "Notificacion Previa", enableEditing: false },
    { accessorKey: "comprobacion_previa_num", header: "Comprobacion Previa", enableEditing: false },
    {
      id: "acciones_expediente",
      header: "Vinculación expediente",
      size: 200,
      enableEditing: false,
      Cell: ({ row }) => (
        <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original)}>
          Editar expediente
        </AppButton>
      ),
    },
  ];

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...MRT_READ_ONLY_BANDEJA,
    columns,
    data,
    initialState: {
      columnVisibility: {
        id: false,
        rubro_nombre: false,
        inspector1: false,
        inspector2: false,
        inspector3: false,
        tipo_actuacion: false,
        contraproducencia: false,
        doc_tipo_codigo: false,
        doc_nro: false,
        contrib_apellido: false,
        contrib_nombre: false,
        acta_inspeccion_num: false,
        notificacion_motivo_1: false,
        notificacion_motivo_2: false,
        notificacion_motivo_3: false,
        comprobacion_motivo: false,
        acta_clausura_num: false,
        clausura_motivo: false,
        acta_decomiso_num: false,
        decomiso_kilos_total: false,
        oficio_numero: false,
        calle: false,
        numero: false,
        oficio_anio: false,
        oficio_causa: false,
        acta_notificacion_num: false,
        notificacion_previa_num: false,
        comprobacion_previa_num: false,
      },
    },
  });

  if (loading) return <Typography sx={TableLoadingStyles}>Cargando Pendientes...</Typography>;

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
        <CardsExpedientes />
        <MaterialReactTable table={table} />
      </Box>

      <AppDialog
        open={modalOpen}
        onClose={closeModal}
        title="Editar expediente (vinculación acta)"
        appearance="glass"
        maxWidth="sm"
        fullWidth
        showCloseButton
        onCloseButtonClick={closeModal}
        contentSx={formDialogContentStackSx}
        actions={
          <>
            <AppButton dsVariant="ghost" dsSize="sm" onClick={closeModal} disabled={saving}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" dsSize="sm" onClick={() => void handleSaveExpediente()} disabled={saving}>
              {saving ? "Guardando..." : "Guardar"}
            </AppButton>
          </>
        }
      >
        {modalApiError ? (
          <Alert severity="error" sx={{ mb: 0 }}>
            {modalApiError}
          </Alert>
        ) : null}
        <AppTextField
          appearance="glass"
          label="Número de expediente"
          value={expNumero}
          onChange={(e) => {
            setExpNumero(e.target.value);
            setFieldErrors((f) => {
              const n = { ...f };
              delete n.expNumero;
              return n;
            });
          }}
          fullWidth
          required
          error={Boolean(fieldErrors.expNumero)}
          helperText={fieldErrors.expNumero || undefined}
        />
        <AppTextField
          appearance="glass"
          label="Año de expediente"
          value={expAnio}
          onChange={(e) => {
            setExpAnio(e.target.value);
            setFieldErrors((f) => {
              const n = { ...f };
              delete n.expAnio;
              return n;
            });
          }}
          fullWidth
          required
          error={Boolean(fieldErrors.expAnio)}
          helperText={fieldErrors.expAnio || undefined}
        />
      </AppDialog>
    </Box>
  );
};

export default TablaPendientesVinculacionActa;
