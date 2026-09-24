import { useCallback, useEffect, useState } from "react";
import { Box } from "@mui/material";

import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudDialogSection,
  CrudFormErrorSummary,
  CrudFormSlot,
  CrudGlassDialog,
} from "../../../components/crudDialog";
import { AppSelect, AppTextField } from "../../../ui";
import {
  emptyGestionUsuarioForm,
  gestionUsuarioFormFromUser,
  USUARIO_ROLE_OPTIONS,
  usuarioRoleLabel,
  type GestionUsuarioFormValues,
} from "../utils/gestionUsuarioForm";

export type GestionUsuarioCrudTarget = {
  id: number;
  username: string;
  email: string;
  role: "admin" | "usuario" | "relevador";
  is_active?: boolean;
};

export type GestionUsuarioCrudDialogProps = {
  open: boolean;
  mode: "view" | "edit" | "create";
  user: GestionUsuarioCrudTarget | null;
  saving: boolean;
  fieldErrors: Record<string, string>;
  globalError: string | null;
  onClose: () => void;
  onModeChange?: (mode: "view" | "edit") => void;
  onSave: (values: GestionUsuarioFormValues) => void;
  onClearFieldError: (field: string) => void;
  disablePortal?: boolean;
};

export function GestionUsuarioCrudDialog({
  open,
  mode,
  user,
  saving,
  fieldErrors,
  globalError,
  onClose,
  onModeChange,
  onSave,
  onClearFieldError,
  disablePortal,
}: GestionUsuarioCrudDialogProps) {
  const [draft, setDraft] = useState<GestionUsuarioFormValues>(() =>
    mode !== "create" && user ? gestionUsuarioFormFromUser(user) : emptyGestionUsuarioForm()
  );

  useEffect(() => {
    if (!open) return;
    if (mode !== "create" && user) {
      setDraft(gestionUsuarioFormFromUser(user));
    } else {
      setDraft(emptyGestionUsuarioForm());
    }
  }, [open, mode, user]);

  const fe = useCallback((key: string) => fieldErrors[key] ?? "", [fieldErrors]);

  const patch = useCallback(
    (patchValues: Partial<GestionUsuarioFormValues>) => {
      setDraft((prev) => ({ ...prev, ...patchValues }));
      Object.keys(patchValues).forEach((k) => onClearFieldError(k));
    },
    [onClearFieldError]
  );

  const handleClose = () => {
    if (saving) return;
    onClose();
  };

  const isCreate = mode === "create";
  const isView = mode === "view";
  const isEdit = mode === "edit";
  const active = user?.is_active !== false;
  const formMode = isView ? "view" : "edit";

  const titulo = isCreate ? "Nuevo usuario" : isView ? "Usuario" : "Editar usuario";
  const subtitulo = isCreate ? "Administrar acceso al sistema" : user?.username || undefined;

  return (
    <CrudGlassDialog
      open={open}
      disablePortal={disablePortal}
      hideBackdrop={disablePortal}
      onClose={(_e, _reason) => handleClose()}
      onCloseButtonClick={handleClose}
      maxWidth="sm"
      title={
        <CrudDialogHeader
          domainChip="Gestión de usuarios"
          mode={isCreate ? "create" : isView ? "view" : "edit"}
          titulo={titulo}
          subtitulo={subtitulo}
          statusChip={!isCreate ? (active ? "Activo" : "Inactivo") : undefined}
        />
      }
      actions={
        <CrudDialogActions
          mode={isCreate ? "create" : isView ? "view" : "edit"}
          onEdit={isView && onModeChange ? () => onModeChange("edit") : undefined}
          onSave={() => onSave(draft)}
          loading={saving}
          canEdit={!isCreate}
          saveLabel={isCreate ? "Crear usuario" : "Guardar cambios"}
        />
      }
    >
      <CrudFormErrorSummary message={globalError} />

      <CrudDialogSection title="Datos del usuario" variant="plain">
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <CrudFormSlot
            label="Usuario"
            mode={formMode}
            value={draft.username}
            required
            error={Boolean(fe("username"))}
            helperText={fe("username")}
          >
            <AppTextField
              appearance="glass"
              label="Usuario"
              value={draft.username}
              onChange={(e) => patch({ username: e.target.value })}
              required
              fullWidth
              error={Boolean(fe("username"))}
              helperText={fe("username") || undefined}
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Email"
            mode={formMode}
            value={draft.email}
            required
            error={Boolean(fe("email"))}
            helperText={fe("email")}
          >
            <AppTextField
              appearance="glass"
              label="Email"
              type="email"
              value={draft.email}
              onChange={(e) => patch({ email: e.target.value })}
              required
              fullWidth
              error={Boolean(fe("email"))}
              helperText={fe("email") || undefined}
            />
          </CrudFormSlot>
        </Box>
      </CrudDialogSection>

      <CrudDialogSection title="Acceso y permisos" variant="plain">
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <CrudFormSlot
            label="Rol"
            mode={formMode}
            value={draft.role ? usuarioRoleLabel(draft.role) : null}
            required
            error={Boolean(fe("role"))}
            helperText={fe("role")}
          >
            <AppSelect
              appearance="glass"
              label="Rol"
              value={draft.role}
              onChange={(e) => patch({ role: e.target.value as GestionUsuarioFormValues["role"] })}
              options={[{ value: "", label: "—" }, ...USUARIO_ROLE_OPTIONS]}
              fullWidth
              error={Boolean(fe("role"))}
              helperText={fe("role") || undefined}
            />
          </CrudFormSlot>
          <CrudFormSlot
            label="Contraseña"
            mode={formMode}
            value={isView ? "••••••••" : draft.password || (isEdit ? "Sin cambios" : null)}
            required={isCreate}
            error={Boolean(fe("password"))}
            helperText={fe("password")}
          >
            <AppTextField
              appearance="glass"
              label="Contraseña"
              type="password"
              value={draft.password}
              onChange={(e) => patch({ password: e.target.value })}
              required={isCreate}
              fullWidth
              placeholder={isEdit ? "Sin cambios" : undefined}
              error={Boolean(fe("password"))}
              helperText={fe("password") || undefined}
            />
          </CrudFormSlot>
        </Box>
      </CrudDialogSection>

      <CrudDialogSection title="Estado" variant="plain">
        <CrudFormSlot
          label="Estado"
          mode="view"
          value={isCreate ? "Activo" : active ? "Activo" : "Inactivo"}
        />
      </CrudDialogSection>
    </CrudGlassDialog>
  );
}
