import { Button } from "@mui/material";

export const TableButtonCreate = ({ table }: any) => {
    return(
        <Button
        variant="contained"
        sx={{
          backgroundColor: "#0166FF",
          color: "white",
          fontFamily: "Tactic Sans",
          textTransform: "none",
        }}
         onClick={() => table.setCreatingRow(true)}
      >
        Crear Relevamiento
      </Button>
    )
}