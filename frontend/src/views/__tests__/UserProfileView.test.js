import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { i18n } from '@/i18n'
import { BaseButtonStub, BaseCardStub, flushPromises } from '@/test/stubs'
import UserProfileView from '@/views/UserProfileView.vue'

const routerState = vi.hoisted(() => ({
  route: {
    params: {
      id: '7',
    },
  },
}))

const userState = vi.hoisted(() => ({
  listUserProducts: vi.fn(),
  listUserReviews: vi.fn(),
  resolveUserProfile: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerState.route,
}))

vi.mock('@/services/user.service', () => ({
  listUserProducts: userState.listUserProducts,
  listUserReviews: userState.listUserReviews,
  resolveUserProfile: userState.resolveUserProfile,
}))

vi.mock('@/services/product.service', () => ({
  resolveProductImageUrl: vi.fn((image) => image),
}))

const mountView = () =>
  mount(UserProfileView, {
    global: {
      plugins: [i18n],
      stubs: {
        BaseButton: BaseButtonStub,
        BaseCard: BaseCardStub,
      },
    },
  })

describe('UserProfileView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routerState.route = {
      params: {
        id: '7',
      },
    }
    i18n.global.locale.value = 'en'
    userState.listUserProducts.mockResolvedValue([])
  })

  it('renders the profile summary, listings, and received reviews', async () => {
    userState.resolveUserProfile.mockResolvedValueOnce({
      active_listing_count: 2,
      avg_rating: 4.5,
      id: 7,
      member_since: '2026-04-01T00:00:00Z',
      username: 'seller@example.com',
    })
    userState.listUserProducts.mockResolvedValueOnce([
      {
        category: 'Furniture',
        condition: 'Good',
        id: 42,
        images: ['/uploads/table.png'],
        price: 149.99,
        state: 'Available',
        title: 'Oak side table',
      },
    ])
    userState.listUserReviews.mockResolvedValueOnce([
      {
        created_at: '2026-04-03T00:00:00Z',
        reviewer_username: 'buyer@example.com',
        review_text: 'Clear communication.',
        stars: 5,
      },
    ])

    const wrapper = mountView()
    await flushPromises()

    expect(userState.resolveUserProfile).toHaveBeenCalledWith('7')
    expect(userState.listUserReviews).toHaveBeenCalledWith(7, {
      page: 1,
      perPage: 5,
    })
    expect(userState.listUserProducts).toHaveBeenCalledWith(7)
    expect(wrapper.text()).toContain('seller@example.com')
    expect(wrapper.text()).toContain('2 active listings')
    expect(wrapper.text()).toContain('4.5')
    expect(wrapper.text()).not.toContain('Public profile')
    expect(wrapper.text()).toContain('Oak side table')
    expect(wrapper.text()).toContain('$149.99')
    expect(wrapper.text()).toContain('buyer@example.com')
    expect(wrapper.text()).toContain('Clear communication.')
    expect(wrapper.text().indexOf('Oak side table')).toBeLessThan(
      wrapper.text().indexOf('Received reviews'),
    )
  })

  it('shows a limited public profile when an email cannot be matched to a user id', async () => {
    routerState.route = {
      params: {
        id: 'seller@example.com',
      },
    }
    userState.resolveUserProfile.mockResolvedValueOnce(null)

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('seller@example.com')
    expect(wrapper.text()).toContain('Limited profile')
    expect(wrapper.text()).toContain('Reviews are unavailable')
    expect(wrapper.text()).toContain('Listings are unavailable')
    expect(userState.listUserProducts).not.toHaveBeenCalled()
    expect(userState.listUserReviews).not.toHaveBeenCalled()
  })
})
