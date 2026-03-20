import axios from 'axios'
import { clearToken, getToken } from '@/services/token.service'

const timeout = Number(import.meta.env.VITE_API_TIMEOUT_MS || 10000)
const fallbackBaseUrl = import.meta.env.VITE_API_BASE_URL || ''

const trimLeadingSlashes = (value = '') => value.replace(/^\/+/, '')
const trimTrailingSlashes = (value = '') => value.replace(/\/+$/, '')

const isLocalDevApi = (baseURL) => {
  if (!import.meta.env.DEV || !baseURL) {
    return false
  }

  try {
    const url = new URL(baseURL)
    return ['localhost', '127.0.0.1'].includes(url.hostname)
  } catch {
    return false
  }
}

const resolveBaseUrl = (baseURL) => (isLocalDevApi(baseURL) ? '' : baseURL)
const resolveServiceBaseUrl = (baseURL, pathPrefix = '') => {
  const normalizedBaseUrl = trimTrailingSlashes(resolveBaseUrl(baseURL))
  const normalizedPathPrefix = trimLeadingSlashes(pathPrefix)

  if (!normalizedPathPrefix) {
    return normalizedBaseUrl
  }

  if (!normalizedBaseUrl) {
    return `/${normalizedPathPrefix}`
  }

  return `${normalizedBaseUrl}/${normalizedPathPrefix}`
}

const hasAuthorizationHeader = (headers) => {
  if (typeof headers?.get === 'function') {
    return Boolean(headers.get('Authorization'))
  }

  return Boolean(headers?.Authorization || headers?.authorization)
}

const setAuthorizationHeader = (headers, token) => {
  if (typeof headers?.set === 'function') {
    headers.set('Authorization', `Bearer ${token}`)
    return headers
  }

  return {
    ...(headers || {}),
    Authorization: `Bearer ${token}`,
  }
}

const createApiClient = ({ baseURL = fallbackBaseUrl, pathPrefix = '' } = {}) => {
  const client = axios.create({
    baseURL: resolveServiceBaseUrl(baseURL, pathPrefix),
    timeout,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  client.interceptors.request.use((config) => {
    const token = getToken()

    if (token && !config.skipAuth && !hasAuthorizationHeader(config.headers)) {
      config.headers = setAuthorizationHeader(config.headers, token)
    }

    return config
  })

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401 && !error.config?.skipAuth) {
        clearToken()
      }

      return Promise.reject(error)
    },
  )

  return client
}

export const apiClient = createApiClient()
export const authApiClient = createApiClient({
  baseURL: import.meta.env.VITE_API_AUTH_URL || fallbackBaseUrl,
  pathPrefix: 'auth',
})
export const inventoryApiClient = createApiClient({
  baseURL: import.meta.env.VITE_API_INVENTORY_URL || fallbackBaseUrl,
  pathPrefix: 'api/v1',
})
export const transactionApiClient = createApiClient({
  baseURL: import.meta.env.VITE_API_TRANSACTION_URL || fallbackBaseUrl,
})
