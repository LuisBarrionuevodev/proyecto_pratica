import type { JSX } from "react";
import { useState } from "react";
import { Box, Paper, Tab, Tabs } from "@mui/material";
import RelevamientosContainer from "./RelevamientosContainer";
import DenunciasCrudPlaceholder from "./Components/DenunciasCrudPlaceholder";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";
import { useAppSession } from "../../auth/AppSessionProvider";

const RelevamientosSectionContainer = (): JSX.Element => {
  const { role } = useAppSession();
  const showDenuncias = role !== "relevamiento";
  const [section, setSection] = useState<"relevamientos" | "denuncias">("relevamientos");

  if (!showDenuncias) {
    return (
      <Box sx={functionalPageShellSx}>
        <RelevamientosContainer />
      </Box>
    );
  }

  return (
    <Box sx={functionalPageShellSx}>
      <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
        <Tabs value={section} onChange={(_, value) => setSection(value)} sx={moduleSlicesTabsSx}>
          <Tab label="Relevamientos" value="relevamientos" />
          <Tab label="Denuncias" value="denuncias" />
        </Tabs>
      </Paper>

      {section === "relevamientos" ? <RelevamientosContainer /> : <DenunciasCrudPlaceholder />}
    </Box>
  );
};

export default RelevamientosSectionContainer;
