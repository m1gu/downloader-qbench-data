import * as React from 'react'
import type { OverviewData, OverviewFilters } from './types'
import { fetchOverviewData } from './api'

type UseOverviewDataState = {
  data: OverviewData | null
  loading: boolean
  error: string | null
}

const initialState: UseOverviewDataState = {
  data: null,
  loading: false,
  error: null,
}

export function useOverviewData(filters: OverviewFilters) {
  const [{ data, loading, error }, setState] = React.useState<UseOverviewDataState>(initialState)

  const refresh = React.useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetchOverviewData(filters)
      setState({ data: response, loading: false, error: null })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setState({ data: null, loading: false, error: message })
    }
  }, [filters])

  React.useEffect(() => {
    void refresh()
  }, [refresh])

  return { data, loading, error, refresh }
}
