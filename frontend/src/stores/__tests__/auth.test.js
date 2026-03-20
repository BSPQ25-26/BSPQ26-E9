import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const authServiceState = vi.hoisted(() => ({
  extractAuthToken: vi.fn(),
  fetchProtectedSession: vi.fn(),
  loginUser: vi.fn(),
  registerUser: vi.fn(),
}))

vi.mock('@/services/auth.service', () => ({
  extractAuthToken: authServiceState.extractAuthToken,
  fetchProtectedSession: authServiceState.fetchProtectedSession,
  loginUser: authServiceState.loginUser,
  registerUser: authServiceState.registerUser,
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('stores the JWT in state and localStorage after login', async () => {
    const { useAuthStore } = await import('@/stores/auth')
    const { getTokenStorageKey } = await import('@/services/token.service')
    const store = useAuthStore()

    authServiceState.loginUser.mockResolvedValue({
      data: {
        access_token: 'jwt-token',
      },
    })
    authServiceState.extractAuthToken.mockReturnValue('jwt-token')

    await store.login({
      email: 'seller@example.com',
      password: 'secret123',
    })

    expect(store.token).toBe('jwt-token')
    expect(store.isAuthenticated).toBe(true)
    expect(window.localStorage.getItem(getTokenStorageKey())).toBe('jwt-token')
  })
})
