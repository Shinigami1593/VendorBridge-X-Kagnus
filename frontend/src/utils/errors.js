export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error.response?.data
  if (error.response?.status === 403) return 'You do not have permission to do that.'
  if (typeof data?.error === 'string') return data.error
  if (typeof data?.detail === 'string') return data.detail
  return fallback
}

export function getFieldErrors(error) {
  const data = error.response?.data || {}
  return Object.fromEntries(
    Object.entries(data)
      .filter(([key, value]) => key !== 'error' && key !== 'detail' && Array.isArray(value))
      .map(([key, value]) => [key, value.join(' ')]),
  )
}
