import { Box, Button, Grid, Typography } from "@mui/material";
import DashboardCards from "./DashboardCards";
import DashboardChart from "./DashboardChart";
import RubrosPieChart from "./DashboardCell";
import { exportDashboardToExcel } from "../../../utils/exportExcelDashboard";

const Panel = () => {

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
    <Box p={3} ml={{xs: 10, sm: 12, md: 20}}>
      <Box display={"flex"} justifyContent={"space-between"}>
      <Typography fontSize={{xs: "25px",sm:"50px"}} fontWeight={800} mb={3}>
        Panel de Control
      </Typography>
       <Button
       sx={{height:"50px", fontSize: {xs:"10px", sm:"14px", backgroundColor:"#0166FF"}}}
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

      {/* Tarjetas principales */}
      <Grid container spacing={3} mb={3}>
        <Grid size = {{ xs:12, sm:6 ,md:3 }}>
          <DashboardCards title="Actuaciones" value={120} />
        </Grid>
        <Grid size = {{ xs:12, sm:6 ,md:3 }}>
          <DashboardCards title="Relevamientos" value={85} />
        </Grid>
        <Grid size = {{ xs:12, sm:6 ,md:3 }}>
          <DashboardCards title="Pendientes" value={14} />
        </Grid>
        <Grid size = {{ xs:12, sm:6 ,md:3 }}>
          <DashboardCards title="Completados" value={191} />
        </Grid>
      </Grid>

      {/* Gráfico */}
      <Grid container spacing={3} >
        <Grid size= {{xs:12, md:12}} display={"flex"}  flexDirection={{xs: "column",sm: "column",md:"row"}} gap={2} >
          <DashboardChart />
          <RubrosPieChart />
        </Grid>
      </Grid>

      

    </Box>
  );
}

export default Panel;