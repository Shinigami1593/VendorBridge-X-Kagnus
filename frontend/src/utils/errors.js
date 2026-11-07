export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error.response?.data
  if (error.response?.status === 403) return 'You do not have permission to do that.'
  if (error.response?.status === 404) return 'The requested item could not be found.'
  if (typeof data?.error === 'string') return data.error
  if (typeof data?.detail === 'string') return data.detail
  if (typeof data?.message === 'string') return data.message
  if (Array.isArray(data?.non_field_errors)) return data.non_field_errors.join(' ')
  const fieldMessages = Object.entries(data || {})
    .filter(([key]) => !['error', 'detail', 'message', 'non_field_errors'].includes(key))
    .flatMap(([key, value]) => {
      if (typeof value === 'string') return [`${key.replaceAll('_', ' ')}: ${value}`]
      if (Array.isArray(value)) return value.filter((message) => typeof message === 'string').map((message) => `${key.replaceAll('_', ' ')}: ${message}`)
      return []
    })
  if (fieldMessages.length) return fieldMessages.join(' ')
  return fallback
}

export function getFieldErrors(error) {
  const data = error.response?.data || {}
  return Object.fromEntries(
    Object.entries(data)
      .filter(([key, value]) => !['error', 'detail', 'non_field_errors'].includes(key) && (Array.isArray(value) || typeof value === 'string'))
      .map(([key, value]) => [key, Array.isArray(value) ? value.join(' ') : value]),
  )
}
