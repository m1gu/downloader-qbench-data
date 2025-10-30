import { parseISO, subDays } from 'date-fns'
import * as React from 'react'
import { ResponsiveHeatMap } from '@nivo/heatmap'
import type { DefaultHeatMapDatum, HeatMapSerie, TooltipProps } from '@nivo/heatmap'
import {
  formatApiDateTimeUtc,
  formatDateInput,
  formatDateLabel,
  formatDateTimeLabel,
  formatHoursToDuration,
  formatNumber,
} from '../../utils/format'
import type { PriorityFilters } from './types'
import { usePriorityOrders } from './usePriorityOrders'
import './priority.css'
import '../overview/overview.css'

const LOOKBACK_DAYS = 30
const DEFAULT_MIN_DAYS = 4
const DEFAULT_SLA_HOURS = 120

type FormState = Pick<PriorityFilters, 'minDaysOverdue' | 'slaHours'>

function computeRange() {
  const end = new Date()
  end.setUTCHours(23, 59, 59, 999)
  const start = subDays(new Date(end), LOOKBACK_DAYS - 1)
  start.setUTCHours(0, 0, 0, 0)
  return {
    from: formatApiDateTimeUtc(start),
    to: formatApiDateTimeUtc(end),
  }
}

export function PriorityOrdersTab() {
  const initialRange = React.useMemo(computeRange, [])
  const [formState, setFormState] = React.useState<FormState>({
    minDaysOverdue: DEFAULT_MIN_DAYS,
    slaHours: DEFAULT_SLA_HOURS,
  })
  const [filters, setFilters] = React.useState<PriorityFilters>({
    dateFrom: initialRange.from,
    dateTo: initialRange.to,
    interval: 'day',
    minDaysOverdue: DEFAULT_MIN_DAYS,
    slaHours: DEFAULT_SLA_HOURS,
  })
  const { data, loading, error, refresh } = usePriorityOrders(filters)
  const [lastUpdated, setLastUpdated] = React.useState<Date | null>(null)

  React.useEffect(() => {
    if (data) {
      setLastUpdated(new Date())
    }
  }, [data])

  const applyFilters = React.useCallback(() => {
    const range = computeRange()
    const nextFilters: PriorityFilters = {
      dateFrom: range.from,
      dateTo: range.to,
      interval: 'day',
      minDaysOverdue: formState.minDaysOverdue,
      slaHours: formState.slaHours,
    }

    const unchanged =
      filters.dateFrom === nextFilters.dateFrom &&
      filters.dateTo === nextFilters.dateTo &&
      filters.minDaysOverdue === nextFilters.minDaysOverdue &&
      filters.slaHours === nextFilters.slaHours

    if (unchanged) {
      void refresh()
    } else {
      setFilters(nextFilters)
    }
  }, [filters, formState.minDaysOverdue, formState.slaHours, refresh])

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target
    const parsed = Number.parseInt(value || '0', 10)
    setFormState((prev) => ({
      ...prev,
      [name]: Number.isNaN(parsed) ? prev[name as keyof FormState] : parsed,
    }))
  }

  const heatmapData = React.useMemo(() => data?.heatmap ?? { periods: [], customers: [] }, [data])
  const heatmapKeys = React.useMemo(() => [...heatmapData.periods], [heatmapData.periods])
  const heatmapRows = React.useMemo(() => {
    if (!heatmapData.customers.length) return [] as HeatMapSerie<DefaultHeatMapDatum, Record<string, never>>[]
    return heatmapData.customers.map((customer) => ({
      id: customer.customerName,
      data: heatmapKeys.map((period) => ({
        x: period,
        y: customer.data[period] ?? 0,
      })),
    })) as HeatMapSerie<DefaultHeatMapDatum, Record<string, never>>[]
  }, [heatmapData.customers, heatmapKeys])

  const hasHeatmap = heatmapRows.length > 0
  const heatmapHeight = React.useMemo(() => {
    if (!heatmapRows.length) return 360
    const baseHeight = 360
    const rowHeight = 48
    const totalRows = heatmapRows.length
    return Math.max(baseHeight, totalRows * rowHeight)
  }, [heatmapRows.length])
  const rangeLabel = React.useMemo(() => {
    try {
      const from = formatDateInput(parseISO(filters.dateFrom))
      const to = formatDateInput(parseISO(filters.dateTo))
      return `${from} - ${to}`
    } catch {
      return `${filters.dateFrom} - ${filters.dateTo}`
    }
  }, [filters.dateFrom, filters.dateTo])
  const lastUpdatedLabel = lastUpdated ? `${formatDateTimeLabel(lastUpdated)}` : '--'

  return (
    <div className="overview">
      <section className="priority__controls">
        <div className="priority__control-meta">
          <span className="priority__meta-label">
            Range:
            <strong> {rangeLabel}</strong>
          </span>
          <span className="priority__meta-label">
            Last refresh:
            <strong> {lastUpdatedLabel}</strong>
          </span>
        </div>
        <div className="priority__control-inputs">
          <label className="priority__field">
            <span>Minimum days overdue</span>
            <input
              type="number"
              name="minDaysOverdue"
              min={0}
              step={1}
              value={formState.minDaysOverdue}
              onChange={handleInputChange}
            />
          </label>
          <label className="priority__field">
            <span>SLA (hours)</span>
            <input
              type="number"
              name="slaHours"
              min={0}
              step={1}
              value={formState.slaHours}
              onChange={handleInputChange}
            />
          </label>
          <button className="priority__refresh" type="button" onClick={applyFilters} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </section>

      {error && <div className="overview__error">Failed to load priority orders: {error}</div>}

      <section className="overview__kpis priority__kpi-grid">
        <KpiCard label="Overdue orders" value={formatNumber(data?.kpis.totalOverdue ?? null)} />
        <KpiCard label="Beyond SLA" value={formatNumber(data?.kpis.overdueBeyondSla ?? null)} accent="alert" />
      </section>

      <section className="priority__grid">
        <div className="overview__card">
          <CardHeader title="Most overdue orders" subtitle={`Top overdue orders for the last ${LOOKBACK_DAYS} days`} />
          <div className="overview__table-wrapper priority__table">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Open time</th>
                  <th>SLA breach</th>
                </tr>
              </thead>
              <tbody>
                {data?.topOrders.length ? (
                  data.topOrders.map((order) => (
                    <tr key={order.id} className={order.slaBreached ? 'priority__order-row--breach' : undefined}>
                      <td className="priority__order-ref">{order.reference}</td>
                      <td>{order.customer}</td>
                      <td>{order.state !== '--' ? <span className="priority__state">{order.state}</span> : '--'}</td>
                      <td>{formatDateTimeLabel(order.createdAt)}</td>
                      <td>{formatHoursToDuration(order.openHours)}</td>
                      <td>
                        <span
                          className={
                            order.slaBreached ? 'priority__sla-chip priority__sla-chip--breach' : 'priority__sla-chip'
                          }
                        >
                          {order.slaBreached ? 'Yes' : 'No'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyTable loading={loading} colSpan={6} />
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overview__card">
          <CardHeader title="Ready to report samples" subtitle="Samples with all tests ready for reporting" />
          <div className="overview__table-wrapper priority__table">
            <table>
              <thead>
                <tr>
                  <th>Sample</th>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Completed</th>
                  <th>Tests</th>
                </tr>
              </thead>
              <tbody>
                {data?.readySamples.length ? (
                  data.readySamples.map((sample) => (
                    <tr key={sample.id}>
                      <td>{sample.name}</td>
                      <td className="priority__order-ref">{sample.orderReference}</td>
                      <td>{sample.customer}</td>
                      <td>{formatDateTimeLabel(sample.completedAt)}</td>
                      <td>
                        {sample.testsDone}/{sample.testsTotal}
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyTable loading={loading} colSpan={5} />
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overview__card overview__card--full">
          <CardHeader title="Overdue heatmap (customers × period)" subtitle="Weekly hotspots of overdue orders" />
          <div className="priority__heatmap" style={{ height: heatmapHeight }}>
            {hasHeatmap ? (
              <ResponsiveHeatMap
                data={heatmapRows}
                margin={{ top: 50, right: 60, bottom: 80, left: 160 }}
                colors={{
                  type: 'sequential',
                  colors: ['#0f172a', '#1e3a8a', '#6366f1', '#f472b6', '#be123c', '#7f1d1d'],
                }}
                axisTop={{
                  tickSize: 5,
                  tickPadding: 5,
                  tickRotation: -45,
                  legend: '',
                  legendOffset: 0,
                  format: (value) => formatDateLabel(parseISO(String(value))),
                }}
                axisRight={null}
                axisBottom={null}
                axisLeft={{
                  tickSize: 5,
                  tickPadding: 5,
                  tickRotation: 0,
                }}
                enableGridX
                enableGridY
                labelTextColor="rgba(255, 255, 255, 0.85)"
                borderWidth={1}
                borderColor="rgba(3, 6, 15, 0.2)"
                emptyColor="rgba(255, 255, 255, 0.2)"
                theme={heatmapTheme}
                tooltip={HeatmapTooltip}
                animate={false}
              />
            ) : (
              <EmptyState loading={loading} />
            )}
          </div>
        </div>

      </section>
    </div>
  )
}

const heatmapTheme = {
  axis: {
    ticks: {
      text: {
        fill: '#a8b3d1',
        fontSize: 12,
      },
    },
    legend: {
      text: {
        fill: '#a8b3d1',
        fontSize: 12,
      },
    },
  },
  legends: {
    text: {
      fill: '#a8b3d1',
      fontSize: 12,
    },
  },
  tooltip: {
    container: {
      background: '#0f1d3b',
      color: '#f4f7ff',
      fontSize: 12,
      borderRadius: 12,
    },
  },
}

const HeatmapTooltip: React.FC<TooltipProps<DefaultHeatMapDatum>> = ({ cell }) => (
  <div className="priority__heatmap-tooltip">
    <strong>{cell.serieId}</strong>
    <div>{formatDateLabel(parseISO(String(cell.data.x)))}</div>
    <div>{cell.value ? `${cell.value} overdue` : 'No overdue orders'}</div>
  </div>
)

type KpiCardProps = {
  label: string
  value: string
  caption?: string
  accent?: 'default' | 'alert'
}

function KpiCard({ label, value, caption, accent = 'default' }: KpiCardProps) {
  const className = accent === 'alert' ? 'overview__kpi overview__kpi--highlight' : 'overview__kpi'
  return (
    <div className={className}>
      <span className="overview__kpi-label">{label}</span>
      <span className="overview__kpi-value">{value}</span>
      {caption && <span className="overview__kpi-subtitle">{caption}</span>}
    </div>
  )
}

type CardHeaderProps = {
  title: string
  subtitle?: string
}

function CardHeader({ title, subtitle }: CardHeaderProps) {
  return (
    <header className="overview__card-header">
      <h2>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
    </header>
  )
}

function EmptyState({ loading }: { loading: boolean }) {
  return <div className="overview__empty">{loading ? 'Loading data...' : 'No data available for the selected range'}</div>
}

function EmptyTable({ loading, colSpan }: { loading: boolean; colSpan: number }) {
  return (
    <tr>
      <td colSpan={colSpan} className="overview__empty">
        {loading ? 'Loading...' : 'No records'}
      </td>
    </tr>
  )
}
