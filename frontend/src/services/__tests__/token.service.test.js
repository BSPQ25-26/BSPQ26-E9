import { beforeEach, describe, expect, it, vi } from 'vitest'

const encodeBase64Url = (value) =>
  window
    .btoa(JSON.stringify(value))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')

const makeJwt = (payload) => `header.${encodeBase64Url(payload)}.signature`

describe('token service', () => {
  beforeEach(() => {
    vi.resetModules()
    window.localStorage.clear()
  })

  it('returns a stored JWT that has not expired', async () => {
    const { getToken, getTokenStorageKey } = await import('@/services/token.service')
    const token = makeJwt({
      sub: 'seller@example.com',
      exp: Math.floor(Date.now() / 1000) + 3600,
    })

    window.localStorage.setItem(getTokenStorageKey(), token)

    expect(getToken()).toBe(token)
  })

  it('clears expired tokens instead of treating them as authenticated sessions', async () => {
    const { getToken, getTokenStorageKey } = await import('@/services/token.service')
    const token = makeJwt({
      sub: 'seller@example.com',
      exp: Math.floor(Date.now() / 1000) - 60,
    })

    window.localStorage.setItem(getTokenStorageKey(), token)

    expect(getToken()).toBe('')
    expect(window.localStorage.getItem(getTokenStorageKey())).toBeNull()
  })

  it('clears malformed tokens instead of treating them as authenticated sessions', async () => {
    const { getToken, getTokenStorageKey } = await import('@/services/token.service')

    window.localStorage.setItem(getTokenStorageKey(), 'not-a-jwt')

    expect(getToken()).toBe('')
    expect(window.localStorage.getItem(getTokenStorageKey())).toBeNull()
  })
})
