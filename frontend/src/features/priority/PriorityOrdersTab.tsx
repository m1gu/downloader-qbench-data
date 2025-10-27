import { parseISO, subDays } from 'date-fns'
import * as React from 'react'
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ResponsiveHeatMap } from '@nivo/heatmap'
import type { DefaultHeatMapDatum, HeatMapSerie, TooltipProps } from '@nivo/heatmap'
import { formatDateInput, formatDateLabel, formatDateTimeLabel, formatHoursToDuration, formatNumber } from '../../utils/format'
import '../overview/overview.css'
import '../operational/operational.css'
import './priority.css'
import type { IntervalOption, PriorityFilters } from './types'
import { usePriorityOrders } from './usePriorityOrders'

const INTERVAL_OPTIONS: Array<{ value: IntervalOption; label: string }> = [
  { value: 'day', label: 'Daily' },
  { value: 'week', label: 'Weekly' },
]

const DEFAULT_MIN_DAYS = 5
const DEFAULT_SLA_HOURS = 240
const PRIORITY_LOOKBACK_DAYS = 30

function createInitialFilters(): PriorityFilters {
  const now = new Date()
  const utcToday = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const from = subDays(utcToday, PRIORITY_LOOKBACK_DAYS)
  return {
    dateFrom: formatDateInput(from),
    dateTo: formatDateInput(utcToday),
    interval: 'day',
    minDaysOverdue: DEFAULT_MIN_DAYS,
    slaHours: DEFAULT_SLA_HOURS,
  }
}

export function PriorityOrdersTab() {
  const initialFilters = React.useMemo(createInitialFilters, [])
  const [formFilters, setFormFilters] = React.useState<PriorityFilters>(initialFilters)
  const [filters, setFilters] = React.useState<PriorityFilters>(initialFilters)

  const { data, loading, error, refresh } = usePriorityOrders(filters)

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target
    setFormFilters((prev) => ({
      ...prev,
      [name]:
        name === 'minDaysOverdue' || name === 'slaHours'
          ? Number.parseInt(value || '0', 10)
          : value,
    }))
  }

  const handleRefresh = () => {
    const isSame =
      formFilters.dateFrom === filters.dateFrom &&
      formFilters.dateTo === filters.dateTo &&
      formFilters.interval === filters.interval &&
      formFilters.minDaysOverdue === filters.minDaysOverdue &&
      formFilters.slaHours === filters.slaHours

    if (isSame) {
      void refresh()
    } else {
      setFilters(formFilters)
    }
  }

  const timeline = data?.timeline ?? []
  const heatmap = data?.heatmap

  const heatmapKeys = React.useMemo(() => (heatmap ? [...heatmap.periods] : []), [heatmap])
  const heatmapRows = React.useMemo(() => {
    if (!heatmap || !heatmap.customers.length) {
      return [] as HeatMapSerie<DefaultHeatMapDatum, Record<string, never>>[]
    }
    const rows = heatmap.customers.map((customer) => {
      return {
        id: customer.customerName,
        data: heatmapKeys.map((period) => ({
          x: period,
          y: customer.data[period] ?? 0,
        })),
      }
    }) as HeatMapSerie<DefaultHeatMapDatum, Record<string, never>>[]
    return rows
  }, [heatmap, heatmapKeys])
  const hasHeatmap = heatmapRows.length > 0

  const heatmapTheme = React.useMemo(
    () => ({
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
    }),
    [],
  )

  const HeatmapTooltip: React.FC<TooltipProps<DefaultHeatMapDatum>> = ({ cell }) => (
    <div className="priority__heatmap-tooltip">
      <strong>{cell.serieId}</strong>
      <div>{formatDateLabel(parseISO(String(cell.data.x)))}</div>
      <div>{cell.value ? `${cell.value} overdue` : 'No overdue orders'}</div>
    </div>
  )

  return (
    <div className="overview">
      <section className="overview__controls">
        <div className="overview__control-group">
          <label className="overview__control">
            <span>From</span>
            <input
              type="date"
              name="dateFrom"
              value={formFilters.dateFrom}
              max={formFilters.dateTo}
              onChange={handleInputChange}
            />
          </label>
          <label className="overview__control">
            <span>To</span>
            <input
              type="date"
              name="dateTo"
              value={formFilters.dateTo}
              min={formFilters.dateFrom}
              onChange={handleInputChange}
            />
          </label>
          <label className="overview__control">
            <span>Interval</span>
            <select name="interval" value={formFilters.interval} onChange={handleInputChange}>
              {INTERVAL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="overview__control">
            <span>Min days overdue</span>
            <input
              type="number"
              name="minDaysOverdue"
              min={0}
              value={formFilters.minDaysOverdue}
              onChange={handleInputChange}
            />
          </label>
          <label className="overview__control">
            <span>SLA hours</span>
            <input
              type="number"
              name="slaHours"
              min={0}
              value={formFilters.slaHours}
              onChange={handleInputChange}
            />
          </label>
          <button className="overview__refresh-button" type="button" onClick={handleRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="overview__status">
          <span>Interval: {filters.interval === 'week' ? 'Weekly' : 'Daily'}</span>
          <span>Min overdue: {filters.minDaysOverdue} days</span>
          <span>SLA: {formatHoursToDuration(filters.slaHours)}</span>
        </div>
      </section>

      {error && <div className="overview__error">Failed to load priority orders: {error}</div>}

      <section className="overview__kpis">
        <KpiCard
          label="Overdue orders"
          value={formatNumber(data?.kpis.totalOverdue ?? null)}
          caption="Orders beyond the minimum overdue days"
        />
        <KpiCard
          label="Beyond SLA"
          value={formatNumber(data?.kpis.overdueBeyondSla ?? null)}
          caption="Overdue orders beyond the SLA threshold"
          accent="alert"
        />
        <KpiCard
          label="Within SLA"
          value={formatNumber(data?.kpis.overdueWithinSla ?? null)}
          caption="Overdue but still within SLA"
        />
        <KpiCard
          label="Avg open time"
          value={formatHoursToDuration(data?.kpis.averageOpenHours ?? null)}
          caption="Average open hours for overdue orders"
        />
      </section>

      <section className="overview__grid priority__grid">
        <div className="overview__card overview__card--full">
          <CardHeader title="Overdue orders timeline" subtitle="Total overdue orders per interval" />
          <div className="overview__chart">
            {timeline.length ? (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.08)" />
                  <XAxis dataKey="label" stroke="var(--color-text-secondary)" />
                  <YAxis stroke="var(--color-text-secondary)" tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#0f1d3b', borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)' }}
                    labelStyle={{ color: '#f4f7ff' }}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="overdueOrders"
                    name="Overdue orders"
                    stroke="#F85149"
                    fill="rgba(248, 81, 73, 0.45)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState loading={loading} />
            )}
          </div>
        </div>

        <div className="overview__card">
          <CardHeader title="Most overdue orders" subtitle="Top orders ranked by open time" />
          <div className="overview__table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Open time</th>
                </tr>
              </thead>
              <tbody>
                {data?.topOrders.length ? (
                  data.topOrders.map((order) => (
                    <tr key={order.id}>
                      <td className="operational__order-ref">{order.reference}</td>
                      <td>
                        <div>{order.customer}</div>
                        {order.createdAt && (
                          <div className="operational__table-subtle">
                            Created {formatDateTimeLabel(order.createdAt)}
                          </div>
                        )}
                      </td>
                      <td>{order.state !== '--' ? <span className="priority__state">{order.state}</span> : '--'}</td>
                      <td>{formatHoursToDuration(order.openHours)}</td>
                    </tr>
                  ))
                ) : (
                  <EmptyTable loading={loading} colSpan={4} />
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overview__card">
          <CardHeader title="Ready to report samples" subtitle="Samples with tests ready to be reported" />
          <div className="overview__table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Sample</th>
                  <th>Order</th>
                  <th>Customer</th>
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
                      <td>
                        {sample.testsDone}/{sample.testsTotal}
                      </td>
                    </tr>
                  ))
                ) : (
                  <EmptyTable loading={loading} colSpan={4} />
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overview__card">
          <CardHeader title="Warning orders" subtitle="Orders approaching the overdue threshold" />
          <div className="overview__table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Status</th>
                  <th>Age</th>
                </tr>
              </thead>
              <tbody>
                {data?.warningOrders.length ? (
                  data.warningOrders.map((order) => (
                    <tr key={order.id}>
                      <td className="operational__order-ref">{order.reference}</td>
                      <td>{order.customer}</td>
                      <td>{order.state !== '--' ? <span className="priority__state">{order.state}</span> : '--'}</td>
                      <td>{formatHoursToDuration(order.openHours)}</td>
                    </tr>
                  ))
                ) : (
                  <EmptyTable loading={loading} colSpan={4} />
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="overview__card overview__card--full">
          <CardHeader title="Overdue heatmap" subtitle="Weekly overdue orders by customer" />
          <div className="priority__heatmap">
            {hasHeatmap ? (
              <ResponsiveHeatMap
                data={heatmapRows}
                margin={{ top: 50, right: 60, bottom: 80, left: 160 }}
                colors={{ type: 'sequential', scheme: 'reds' }}
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
                borderColor="rgba(3, 6, 15, 0.2)"
                emptyColor="rgba(255, 255, 255, 0.06)"
                valueFormat={(value) => (value ? `${value}` : '')}
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
