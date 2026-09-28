import { Button } from "@mui/material";
import { FONT_FAMILY_UI } from "../../../theme/typography";

export const TableButtonCreate = ({ table }: any) => {
    return(
        <Button
        variant="contained"
        sx={{
          backgroundColor: "#0166FF",
          color: "white",
          fontFamily: FONT_FAMILY_UI,
          textTransform: "none",
        }}
         onClick={() => table.setCreatingRow(true)}
      >
        Crear Actuacion
      </Button>
    )
}