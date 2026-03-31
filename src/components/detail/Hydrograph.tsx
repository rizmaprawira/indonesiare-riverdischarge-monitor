import { Suspense, lazy, useMemo } from 'react';
import type { PointSeries } from '../../types';
import { formatDateShort } from '../../lib/format';
import styles from './Hydrograph.module.css';

const ReactECharts = lazy(() => import('echarts-for-react'));

interface HydrographProps {
  series: PointSeries;
}

export function Hydrograph({ series }: HydrographProps) {
  const option = useMemo(() => {
    const xAxisLabels = series.dates.map((date) => formatDateShort(date));

    return {
      grid: { left: 52, right: 20, top: 24, bottom: 40 },
      tooltip: {
        trigger: 'axis',
        formatter: (params: { dataIndex: number; value: number }[]) => {
          const param = params[0];
          const date = series.dates[param.dataIndex];
          return `<strong>${formatDateShort(date)}</strong><br/>Discharge: ${param.value?.toFixed(1) ?? 'N/A'} m³/s`;
        },
      },
      xAxis: {
        type: 'category',
        data: xAxisLabels,
        name: 'Date',
        nameLocation: 'middle',
        nameGap: 28,
      },
      yAxis: {
        type: 'value',
        name: 'Discharge (m³/s)',
        nameLocation: 'middle',
        nameGap: 44,
      },
      series: [
        {
          name: 'Discharge',
          type: 'line',
          data: series.values,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2.5,
            color: '#133B70',
          },
          itemStyle: {
            color: '#133B70',
          },
          areaStyle: {
            color: 'rgba(19, 59, 112, 0.12)',
          },
        },
      ],
    };
  }, [series]);

  return (
    <div className={styles.chart}>
      <Suspense fallback={<div className={styles.loading}>Loading chart…</div>}>
        <ReactECharts option={option} style={{ width: '100%', height: '280px' }} />
      </Suspense>
    </div>
  );
}
