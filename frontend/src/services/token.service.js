const defaultStorageKey = 'wallabot_auth_token'
const tokenExpirySkewSeconds = 5

export const getTokenStorageKey = () =>
  import.meta.env.VITE_AUTH_TOKEN_STORAGE_KEY || defaultStorageKey

const decodeBase64Url = (value) => {
  const normalizedValue = String(value || '').replace(/-/g, '+').replace(/_/g, '/')
  const paddedValue = normalizedValue.padEnd(Math.ceil(normalizedValue.length / 4) * 4, '=')

  return window.atob(paddedValue)
}

export const getTokenPayload = (token) => {
  if (typeof window === 'undefined' || typeof window.atob !== 'function') {
    return null
  }

  const [, payload] = String(token || '').split('.')

  if (!payload) {
    return null
  }

  try {
    return JSON.parse(decodeBase64Url(payload))
  } catch {
    return null
  }
}

export const isUsableAuthToken = (token, now = Date.now()) => {
  const payload = getTokenPayload(token)
  const expiresAt = Number(payload?.exp)

  if (!payload || !Number.isFinite(expiresAt)) {
    return false
  }

  return expiresAt > Math.floor(now / 1000) + tokenExpirySkewSeconds
}

const getRawToken = () => {
  if (typeof window === 'undefined') {
    return ''
  }

  return window.localStorage.getItem(getTokenStorageKey()) || ''
}

export const getToken = () => {
  const token = getRawToken()

  if (!token) {
    return ''
  }

  if (!isUsableAuthToken(token)) {
    clearToken()
    return ''
  }

  return token
}

export const persistToken = (token) => {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(getTokenStorageKey(), token)
}

export const clearToken = () => {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.removeItem(getTokenStorageKey())
}
