import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiState = vi.hoisted(() => ({
  authRootApiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('@/services/api', () => apiState)

describe('user service', () => {
  beforeEach(async () => {
    vi.resetModules()
    vi.clearAllMocks()
    const { clearUserProfileCache } = await import('@/services/user.service')
    clearUserProfileCache()
  })

  it('loads and normalizes a public user profile', async () => {
    const { getUserProfile } = await import('@/services/user.service')

    apiState.authRootApiClient.get.mockResolvedValueOnce({
      data: {
        active_listing_count: 3,
        avg_rating: '4.5',
        member_since: '2026-04-01T00:00:00Z',
        username: 'seller@example.com',
      },
    })

    await expect(getUserProfile(7)).resolves.toEqual({
      active_listing_count: 3,
      avg_rating: 4.5,
      id: 7,
      member_since: '2026-04-01T00:00:00Z',
      username: 'seller@example.com',
    })
    expect(apiState.authRootApiClient.get).toHaveBeenCalledWith('/users/7/profile', {
      skipAuth: true,
    })
  })

  it('loads paginated received reviews', async () => {
    const { listUserReviews } = await import('@/services/user.service')

    apiState.authRootApiClient.get.mockResolvedValueOnce({
      data: [
        {
          created_at: '2026-04-02T00:00:00Z',
          reviewer_username: 'buyer@example.com',
          review_text: 'Great seller.',
          stars: 5,
        },
      ],
    })

    await expect(listUserReviews(7, { page: 2, perPage: 10 })).resolves.toEqual([
      {
        created_at: '2026-04-02T00:00:00Z',
        reviewer_username: 'buyer@example.com',
        review_text: 'Great seller.',
        stars: 5,
      },
    ])
    expect(apiState.authRootApiClient.get).toHaveBeenCalledWith('/users/7/ratings', {
      params: {
        limit: 10,
        skip: 10,
      },
      skipAuth: true,
    })
  })

  it('loads and normalizes active profile listings', async () => {
    const { listUserProducts } = await import('@/services/user.service')

    apiState.authRootApiClient.get.mockResolvedValueOnce({
      data: [
        {
          category: 'Furniture',
          condition: 'Good',
          id: 42,
          price: '149.99',
          seller_id: 'seller@example.com',
          state: 'Available',
          title: 'Oak side table',
        },
      ],
    })

    await expect(listUserProducts(7)).resolves.toEqual([
      expect.objectContaining({
        category: 'Furniture',
        condition: 'Good',
        id: 42,
        price: 149.99,
        seller_id: 'seller@example.com',
        state: 'Available',
        title: 'Oak side table',
      }),
    ])
    expect(apiState.authRootApiClient.get).toHaveBeenCalledWith('/users/7/products', {
      skipAuth: true,
    })
  })

  it('creates a rating with the backend payload shape', async () => {
    const { createUserRating } = await import('@/services/user.service')

    apiState.authRootApiClient.post.mockResolvedValueOnce({
      data: {
        rating_id: 123,
      },
    })

    await createUserRating({
      reviewText: 'Smooth pickup.',
      stars: 4,
      toUserId: 7,
      transactionId: 9001,
    })

    expect(apiState.authRootApiClient.post).toHaveBeenCalledWith('/ratings', {
      review_text: 'Smooth pickup.',
      stars: 4,
      to_user_id: 7,
      transaction_id: 9001,
    })
  })

  it('resolves an email profile through the public username lookup', async () => {
    const { resolveUserProfile } = await import('@/services/user.service')

    apiState.authRootApiClient.get.mockResolvedValueOnce({
      data: {
        id: 2,
        username: 'seller@example.com',
        avg_rating: 4,
      },
    })

    await expect(resolveUserProfile('seller@example.com')).resolves.toMatchObject({
      avg_rating: 4,
      id: 2,
      username: 'seller@example.com',
    })
    expect(apiState.authRootApiClient.get).toHaveBeenCalledWith('/users/resolve', {
      params: {
        username: 'seller@example.com',
      },
      skipAuth: true,
    })
  })

  it('returns null when a username cannot be resolved', async () => {
    const { resolveUserProfile } = await import('@/services/user.service')

    apiState.authRootApiClient.get.mockRejectedValueOnce({
      response: {
        status: 404,
      },
    })

    await expect(resolveUserProfile('missing@example.com')).resolves.toBeNull()
  })
})
