import type { JSX } from "react";
import { useState } from "react";
import { Box, Paper, Tab, Tabs } from "@mui/material";
import RelevamientosContainer from "./RelevamientosContainer";
import DenunciasCrudPlaceholder from "./Components/DenunciasCrudPlaceholder";
import { relevamientosSectionOuterSx } from "../Actuaciones/styles/filtroStyles";
import { glassTabsHeaderPanelSx } from "../../styles/GlassStyles";

const RelevamientosSectionContainer = (): JSX.Element => {
  const [section, setSection] = useState<"relevamientos" | "denuncias">("relevamientos");

  return (
    <Box sx={relevamientosSectionOuterSx}>
      <Paper elevation={0} sx={glassTabsHeaderPanelSx}>
        <Tabs value={section} onChange={(_, value) => setSection(value)} sx={{ marginBottom: 0 }}>
          <Tab label="Relevamientos" value="relevamientos" />
          <Tab label="Denuncias" value="denuncias" />
        </Tabs>
      </Paper>

      {section === "relevamientos" ? <RelevamientosContainer /> : <DenunciasCrudPlaceholder />}
    </Box>
  );
};

export default RelevamientosSectionContainer;
