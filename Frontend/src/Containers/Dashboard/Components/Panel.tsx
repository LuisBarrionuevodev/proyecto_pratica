import { Box, Button, Grid, TextField, Typography } from "@mui/material";
import { exportDashboardToExcel } from "../../../utils/exportExcelDashboard";
import ActuacionesMensualesChart from "./DashboardActuacionMensual";
import DecomisoMensualChart from "./DashboardDecomiso";
import TopRubrosChart from "./DashboardTopRubros";
import RankingInspectoresChart from "./DashboardInspectores";
import DistribucionTipoChart from "./DashboardDistribucion";
import ComparacionTurnoChart from "./DashboardTurnos";
import PipelineChart from "./DashboardEmbudo";
import ChartCard from "./ChartCard";
import FunnelChart from "./DashboardFunnel";
import KPI from "./DashboardKPI";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { useEffect, useState } from "react";

type Periodo = "Semanal" | "Mensual" | "Trimestral" | "Anual";

const Panel = () => {

  const [periodo, setPeriodo] = useState<Periodo>("Mensual");
  const [dashboardData, setDashboardData] = useState<any>(null);

  useEffect(() => {
    const fetchDashboard = async () => {

      // Ejemplo de como se traeria la data:

      try {
        const res = await fetch(
          `/api/dashboard?periodo=${periodo}`
        );
        const data = await res.json();
        setDashboardData(data);
      } catch (err) {
        console.error(err);
      }
    };

    fetchDashboard();
  }, [periodo]);


  const tarjetasData = [
    { title: "Actuaciones", value: 120 },
    { title: "Relevamientos", value: 85 },
    { title: "Pendientes", value: 14 },
    { title: "Completados", value: 191 },
  ];

  const lineChartData = [
    { mes: "Ene", actu: 40 },
    { mes: "Feb", actu: 55 },
    { mes: "Mar", actu: 90 },
    { mes: "Abr", actu: 75 },
    { mes: "May", actu: 120 },
  ];

  const pieChartData = [
    { rubro: "Panaderia", clausuras: 120 },
    { rubro: "Carniceria", clausuras: 90 },
    { rubro: "Drugstore", clausuras: 70 },
    { rubro: "Kiosco", clausuras: 50 },
    { rubro: "Fiambreria", clausuras: 40 },
    { rubro: "Otros", clausuras: 30 },
  ];

  return (
    <Box p={3} ml={3}>
      <Box display={"flex"} flexDirection={{ xs: "column", md: "column", lg: "row" }} justifyContent={"space-between"} alignItems={"center"}>
        <Typography color="white" fontSize={{ xs: "20px", sm: "50px" }} fontWeight={500} >
          Panel de Control
        </Typography>
        <Box
          display="flex"
          flexDirection={{ xs: "column", md: "row" }}
          bgcolor="#2B2E34"
          borderRadius={3}
          height={{ xs: "auto", md: "50px" }}
        >
          {["semanal", "mensual", "trimestral", "anual"].map((item) => (
            <Button
              key={item}
              onClick={() => setPeriodo(item as Periodo)}
              variant={periodo === item ? "contained" : "text"}
              sx={{
                color: periodo === item ? "#000" : "#fff",
                backgroundColor:
                  periodo === item ? "#fff" : "transparent",
                borderRadius: 2,
                
                fontWeight: 500,
                textTransform: "uppercase",
                "&:hover": {
                  backgroundColor:
                    periodo === item ? "#fff" : "rgba(255,255,255,0.1)",
                },
              }}
            >
              {item}
            </Button>
          ))}
        </Box>
        <Box sx={{ display: "flex", flexDirection: { xs: "column", xl: "row" }, gap: 3, m: 3 }}>
          <Box >
            <TextField
              type="date"
              label="Desde"
              slotProps={{
                inputLabel: { shrink: true }
              }}
              variant="outlined"
              sx={filtroItemStyles}
            />
          </Box>

          <Box >
            <TextField
              type="date"
              label="Hasta"
              slotProps={{
                inputLabel: { shrink: true }
              }}
              variant="outlined"
              sx={filtroItemStyles}
            />
          </Box>
        </Box>
        <Button
          sx={{ height: "50px", mb: { xs: 3, lg: 0 }, fontSize: { xs: "10px", sm: "14px", backgroundColor: "#0166FF", borderRadius: 10 } }}
          variant="contained"
          color="primary"
          onClick={() =>
            exportDashboardToExcel({
              tarjetas: tarjetasData,
              lineChart: lineChartData,
              pieChart: pieChartData,
            })
          }
        >
          Descargar Informe
        </Button>
      </Box>

      <Grid container spacing={2} mb={2}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4, xl: 2 }}>
          <KPI title="Actuaciones" value={400} percentage={10} icon={""} periodo={periodo} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4, xl: 2 }}>
          <KPI title="Relevamientos" value={250} percentage={30} icon={""} periodo={periodo} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4, xl: 2 }}>
          <KPI title="Kilos Decomisados" value={300} percentage={32} icon={""} periodo={periodo} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4, xl: 2 }}>
          <KPI title="CPC" value={250} percentage={40} icon={""} periodo={periodo} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 2.4, xl: 2 }}>
          <KPI title="CID" value={15} percentage={30} icon={""} periodo={periodo} />
        </Grid>
      </Grid>

      <Grid container spacing={3} >
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard title={`Actuaciones ${periodo}`}>
            <ActuacionesMensualesChart
            periodo={periodo} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <ChartCard title={`Decomiso ${periodo}`}>
            <DecomisoMensualChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <ChartCard title={`Top Rubros ${periodo}`}>
            <TopRubrosChart
             />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <ChartCard title={`Distribucion por Tipo ${periodo}`}>
            <DistribucionTipoChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <ChartCard title={`Ranking Inspectores ${periodo}`}>
            <RankingInspectoresChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <ChartCard title={`Comparacion por Turno ${periodo}`}>
            <ComparacionTurnoChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <ChartCard title="Funnel">
            <FunnelChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard title="Pipeline">
            <PipelineChart />
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Panel;