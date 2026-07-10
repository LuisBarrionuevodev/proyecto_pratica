import { useCallback, useEffect, useState } from "react";
import type { GestionDomiciliosRow } from "../../../../../api/gestionDomiciliosApi";
import { searchAddress } from "../services/geocodeSearchProvider";
import {
  createPendingManualSave,
  shouldExecuteManualSave,
} from "../services/manualMapPanelSaveFlow";
import { GESTION_MAP_DEFAULT_CENTER } from "../mapaDomiciliosMapConstants";

export function useMapaEdicionManual(
  editRow: GestionDomiciliosRow | null,
  onSave: (payload: { domicilio_id: number; lat: number; lng: number }) => Promise<void>
) {
  const [pin, setPin] = useState<{ lat: number; lng: number } | null>(null);
  const [searchText, setSearchText] = useState("");
  const [saving, setSaving] = useState(false);
  const [searching, setSearching] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingSave, setPendingSave] = useState<ReturnType<typeof createPendingManualSave>>(null);

  useEffect(() => {
    if (!editRow) {
      setPin(null);
      setSearchText("");
      setConfirmOpen(false);
      setPendingSave(null);
      return;
    }
    setSearchText(editRow.domicilio_linea);
    if (editRow.lat != null && editRow.lng != null) {
      setPin({ lat: editRow.lat, lng: editRow.lng });
    } else {
      setPin(null);
    }
  }, [editRow]);

  const onSearch = useCallback(async () => {
    if (!searchText.trim()) return;
    setSearching(true);
    try {
      const result = await searchAddress(searchText);
      if (result) {
        setPin({ lat: result.lat, lng: result.lng });
      }
    } finally {
      setSearching(false);
    }
  }, [searchText]);

  const handleRequestSave = useCallback(() => {
    if (!editRow) return;
    const pending = createPendingManualSave(editRow.domicilio_id, pin);
    if (!pending) return;
    setPendingSave(pending);
    setConfirmOpen(true);
  }, [editRow, pin]);

  const handleCancelConfirm = useCallback(() => {
    setConfirmOpen(false);
    setPendingSave(null);
  }, []);

  const handleConfirmSave = useCallback(async () => {
    if (!shouldExecuteManualSave(true, pendingSave)) return;
    setSaving(true);
    try {
      await onSave({
        domicilio_id: pendingSave!.domicilio_id,
        lat: pendingSave!.lat,
        lng: pendingSave!.lng,
      });
      setConfirmOpen(false);
      setPendingSave(null);
    } finally {
      setSaving(false);
    }
  }, [onSave, pendingSave]);

  const editFocusCenter: [number, number] | null = editRow
    ? pin
      ? [pin.lat, pin.lng]
      : GESTION_MAP_DEFAULT_CENTER
    : null;

  return {
    pin,
    setPin,
    searchText,
    setSearchText,
    saving,
    searching,
    confirmOpen,
    onSearch,
    handleRequestSave,
    handleCancelConfirm,
    handleConfirmSave,
    editFocusCenter,
  };
}
