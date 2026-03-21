import { AppSelect } from "../../../ui";

type Props = {
  distritos: string[];
  value: string;
  onChange: (v: string) => void;
};

export default function DistrictFilter({ distritos, value, onChange }: Props) {
  return (
    <AppSelect
      size="small"
      label="Filtrar por distrito"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      options={[
        { value: "", label: "Todos" },
        ...distritos.map((d) => ({ value: d, label: d })),
      ]}
    />
  );
}
