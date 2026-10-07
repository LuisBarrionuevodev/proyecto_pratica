/** @jsxImportSource react */
import { useCallback, useRef, useState } from "react";
import { Box } from "@mui/material";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { useAppFeedback } from "../../../components/feedback";
import {
  ActuacionMediaGallery,
  type ActuacionMediaGalleryHandle,
} from "../../../features/media/components/ActuacionMediaGallery";
import { MediaUploadPanelErrorBoundary } from "../../../features/media/components/MediaUploadPanelErrorBoundary";
import { AppButton, ConfirmDialog } from "../../../ui";
import {
  CrudDialogActions,
  CrudDialogHeader,
  CrudGlassDialog,
} from "../../../components/crudDialog";

export type InspectorCargarFotosDialogProps = {
  open: boolean;
  draft: IActuacionListItem;
  detailLoading?: boolean;
  onClose: () => void;
  disablePortal?: boolean;
};

/**
 * Modal exclusivo de fotos para Inspector (Mis trabajos). Subida manual con GUARDAR FOTOS.
 */
export function InspectorCargarFotosDialog({
  open,
  draft,
  detailLoading = false,
  onClose,
  disablePortal,
}: InspectorCargarFotosDialogProps) {
  const feedback = useAppFeedback();
  const galleryRef = useRef<ActuacionMediaGalleryHandle | null>(null);
  const [saving, setSaving] = useState(false);
  const [discardConfirmOpen, setDiscardConfirmOpen] = useState(false);

  const rutaItemId = draft.ruta_item_id ?? null;

  const tryClose = useCallback(() => {
    const gallery = galleryRef.current;
    if (gallery?.isUploadInProgress()) return;
    const pending = gallery?.pendingSaveCount() ?? 0;
    if (pending > 0) {
      setDiscardConfirmOpen(true);
      return;
    }
    onClose();
  }, [onClose]);

  const handleGuardarFotos = useCallback(async () => {
    const gallery = galleryRef.current;
    if (!gallery || gallery.isUploadInProgress()) return;
    const pending = gallery.pendingSaveCount();
    if (pending === 0) {
      feedback.info("Seleccioná fotos para guardar.");
      return;
    }
    setSaving(true);
    try {
      const outcome = await gallery.saveQueuedPhotos();
      if (outcome === "success") {
        feedback.success("Fotos guardadas correctamente.");
        onClose();
      }
    } finally {
      setSaving(false);
    }
  }, [feedback, onClose]);

  const uploadBusy = saving || (galleryRef.current?.isUploadInProgress() ?? false);

  return (
    <>
      <CrudGlassDialog
        open={open}
        disablePortal={disablePortal}
        hideBackdrop={disablePortal}
        onClose={(_e, _reason) => tryClose()}
        onCloseButtonClick={tryClose}
        maxWidth="md"
        mobileFullScreen
        title={
          <CrudDialogHeader
            domainChip="Mis trabajos"
            titulo="Cargar más fotos"
            subtitulo="Seleccioná fotos y guardalas cuando estés listo"
            reference={draft.orden_trabajo_numero ?? String(draft.id)}
          />
        }
        actions={
          <CrudDialogActions
            mode="edit"
            loading={detailLoading || uploadBusy}
            saveLabel="GUARDAR FOTOS"
            onSave={() => void handleGuardarFotos()}
            saveDisabled={uploadBusy || rutaItemId == null}
            extraActions={
              <AppButton dsVariant="ghost" dsSize="sm" onClick={tryClose} disabled={uploadBusy}>
                Volver
              </AppButton>
            }
          />
        }
      >
        <Box sx={{ position: "relative" }}>
          <MediaUploadPanelErrorBoundary
            resetKey={rutaItemId ?? draft.id}
            rutaItemId={rutaItemId}
            onClosePanel={tryClose}
          >
            <ActuacionMediaGallery
              ref={galleryRef}
              rutaItemId={rutaItemId}
              readOnly={false}
              hideTitle
              manualSave
            />
          </MediaUploadPanelErrorBoundary>
        </Box>
      </CrudGlassDialog>

      <ConfirmDialog
        open={discardConfirmOpen}
        onClose={() => setDiscardConfirmOpen(false)}
        onConfirm={() => {
          galleryRef.current?.discardLocalQueue();
          setDiscardConfirmOpen(false);
          onClose();
        }}
        title="¿Salir sin guardar las fotos seleccionadas?"
        confirmLabel="Salir sin guardar"
        cancelLabel="Seguir cargando"
      >
        Las fotos elegidas todavía no se subieron.
      </ConfirmDialog>
    </>
  );
}
