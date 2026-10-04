import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import DownloadIcon from "@mui/icons-material/Download";
import { getMediaDownloadUrl } from "../../../api/mediaApi";
import type { MediaArchivoListItem } from "../mediaTypes";

type Props = {
  open: boolean;
  item: MediaArchivoListItem | null;
  onClose: () => void;
};

const MIN_SCALE = 1;
const MAX_SCALE = 4;
const SCALE_STEP = 0.5;

export function MediaPreviewDialog({ open, item, onClose }: Props) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ active: boolean; startX: number; startY: number; panX: number; panY: number } | null>(
    null
  );
  const viewportRef = useRef<HTMLDivElement | null>(null);

  const resetView = useCallback(() => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  }, []);

  useEffect(() => {
    if (!open || !item) {
      setUrl(null);
      setError(null);
      resetView();
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    resetView();
    getMediaDownloadUrl(item.archivo_id)
      .then((res) => {
        if (!cancelled) setUrl(res.download_url);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo obtener el enlace de descarga.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, item?.archivo_id, resetView]);

  const handleClose = () => {
    resetView();
    onClose();
  };

  const zoomIn = () => setScale((s) => Math.min(MAX_SCALE, s + SCALE_STEP));
  const zoomOut = () => setScale((s) => Math.max(MIN_SCALE, s - SCALE_STEP));

  const onDoubleClick = () => {
    if (scale > 1) {
      resetView();
    } else {
      setScale(2);
    }
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (scale <= 1) return;
    dragRef.current = {
      active: true,
      startX: e.clientX,
      startY: e.clientY,
      panX: pan.x,
      panY: pan.y,
    };
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d?.active) return;
    setPan({
      x: d.panX + (e.clientX - d.startX),
      y: d.panY + (e.clientY - d.startY),
    });
  };

  const onPointerUp = () => {
    if (dragRef.current) dragRef.current.active = false;
  };

  const isPdf = item?.content_type === "application/pdf";

  return (
    <Dialog open={open} onClose={handleClose} fullScreen={fullScreen} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
        <Typography variant="subtitle1" noWrap sx={{ flex: 1 }}>
          {item?.original_filename ?? "Archivo"}
        </Typography>
        <Stack direction="row" spacing={0.5} alignItems="center">
          {url && !isPdf ? (
            <>
              <IconButton size="small" onClick={zoomOut} aria-label="Reducir zoom">
                <RemoveIcon />
              </IconButton>
              <IconButton size="small" onClick={zoomIn} aria-label="Ampliar zoom">
                <AddIcon />
              </IconButton>
            </>
          ) : null}
          {url ? (
            <IconButton
              component="a"
              href={url}
              download={item?.original_filename}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Descargar"
            >
              <DownloadIcon />
            </IconButton>
          ) : null}
          <IconButton onClick={handleClose} aria-label="Cerrar">
            <CloseIcon />
          </IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent>
        {loading ? <Typography>Cargando…</Typography> : null}
        {error ? <Typography color="error">{error}</Typography> : null}
        {item ? (
          <Typography variant="caption" display="block" sx={{ mb: 1 }}>
            {item.content_type} · {(item.byte_size / 1024).toFixed(0)} KB
          </Typography>
        ) : null}
        {url && item && isPdf ? (
          <Stack spacing={1}>
            <Typography
              component="a"
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              sx={{ color: "primary.main" }}
            >
              Abrir documento
            </Typography>
          </Stack>
        ) : null}
        {url && item && !isPdf ? (
          <Box
            ref={viewportRef}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
            onDoubleClick={onDoubleClick}
            sx={{
              overflow: "hidden",
              height: fullScreen ? "calc(100vh - 140px)" : "70vh",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "action.hover",
              borderRadius: 1,
              touchAction: scale > 1 ? "none" : "manipulation",
              cursor: scale > 1 ? "grab" : "zoom-in",
            }}
          >
            <Box
              component="img"
              src={url}
              alt={item.original_filename}
              sx={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
                transformOrigin: "center center",
                userSelect: "none",
              }}
              draggable={false}
            />
          </Box>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
