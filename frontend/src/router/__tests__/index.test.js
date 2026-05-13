import { beforeEach, describe, expect, it } from 'vitest'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores'
import { getTokenStorageKey } from '@/services/token.service'

const encodeBase64Url = (value) =>
  window
    .btoa(JSON.stringify(value))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')

const makeJwt = (payload) => `header.${encodeBase64Url(payload)}.signature`

describe('router auth guard', () => {
  beforeEach(async () => {
    window.localStorage.clear()

    const authStore = useAuthStore(pinia)
    authStore.$reset()

    await router.push('/login')
    await router.isReady()
  })

  it('redirects unauthenticated users away from products', async () => {
    await router.push('/products')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/products')
  })

  it('allows products when a non-expired token is present', async () => {
    const token = makeJwt({
      sub: 'seller@example.com',
      exp: Math.floor(Date.now() / 1000) + 3600,
    })

    window.localStorage.setItem(getTokenStorageKey(), token)

    await router.push('/products')

    expect(router.currentRoute.value.path).toBe('/products')
  })
})
