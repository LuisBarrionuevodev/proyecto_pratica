import { Box } from "@mui/material";
import { BarChart } from "@mui/x-charts";
import { ChartStyle } from "../../../styles/DashboardStyles";


const EfectivasInefectivasChart = () => {

    return (
        <Box sx={{ height: 350,}}>
            <BarChart
                sx={ChartStyle}
                slotProps={{
                    tooltip: {
                        trigger: "item",
                    },
                }}
                xAxis={[
                    {
                        scaleType: "band",
                        data: ["Efectivas", "Inefectivas"],
                    },
                ]}
                series={[
                    {
                        label: "Efectivas",
                        data: [350],
                        color: "#22BF75",
                        stack: "total",
                    },
                    {
                        label: "Inefectivas",
                        data: [null, 222],
                        color: "#FA4F58",
                        stack: "total",
                    },
                ]}
                height={350}
            />
        </Box>
    );
};

export default EfectivasInefectivasChart;