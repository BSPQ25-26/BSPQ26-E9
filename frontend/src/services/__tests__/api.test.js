import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const axiosState = vi.hoisted(() => ({
  create: vi.fn(),
  requestHandlers: [],
  responseRejectedHandlers: [],
}))

vi.mock('axios', () => ({
  default: {
    create: axiosState.create,
  },
}))

const makeAxiosClient = () => ({
  interceptors: {
    request: {
      use: vi.fn((handler) => {
        axiosState.requestHandlers.push(handler)
      }),
    },
    response: {
      use: vi.fn((_onFulfilled, onRejected) => {
        axiosState.responseRejectedHandlers.push(onRejected)
      }),
    },
  },
})

const encodeBase64Url = (value) =>
  window
    .btoa(JSON.stringify(value))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')

const makeJwt = (payload) => `header.${encodeBase64Url(payload)}.signature`

describe('api clients', () => {
  beforeEach(() => {
    vi.resetModules()
    window.localStorage.clear()
    axiosState.requestHandlers = []
    axiosState.responseRejectedHandlers = []
    axiosState.create.mockImplementation(makeAxiosClient)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('does not send the JSON content type for multipart form uploads', async () => {
    await import('@/services/api')

    const requestInterceptor = axiosState.requestHandlers[0]
    const headers = new Headers({
      'Content-Type': 'application/json',
    })
    const formData = new FormData()
    const config = requestInterceptor({
      data: formData,
      headers,
    })

    expect(config.headers.get('Content-Type')).toBeNull()
  })

  it('preserves non-content-type headers when preparing form uploads', async () => {
    await import('@/services/api')

    const requestInterceptor = axiosState.requestHandlers[0]
    const config = requestInterceptor({
      data: new FormData(),
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    })

    expect(config.headers).toEqual({
      Accept: 'application/json',
    })
  })

  it('clears stored auth and requests login when an authenticated request receives 401', async () => {
    const { getTokenStorageKey } = await import('@/services/token.service')
    const token = makeJwt({
      sub: 'seller@example.com',
      exp: Math.floor(Date.now() / 1000) + 3600,
    })
    const authRequiredEvents = []

    window.localStorage.setItem(getTokenStorageKey(), token)
    window.location.hash = '#/products'
    window.addEventListener(
      'wallabot:auth-required',
      (event) => {
        authRequiredEvents.push(event)
      },
      { once: true },
    )

    await import('@/services/api')

    const authError = {
      config: {},
      response: {
        status: 401,
      },
    }

    await expect(axiosState.responseRejectedHandlers[0](authError)).rejects.toBe(authError)

    expect(window.localStorage.getItem(getTokenStorageKey())).toBeNull()
    expect(authRequiredEvents).toHaveLength(1)
    expect(authRequiredEvents[0].detail.redirect).toBe('/products')
  })
})
