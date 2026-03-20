import { defineStore } from 'pinia'
import {
  extractAuthToken,
  fetchProtectedSession,
  loginUser,
  registerUser,
} from '@/services/auth.service'
import { clearToken, getToken, persistToken } from '@/services/token.service'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getToken(),
    user: null,
    status: 'idle',
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
  },
  actions: {
    syncTokenFromStorage() {
      const storedToken = getToken()

      if (storedToken !== this.token) {
        this.token = storedToken

        if (!storedToken) {
          this.user = null
        }
      }

      return storedToken
    },
    setToken(token) {
      this.token = token

      if (token) {
        persistToken(token)
        return
      }

      clearToken()
    },
    async login(credentials) {
      this.status = 'loading'

      try {
        const { data } = await loginUser(credentials)
        const token = extractAuthToken(data)

        if (!token) {
          throw new Error('We could not sign you in. Please try again.')
        }

        this.user = data.user ? { email: data.user } : { email: credentials.email }
        this.setToken(token)

        return data
      } finally {
        this.status = 'idle'
      }
    },
    async register(payload) {
      this.status = 'loading'

      try {
        const { data } = await registerUser(payload)
        const token = extractAuthToken(data)

        if (!token) {
          throw new Error('We could not create your account. Please try again.')
        }

        this.user = { email: payload.email }
        this.setToken(token)

        return data
      } finally {
        this.status = 'idle'
      }
    },
    async refreshSession() {
      const token = this.syncTokenFromStorage()

      if (!token) {
        return null
      }

      try {
        const { data } = await fetchProtectedSession()
        this.user = data.user ? { email: data.user } : this.user
        return data
      } catch (error) {
        this.logout()
        throw error
      }
    },
    logout() {
      this.user = null
      this.setToken('')
    },
  },
})
