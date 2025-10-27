import { getEnv } from './env'

const DEFAULT_API_BASE_URL = 'https://615c98lc-8000.use.devtunnels.ms/api/v1'

export const API_BASE_URL = getEnv('API_BASE_URL', getEnv('VITE_API_BASE_URL', DEFAULT_API_BASE_URL))

export const DEFAULT_DATE_RANGE_DAYS = 7
