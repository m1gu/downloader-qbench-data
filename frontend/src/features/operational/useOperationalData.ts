import * as React from 'react'
import type { OperationalData, OperationalFilters } from './types'
import { fetchOperationalData } from './api'

type OperationalState = {
  data: OperationalData | null
  loading: boolean
  error: string | null
}

const initialState: OperationalState = {
  data: null,
  loading: false,
  error: null,
}

export function useOperationalData(filters: OperationalFilters) {
  const [state, setState] = React.useState<OperationalState>(initialState)

  const refresh = React.useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetchOperationalData(filters)
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
