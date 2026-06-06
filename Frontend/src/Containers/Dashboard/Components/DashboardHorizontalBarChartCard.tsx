import { Box } from "@mui/material";

import type { DashboardRankingChartItem } from "./DashboardRankingBarChart";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";
import { DashboardRankingBarChart } from "./DashboardRankingBarChart";

type Props = {
  title: string;
  items: DashboardRankingChartItem[];
  loading?: boolean;
  emptyMessage?: string;
  maxItems?: number;
  color?: string;
};

/**
 * Card analytics con ranking en barras horizontales (reemplaza listas manuales).
 */
export function DashboardHorizontalBarChartCard({
  title,
  items,
  loading = false,
  emptyMessage,
  maxItems,
  color,
}: Props) {
  return (
    <Box sx={{ width: "100%", display: "flex", flex: 1 }}>
      <DashboardAnalyticsChartCard title={title} loading={loading} fillHeight>
        <DashboardRankingBarChart
          items={items}
          loading={loading}
          emptyMessage={emptyMessage}
          maxItems={maxItems}
          color={color}
        />
      </DashboardAnalyticsChartCard>
    </Box>
  );
}
