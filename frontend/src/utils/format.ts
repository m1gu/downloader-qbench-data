import { format, parseISO } from 'date-fns'

export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) return null
  try {
    return parseISO(value)
  } catch {
    return null
  }
}

export function formatDateInput(date: Date): string {
  return format(date, 'yyyy-MM-dd')
}

export function formatDateLabel(date: Date): string {
  return format(date, 'MMM dd')
}

export function formatDateTimeLabel(date: Date | null): string {
  if (!date) return '--'
  return format(date, 'yyyy-MM-dd HH:mm')
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return new Intl.NumberFormat('en-US').format(value)
}

export function formatHoursToDuration(hours: number | null | undefined): string {
  if (hours === null || hours === undefined || Number.isNaN(hours) || hours <= 0) {
    return '--'
  }

  const totalHours = Math.round(hours)
  const days = Math.floor(totalHours / 24)
  const remainingHours = totalHours % 24

  if (days > 0) {
    return `${days} d ${remainingHours} h`
  }

  return `${remainingHours} h`
}
