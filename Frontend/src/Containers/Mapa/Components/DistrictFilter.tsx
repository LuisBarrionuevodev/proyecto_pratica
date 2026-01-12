import { TextField, MenuItem } from "@mui/material";

type Props = {
  distritos: string[];
  value: string;
  onChange: (v: string) => void;
};

export default function DistrictFilter({ distritos, value, onChange }: Props) {
  return (
    <TextField select size="small" label="Filtrar por distrito" value={value} onChange={(e) => onChange(e.target.value)}>
      <MenuItem value="">Todos</MenuItem>
      {distritos.map((d) => (
        <MenuItem key={d} value={d}>{d}</MenuItem>
      ))}
    </TextField>
  );
}
