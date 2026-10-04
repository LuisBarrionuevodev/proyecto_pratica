import { useEffect, useState } from "react";
import {
  Box,
  ImageListItem,
  ImageListItemBar,
  Skeleton,
  Typography,
} from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { getMediaDownloadUrl } from "../../../api/mediaApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { MediaArchivoListItem } from "../mediaTypes";

type Props = {
  item: MediaArchivoListItem;
  onOpen: () => void;
  onDelete?: () => void;
  deleting?: boolean;
};

export function MediaThumbnailTile({ item, onOpen, onDelete, deleting }: Props) {
  const isImg = item.content_type.startsWith("image/");
  const [thumbUrl, setThumbUrl] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "ok" | "error">(
    isImg ? "loading" : "idle"
  );

  useEffect(() => {
    if (!isImg) return;
    let cancelled = false;
    setLoadState("loading");
    setThumbUrl(null);
    getMediaDownloadUrl(item.archivo_id)
      .then((res) => {
        if (!cancelled) {
          setThumbUrl(res.download_url);
          setLoadState("ok");
        }
      })
      .catch(() => {
        if (!cancelled) setLoadState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [item.archivo_id, isImg]);

  return (
    <ImageListItem sx={{ cursor: "pointer" }} onClick={onOpen}>
      <Box
        sx={{
          height: 96,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "action.hover",
          borderRadius: 1,
          overflow: "hidden",
          position: "relative",
        }}
      >
        {isImg ? (
          loadState === "loading" ? (
            <Skeleton variant="rectangular" width="100%" height={96} />
          ) : loadState === "error" ? (
            <Typography variant="caption" sx={{ px: 1, color: GLASS_COLORS.textMuted }}>
              No se pudo cargar
            </Typography>
          ) : thumbUrl ? (
            <img
              src={thumbUrl}
              alt={item.original_filename}
              loading="lazy"
              style={{ width: "100%", height: 96, objectFit: "cover" }}
            />
          ) : null
        ) : (
          <StackLikePdf />
        )}
        {onDelete ? (
          <Box
            component="button"
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            disabled={deleting}
            sx={{
              position: "absolute",
              top: 4,
              right: 4,
              border: "none",
              borderRadius: 1,
              px: 0.75,
              py: 0.25,
              fontSize: 11,
              cursor: deleting ? "wait" : "pointer",
              bgcolor: "error.main",
              color: "error.contrastText",
            }}
          >
            Eliminar
          </Box>
        ) : null}
      </Box>
      <ImageListItemBar
        title={item.original_filename}
        subtitle={
          isImg
            ? `${(item.byte_size / 1024).toFixed(0)} KB`
            : "PDF · Abrir documento"
        }
      />
    </ImageListItem>
  );
}

function StackLikePdf() {
  return (
    <Box sx={{ textAlign: "center", px: 1 }}>
      <PictureAsPdfIcon sx={{ color: GLASS_COLORS.textSecondary }} />
      <Typography variant="caption" display="block" sx={{ color: GLASS_COLORS.textMuted }}>
        PDF
      </Typography>
    </Box>
  );
}
