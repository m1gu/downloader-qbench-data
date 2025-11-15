import * as React from 'react'
import type { TatFilters, SlowReportedOrdersData } from './types'
import { fetchSlowReportedOrders } from './api'

type TatState = {
  data: SlowReportedOrdersData | null
  loading: boolean
  error: string | null
}

const initialState: TatState = { data: null, loading: false, error: null }

export function useTatOrders(filters: TatFilters, options: { lookbackDays?: number }) {
  const cacheKey = React.useMemo(() => JSON.stringify({ ...filters, lookbackDays: options.lookbackDays }), [filters, options.lookbackDays])
  const [state, setState] = React.useState<TatState>(() => initialState)

  const refresh = React.useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetchSlowReportedOrders({
        dateFrom: filters.dateFrom,
        dateTo: filters.dateTo,
        customerQuery: filters.customerQuery,
        minOpenHours: filters.minOpenHours,
        thresholdHours: filters.thresholdHours,
        lookbackDays: options.lookbackDays,
      })
      setState({ data: response, loading: false, error: null })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      setState((prev) => ({ data: prev.data, loading: false, error: message }))
    }
  }, [filters, options.lookbackDays])

  React.useEffect(() => {
    void refresh()
  }, [refresh])

  return { ...state, refresh }
}
