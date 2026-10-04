import { useEffect, useState } from "react";
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
import { getMediaDownloadUrl } from "../../../api/mediaApi";
import type { MediaArchivoListItem } from "../mediaTypes";

type Props = {
  open: boolean;
  item: MediaArchivoListItem | null;
  onClose: () => void;
};

export function MediaPreviewDialog({ open, item, onClose }: Props) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !item) {
      setUrl(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
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
  }, [open, item?.archivo_id]);

  const isPdf = item?.content_type === "application/pdf";

  return (
    <Dialog open={open} onClose={onClose} fullScreen={fullScreen} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="subtitle1" noWrap sx={{ pr: 2 }}>
          {item?.original_filename ?? "Archivo"}
        </Typography>
        <IconButton onClick={onClose} aria-label="Cerrar">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {loading ? <Typography>Cargando…</Typography> : null}
        {error ? <Typography color="error">{error}</Typography> : null}
        {url && item && !isPdf ? (
          <Box
            component="img"
            src={url}
            alt={item.original_filename}
            sx={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain", mx: "auto", display: "block" }}
          />
        ) : null}
        {url && item && isPdf ? (
          <Stack spacing={1}>
            <Typography variant="body2">PDF · {(item.byte_size / 1024).toFixed(0)} KB</Typography>
            <Typography
              component="a"
              href={url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir documento
            </Typography>
          </Stack>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
