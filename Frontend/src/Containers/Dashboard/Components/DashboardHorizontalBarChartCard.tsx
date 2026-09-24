import { Box } from "@mui/material";

import type { DashboardRankingBarItem } from "./DashboardRankingBarList";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";
import { DashboardRankingBarList } from "./DashboardRankingBarList";

type Props = {
  title: string;
  items: DashboardRankingBarItem[];
  emptyMessage?: string;
  maxItems?: number;
  color?: string;
};

/**
 * Card analytics con ranking legible (etiqueta + barra + valor).
 */
export function DashboardHorizontalBarChartCard({
  title,
  items,
  emptyMessage,
  maxItems = 7,
  color,
}: Props) {
  return (
    <Box sx={{ width: "100%", display: "flex", flex: 1 }}>
      <DashboardAnalyticsChartCard title={title} fillHeight>
        <DashboardRankingBarList
          items={items}
          emptyMessage={emptyMessage}
          maxItems={maxItems}
          color={color}
        />
      </DashboardAnalyticsChartCard>
    </Box>
  );
}
