import { TextField, InputAdornment, IconButton } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";

type Props = { value: string; onChange: (v: string) => void; onClear?: () => void; };

export default function SearchBar({ value, onChange, onClear }: Props) {
  return (
    <TextField
    sx={{fontSize:"5px",}}
      size="small"
      placeholder="Buscar locales..."
      value={value}
      onChange={(e) => onChange(e.target.value)}
      InputProps={{
        startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment>,
        endAdornment: value ? (
          <InputAdornment position="end">
            <IconButton size="small" onClick={() => { onChange(""); onClear?.(); }}>
              <ClearIcon />
            </IconButton>
          </InputAdornment>
        ) : undefined,
      }}
    />
  );
}
