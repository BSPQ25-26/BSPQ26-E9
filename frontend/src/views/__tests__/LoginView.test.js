import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BaseButtonStub, BaseCardStub, BaseInputStub, deferred, flushPromises } from '@/test/stubs'
import LoginView from '@/views/LoginView.vue'

const routerState = vi.hoisted(() => ({
  push: vi.fn(),
  route: {
    query: {},
  },
}))

const authState = vi.hoisted(() => ({
  login: vi.fn(),
}))

const toastState = vi.hoisted(() => ({
  success: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerState.route,
  useRouter: () => ({
    push: routerState.push,
  }),
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    login: authState.login,
  }),
}))

vi.mock('@/stores/toast', () => ({
  useToastStore: () => toastState,
}))

const mountView = () =>
  mount(LoginView, {
    global: {
      stubs: {
        BaseButton: BaseButtonStub,
        BaseCard: BaseCardStub,
        BaseInput: BaseInputStub,
      },
    },
  })

describe('LoginView', () => {
  beforeEach(() => {
    routerState.route.query = {}
  })

  it('renders the responsive two-column form shell', () => {
    const wrapper = mountView()
    const form = wrapper.find('form')

    expect(form.classes()).toContain('responsive-form')
    expect(form.classes()).toContain('responsive-form--desktop-two')
  })

  it('shows inline validation errors for invalid input', async () => {
    const wrapper = mountView()
    const inputs = wrapper.findAll('input')

    await inputs[0].setValue('not-an-email')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Enter a valid email.')
    expect(wrapper.text()).toContain('Enter your password.')
    expect(authState.login).not.toHaveBeenCalled()
  })

  it('logs in, disables submit while pending, and redirects to the requested route', async () => {
    routerState.route.query = {
      redirect: '/products/new/create',
    }

    const pendingRequest = deferred()
    authState.login.mockReturnValueOnce(pendingRequest.promise)

    const wrapper = mountView()
    const inputs = wrapper.findAll('input')

    await inputs[0].setValue(' seller@example.com ')
    await inputs[1].setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.find('button[type=\"submit\"]').attributes('disabled')).toBeDefined()
    expect(authState.login).toHaveBeenCalledWith({
      email: 'seller@example.com',
      password: 'secret123',
    })

    pendingRequest.resolve()
    await flushPromises()

    expect(toastState.success).toHaveBeenCalledWith('You are signed in.')
    expect(routerState.push).toHaveBeenCalledWith('/products/new/create')
  })
})
