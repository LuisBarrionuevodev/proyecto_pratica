import { Grid, Card, CardContent, Typography } from "@mui/material";
import type { ReactNode } from "react";

interface ChartCardProps {
    title: string;
    children: ReactNode;
}


const ChartCard = ({ title, children }: ChartCardProps) => (
    <Card
        sx={{
            bgcolor: "#2B2E34",
            borderRadius: 3,
            boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
            p: 2,
            minWidth:"260px",
            height: "90%",
            transition: "0.3s",
            "&:hover": {
                boxShadow: "0 15px 40px rgba(0,0,0,0.08)",

            }
        }
    }
            >
        <Typography variant="h6" sx={{ color: "white", mb: 2, fontWeight: 600 }}>
            {title}
        </Typography>
        <CardContent sx={{ p: 0 }}>
            {children}
        </CardContent>
    </Card >
);

export default ChartCard;