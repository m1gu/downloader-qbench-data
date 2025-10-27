export type IntervalOption = 'day' | 'week'

export interface PriorityFilters {
  dateFrom: string
  dateTo: string
  interval: IntervalOption
  minDaysOverdue: number
  slaHours: number
}

export interface PriorityKpis {
  totalOverdue: number
  overdueBeyondSla: number
  overdueWithinSla: number
  averageOpenHours: number | null
  maxOpenHours: number | null
  percentOverdueVsActive: number
}

export interface OverdueOrder {
  id: number
  reference: string
  customer: string
  state: string
  createdAt: Date | null
  openHours: number
  slaBreached: boolean
}

export interface WarningOrder extends OverdueOrder {}

export interface ReadySample {
  id: number
  name: string
  orderReference: string
  customer: string
  completedAt: Date | null
  testsDone: number
  testsTotal: number
}

export interface TimelinePoint {
  date: Date
  label: string
  overdueOrders: number
}

export interface HeatmapCustomer {
  customerName: string
  data: Record<string, number>
  total: number
}

export interface HeatmapData {
  periods: string[]
  customers: HeatmapCustomer[]
}

export interface StateBreakdownItem {
  state: string
  count: number
  ratio: number
}

export interface PriorityOrdersData {
  kpis: PriorityKpis
  topOrders: OverdueOrder[]
  warningOrders: WarningOrder[]
  readySamples: ReadySample[]
  timeline: TimelinePoint[]
  heatmap: HeatmapData
  stateBreakdown: StateBreakdownItem[]
}
