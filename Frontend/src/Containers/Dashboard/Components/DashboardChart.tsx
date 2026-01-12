import { Card, CardContent, Typography } from "@mui/material";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const data = [
  { name: "Ene", actu: 40 },
  { name: "Feb", actu: 55 },
  { name: "Mar", actu: 90 },
  { name: "Abr", actu: 75 },
  { name: "May", actu: 120 },
];

export default function DashboardChart() {
  return (
    <Card sx={{ borderRadius: 3, width: {sm: "550px",md:"800px"} }}>
      <CardContent>
        <Typography variant="h6" mb={2}>
          Actuaciones por mes
        </Typography>

        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="actu" stroke="#1976d2" strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
