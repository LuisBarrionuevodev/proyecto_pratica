import { Card, CardContent, Typography } from "@mui/material";

interface Props {
  title: string;
  value: number;
}

export default function DashboardCards({ title, value }: Props) {
  return (
    <Card sx={{ borderRadius: 3 }}>
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary">
          {title}
        </Typography>

        <Typography variant="h4" fontWeight={600}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}
