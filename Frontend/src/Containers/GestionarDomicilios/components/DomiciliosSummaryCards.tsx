import { Box, Card, CardContent, Typography } from "@mui/material";

interface DomiciliosSummaryCardsProps {
  nomenclaturaCount: number;
  geolocalizacionCount: number;
}

const DomiciliosSummaryCards = ({
  nomenclaturaCount,
  geolocalizacionCount,
}: DomiciliosSummaryCardsProps) => {
  const total = nomenclaturaCount + geolocalizacionCount;

  return (
    <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", marginBottom: 2 }}>
      <Card sx={{ minWidth: 220 }}>
        <CardContent>
          <Typography variant="subtitle2">Pendientes nomenclatura</Typography>
          <Typography variant="h5">{nomenclaturaCount}</Typography>
        </CardContent>
      </Card>
      <Card sx={{ minWidth: 220 }}>
        <CardContent>
          <Typography variant="subtitle2">Pendientes geolocalización</Typography>
          <Typography variant="h5">{geolocalizacionCount}</Typography>
        </CardContent>
      </Card>
      <Card sx={{ minWidth: 220 }}>
        <CardContent>
          <Typography variant="subtitle2">Total pendientes</Typography>
          <Typography variant="h5">{total}</Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default DomiciliosSummaryCards;
