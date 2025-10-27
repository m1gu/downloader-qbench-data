import * as React from 'react'
import type { PriorityFilters, PriorityOrdersData } from './types'
import { fetchPriorityOrders } from './api'

type PriorityState = {
  data: PriorityOrdersData | null
  loading: boolean
  error: string | null
}

const initialState: PriorityState = {
  data: null,
  loading: false,
  error: null,
}

export function usePriorityOrders(filters: PriorityFilters) {
  const [state, setState] = React.useState<PriorityState>(initialState)

  const refresh = React.useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetchPriorityOrders(filters)
      setState({
        data: response,
        loading: false,
        error: null,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      setState({
        data: null,
        loading: false,
        error: message,
      })
    }
  }, [filters])

  React.useEffect(() => {
    void refresh()
  }, [refresh])

  return { ...state, refresh }
}
