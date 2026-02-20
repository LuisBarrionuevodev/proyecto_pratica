import { ResponsiveFunnel } from "@nivo/funnel";
import { Box } from "@mui/material";

const data = [
    { id: "Actuaciones", value: 1000 },
    { id: "Inspecciones", value: 800 },
    { id: "Notificaciones", value: 600 },
    { id: "Clausuras", value: 400 },
    { id: "Decomisos", value: 200 },
];

const FunnelChart = () => {
    return (
        <Box sx={{ height: 350 }}>
            <ResponsiveFunnel
                data={data}
                margin={{ top: 30, right: 20, bottom: 20, left: 20 }}
                valueFormat=">-.0f"
                colors={{ scheme: "category10" }}
                borderWidth={1}
                borderColor="#fff"
                labelColor="#333"
                beforeSeparatorLength={30}
                afterSeparatorLength={30}
                beforeSeparatorOffset={15}
                afterSeparatorOffset={15}
                currentPartSizeExtension={10}
                motionConfig="gentle"
            />
        </Box>
    );
};

export default FunnelChart;