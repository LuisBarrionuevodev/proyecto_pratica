import { Tooltip } from "@mui/material";

import { AppButton } from "../../../ui";

export type ReinspeccionOperativaAccionCellProps = {
  onProrroga: () => void;
  disabled?: boolean;
  disabledReason?: string;
};

/** Acción en bandeja Pendiente reinspección: prórroga (bloqueada si está en pool/ruta). */
export function ReinspeccionOperativaAccionCell({
  onProrroga,
  disabled = false,
  disabledReason,
}: ReinspeccionOperativaAccionCellProps) {
  const button = (
    <AppButton dsVariant="primary" dsSize="sm" onClick={onProrroga} disabled={disabled}>
      Prórroga
    </AppButton>
  );

  if (disabled && disabledReason) {
    return (
      <Tooltip title={disabledReason}>
        <span>{button}</span>
      </Tooltip>
    );
  }

  return button;
}
