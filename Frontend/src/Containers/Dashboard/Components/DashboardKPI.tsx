import {
    Card,
    CardContent,
    Typography,
    Box,
} from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import type { ReactNode } from "react";
import type { Periodo } from "../../../types/periodos";

interface KPIProps {
    title: string;
    value: number | string;
    percentage: number;
    icon: ReactNode;
    periodo: Periodo;
}

const KPI = ({ title, value, percentage, icon, periodo }: KPIProps) => {

    const labelPeriodo = {
        Semanal: "Semana",
        Mensual: "Mes",
        Trimestral: "Trimestre",
        Anual: "Año",
    };

    const isPositive = percentage >= 0;

    return (
        <Card
            sx={{
                borderRadius: 3,
                boxShadow: "0 4px 20px rgba(0,0,0,0.05)",
                p: 2,
                bgcolor: "#2B2E34"
            }}
        >
            <CardContent sx={{ p: 0 }}>
                {/* Header */}
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                    {icon}
                    <Typography variant="body2" fontWeight={700} color="white">
                        {title}
                    </Typography>
                </Box>

                {/* Value */}
                <Typography variant="h4" fontWeight={500} color="white">
                    {value}
                </Typography>

                {/* Percentage */}
                <Box display="flex" alignItems="center" gap={0.5} mt={1}>
                    {isPositive ? (
                        <TrendingUpIcon sx={{ fontSize: 18, color: "success.main" }} />
                    ) : (
                        <TrendingDownIcon sx={{ fontSize: 18, color: "error.main" }} />
                    )}

                    <Typography
                        variant="body2"
                        sx={{
                            color: isPositive ? "success.main" : "error.main",
                            fontWeight: 500,
                        }}
                    >
                        {percentage}%
                    </Typography>

                    <Typography variant="body2" color="white">
                        {periodo === "Semanal" ? "Última" : "Último"} {labelPeriodo[periodo]}
                    </Typography>
                </Box>
            </CardContent>
        </Card>
    );
};

export default KPI;