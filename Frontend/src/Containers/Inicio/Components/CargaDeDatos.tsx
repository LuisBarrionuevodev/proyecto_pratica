import { Box, TextField, InputAdornment } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import type { JSX } from "react";
import { SearchFieldStyles } from "../../../styles/InicioStyles";

const CargaDeDatos = (): JSX.Element => {
    return (
        <Box sx={{ width: "100%", display: "flex", justifyContent: "center" }}>
            <TextField
                placeholder="Buscar actuaciones, relevamientos, inspectores..."
                sx={SearchFieldStyles}
                slotProps={{
                    input: {
                        startAdornment: (
                            <InputAdornment position="start">
                                <SearchIcon sx={{ color: "#666" }} />
                            </InputAdornment>
                        ),
                    },
                }}
            />
        </Box>
    );
};

export default CargaDeDatos;