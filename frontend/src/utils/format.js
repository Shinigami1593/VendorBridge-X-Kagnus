const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
})

const dateFormatter = new Intl.DateTimeFormat('en-IN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const dateTimeFormatter = new Intl.DateTimeFormat('en-IN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatMoney(value) {
  const amount = Number(value)
  return Number.isFinite(amount) ? moneyFormatter.format(amount) : '—'
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : dateFormatter.format(date)
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : dateTimeFormatter.format(date)
}

export function timeAgo(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  const seconds = Math.round((date.getTime() - Date.now()) / 1000)
  const units = [
    ['year', 31536000],
    ['month', 2592000],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]

  for (const [unit, length] of units) {
    const amount = Math.round(Math.abs(seconds) / length)
    if (amount >= 1) {
      return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(
        seconds < 0 ? -amount : amount,
        unit,
      )
    }
  }

  return 'just now'
}

export function formatCompactMoney(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '—'

  const absoluteAmount = Math.abs(amount)
  const [divisor, suffix] = absoluteAmount >= 10000000
    ? [10000000, 'Cr']
    : absoluteAmount >= 100000
      ? [100000, 'L']
      : absoluteAmount >= 1000
        ? [1000, 'K']
        : [1, '']
  const compact = amount / divisor
  const formatted = new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 1,
  }).format(compact)

  return `${formatted}${suffix ? ` ${suffix}` : ''}`
}
