export const createFieldErrors = (fields) =>
  Object.fromEntries(fields.map((field) => [field, '']))

export const normalizeApiFormError = (error, fields, fallbackMessage) => {
  const fieldErrors = createFieldErrors(fields)
  const payload = error?.response?.data
  const detail = payload?.detail
  const errorCode = error?.code
  let formError = ''
  let hasFieldErrors = false

  if (Array.isArray(detail)) {
    detail.forEach((issue) => {
      const field = Array.isArray(issue?.loc)
        ? issue.loc.find((part) => fields.includes(part))
        : ''

      if (field && !fieldErrors[field]) {
        fieldErrors[field] = issue?.msg || fallbackMessage
        hasFieldErrors = true
        return
      }

      if (!formError && typeof issue?.msg === 'string') {
        formError = issue.msg
      }
    })
  } else if (typeof detail === 'string') {
    formError = detail
  }

  if (!formError && typeof payload?.message === 'string') {
    formError = payload.message
  }

  if (!formError && error?.message === 'Network Error') {
    formError = 'We cannot reach the service right now. Please try again in a moment.'
  }

  if (!formError && [502, 503, 504].includes(error?.response?.status)) {
    formError = 'We cannot reach the service right now. Please try again in a moment.'
  }

  if (!formError && errorCode === 'ECONNABORTED') {
    formError = 'This is taking longer than expected. Please try again.'
  }

  if (!formError && typeof error?.message === 'string' && error.message !== 'Network Error') {
    formError = error.message
  }

  if (!formError && !hasFieldErrors) {
    formError = fallbackMessage
  }

  return {
    fieldErrors,
    formError,
  }
}
