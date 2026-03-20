const defaultStorageKey = 'wallabot_auth_token'

export const getTokenStorageKey = () =>
  import.meta.env.VITE_AUTH_TOKEN_STORAGE_KEY || defaultStorageKey

export const getToken = () => {
  if (typeof window === 'undefined') {
    return ''
  }

  return window.localStorage.getItem(getTokenStorageKey()) || ''
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
