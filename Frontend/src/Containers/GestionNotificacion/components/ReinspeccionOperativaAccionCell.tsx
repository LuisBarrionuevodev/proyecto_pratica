import { AppButton } from "../../../ui";

export type ReinspeccionOperativaAccionCellProps = {
  onProrroga: () => void;
};

/** Acción única en bandeja Pendiente reinspección: abre modal de prórroga (incluye detalle). */
export function ReinspeccionOperativaAccionCell({ onProrroga }: ReinspeccionOperativaAccionCellProps) {
  return (
    <AppButton dsVariant="primary" dsSize="sm" onClick={onProrroga}>
      Prórroga
    </AppButton>
  );
}
