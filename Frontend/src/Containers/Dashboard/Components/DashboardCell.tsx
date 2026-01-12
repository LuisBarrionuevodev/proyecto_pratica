import { Box, Typography } from "@mui/material";
import { PieChart, Pie, Cell } from "recharts";

const rubrosData = [
    { name: "Panaderia", value: 6 },
    { name: "Carniceria", value: 30 },
    { name: "Drugstore", value: 15 },
    { name: "Kiosco", value: 8 },
    { name: "Fiambreria", value: 35 },
    { name: "Otros", value: 10 },
];

const colors = ['#8884d8', '#83a6ed', '#8dd1e1', '#82ca9d', '#a4de6c', 'url(#pattern-checkers)'];

const renderValueLabel = (props: any) => {
    const { cx, cy, midAngle, outerRadius, value } = props;
    const RADIAN = Math.PI / 180;
    const radius = outerRadius + 25;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
        <text
            className="pie-label"
            x={x}
            y={y}
            fill="#000"
            textAnchor={x > cx ? "start" : "end"}
            dominantBaseline="central"
            fontSize={14}
            fontWeight="bold"
        >
            {value}
        </text>
    );
};

const renderLabel = (props: any) => {
    const { name, cx, cy, midAngle, innerRadius, outerRadius } = props;

    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
        <text
            className="pie-label"
            x={x}
            y={y}
            fill="#000"
            textAnchor="middle"
            dominantBaseline="text-before-edge"
            fontSize={14}
            fontWeight="bold"
        >
            {`${name}`}
        </text>
    );
};

const RubrosPieChart = ({ isAnimationActive = true }) => {
    return (
        <Box sx={{display:"flex", flexDirection:"column",alignItems:"center",
            width:{xs:"300px", sm:"500px"}, aspectRatio:1
        }}>
            <Typography  fontSize={"20px"} fontWeight={500} color="#000000de">
                Rubros Clausurados
            </Typography>
            <PieChart
                className="pie-label"
                style={{
                    width: "100%",
                    maxWidth: "400px",
                    maxHeight: "700vh",
                    aspectRatio: 1,
                }}
            >

                <Pie
                    data={rubrosData}
                    dataKey="value"
                    label={renderValueLabel}
                    labelLine={{ stroke: "#000", strokeWidth: 3 }}
                    isAnimationActive={isAnimationActive}
                >
                    {rubrosData.map((_entry, index) => (
                        <Cell key={index} fill={colors[index]} />
                    ))}
                </Pie>

                <Pie
                    data={rubrosData}
                    dataKey="value"
                    innerRadius={50}
                    label={renderLabel}
                    isAnimationActive={false}
                    fill="transparent"
                />
            </PieChart>
        </Box>
    );
};

export default RubrosPieChart;