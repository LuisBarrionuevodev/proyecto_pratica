import {
  Box,
  ImageListItem,
  ImageListItemBar,
  Skeleton,
  Typography,
} from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { MediaArchivoListItem } from "../mediaTypes";
import { useLazyMediaDownloadUrl } from "../hooks/useLazyMediaDownloadUrl";

type Props = {
  item: MediaArchivoListItem;
  onOpen: () => void;
  onDelete?: () => void;
  deleting?: boolean;
};

export function MediaThumbnailTile({ item, onOpen, onDelete, deleting }: Props) {
  const isImg = item.content_type.startsWith("image/");
  const { phase, thumbUrl, rootRef, retry } = useLazyMediaDownloadUrl({
    archivoId: item.archivo_id,
    enabled: isImg,
  });

  const ariaLabel = isImg
    ? `Ver imagen: ${item.original_filename}`
    : `Abrir PDF: ${item.original_filename}`;

  return (
    <ImageListItem
      sx={{ cursor: "pointer" }}
      onClick={onOpen}
      aria-label={ariaLabel}
    >
      <Box
        ref={isImg ? rootRef : undefined}
        role="button"
        tabIndex={0}
        aria-label={ariaLabel}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onOpen();
          }
        }}
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
          phase === "loading" || phase === "idle" ? (
            <Skeleton variant="rectangular" width="100%" height={96} />
          ) : phase === "error" ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 0.5,
                px: 1,
              }}
            >
              <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, textAlign: "center" }}>
                No se pudo cargar
              </Typography>
              <Box
                component="button"
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  retry();
                }}
                sx={{
                  border: "none",
                  borderRadius: 1,
                  px: 0.75,
                  py: 0.25,
                  fontSize: 11,
                  cursor: "pointer",
                  bgcolor: "primary.main",
                  color: "primary.contrastText",
                }}
              >
                Reintentar
              </Box>
            </Box>
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
      {!isImg ? (
        <ImageListItemBar
          title={item.original_filename}
          subtitle="PDF · Abrir documento"
        />
      ) : null}
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
