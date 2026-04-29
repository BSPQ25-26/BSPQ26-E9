import { afterEach, describe, expect, it, vi } from 'vitest'

const wallabotApiClient = vi.hoisted(() => ({
  post: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  wallabotApiClient,
}))

const loadWallabotService = async ({ priceEnabled = '' } = {}) => {
  vi.resetModules()
  if (priceEnabled) {
    vi.stubEnv('VITE_WALLABOT_PRICE_ENABLED', priceEnabled)
  }

  return import('@/services/wallabot.service')
}

describe('wallabot.service', () => {
  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllEnvs()
  })

  it('does not call the price endpoint when the backend feature is disabled', async () => {
    const { recommendProductPrice } = await loadWallabotService({ priceEnabled: 'false' })

    const result = await recommendProductPrice({
      condition: 'New',
      description: 'Small framed print.',
      title: 'Print',
    })

    expect(result).toBeNull()
    expect(wallabotApiClient.post).not.toHaveBeenCalled()
  })

  it('calls the price endpoint by default', async () => {
    wallabotApiClient.post.mockResolvedValueOnce({
      data: {
        data_source: 'backend',
        price_range_max: 120,
        price_range_min: 80,
        recommended_price: 100,
      },
    })

    const { recommendProductPrice } = await loadWallabotService()

    const result = await recommendProductPrice({
      condition: 'Good',
      description: 'Solid oak table.',
      title: 'Table',
    })

    expect(wallabotApiClient.post).toHaveBeenCalledWith('/price', {
      condition: 'Good',
      description: 'Solid oak table.',
      title: 'Table',
    })
    expect(result).toEqual({
      dataSource: 'backend',
      priceRangeMax: 120,
      priceRangeMin: 80,
      recommendedPrice: 100,
    })
  })
})
