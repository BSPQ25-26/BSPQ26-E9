import { authApiClient } from '@/services/api'

const socialLoginRedirectStorageKey = 'wallabot_social_login_redirect'
const supportedSocialProviders = new Set(['google', 'facebook'])

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

const resolveBrowserAuthBaseUrl = () => {
  const configuredBaseUrl = import.meta.env.VITE_API_AUTH_URL || import.meta.env.VITE_API_BASE_URL || ''

  if (isLocalDevApi(configuredBaseUrl)) {
    return ''
  }

  return trimTrailingSlashes(configuredBaseUrl)
}

const normalizeProvider = (provider) => String(provider || '').trim().toLowerCase()

export const extractAuthToken = (payload) =>
  payload?.access_token ||
  payload?.accessToken ||
  payload?.token ||
  payload?.session?.access_token ||
  ''

export const loginUser = (credentials) =>
  authApiClient.post('/login', credentials, { skipAuth: true })

export const registerUser = (payload) =>
  authApiClient.post('/register', payload, { skipAuth: true })

export const fetchProtectedSession = () => authApiClient.get('/protected')

export const getSocialLoginUrl = (provider) => {
  const normalizedProvider = normalizeProvider(provider)

  if (!supportedSocialProviders.has(normalizedProvider)) {
    throw new Error(`Unsupported social login provider: ${provider}`)
  }

  return `${resolveBrowserAuthBaseUrl()}/auth/${normalizedProvider}`
}

export const persistSocialLoginRedirect = (redirectTarget) => {
  if (typeof window === 'undefined' || !redirectTarget) {
    return
  }

  try {
    window.sessionStorage.setItem(socialLoginRedirectStorageKey, redirectTarget)
  } catch {
    // Session storage can be unavailable in some browser modes.
  }
}

export const consumeSocialLoginRedirect = () => {
  if (typeof window === 'undefined') {
    return ''
  }

  try {
    const redirectTarget = window.sessionStorage.getItem(socialLoginRedirectStorageKey) || ''
    window.sessionStorage.removeItem(socialLoginRedirectStorageKey)
    return redirectTarget
  } catch {
    return ''
  }
}

export const beginSocialLogin = (provider, redirectTarget) => {
  const loginUrl = getSocialLoginUrl(provider)

  persistSocialLoginRedirect(redirectTarget)

  if (typeof window !== 'undefined') {
    window.location.assign(loginUrl)
  }

  return loginUrl
}
