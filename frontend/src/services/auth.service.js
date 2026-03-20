import { authApiClient } from '@/services/api'

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
