import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { BaseButtonStub, BaseCardStub, BaseInputStub, deferred, flushPromises } from '@/test/stubs'
import RegisterView from '@/views/RegisterView.vue'

const routerState = vi.hoisted(() => ({
  push: vi.fn(),
}))

const authState = vi.hoisted(() => ({
  register: vi.fn(),
}))

const toastState = vi.hoisted(() => ({
  success: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: routerState.push,
  }),
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    register: authState.register,
  }),
}))

vi.mock('@/stores/toast', () => ({
  useToastStore: () => toastState,
}))

const mountView = () =>
  mount(RegisterView, {
    global: {
      stubs: {
        BaseButton: BaseButtonStub,
        BaseCard: BaseCardStub,
        BaseInput: BaseInputStub,
      },
    },
  })

describe('RegisterView', () => {
  it('keeps email full-width inside the responsive desktop form grid', () => {
    const wrapper = mountView()
    const form = wrapper.find('form')
    const inputs = wrapper.findAll('label')

    expect(form.classes()).toContain('responsive-form')
    expect(form.classes()).toContain('responsive-form--desktop-two')
    expect(inputs[0].classes()).toContain('form-field--full')
  })

  it('shows inline validation errors for email format and password length', async () => {
    const wrapper = mountView()
    const inputs = wrapper.findAll('input')

    await inputs[0].setValue('bad-email')
    await inputs[1].setValue('short')
    await inputs[2].setValue('short')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Enter a valid email.')
    expect(wrapper.text()).toContain('Use at least 8 characters.')
    expect(authState.register).not.toHaveBeenCalled()
  })

  it('registers, disables submit while pending, and redirects to products', async () => {
    const pendingRequest = deferred()
    authState.register.mockReturnValueOnce(pendingRequest.promise)

    const wrapper = mountView()
    const inputs = wrapper.findAll('input')

    await inputs[0].setValue(' seller@example.com ')
    await inputs[1].setValue('secret123')
    await inputs[2].setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(authState.register).toHaveBeenCalledWith({
      email: 'seller@example.com',
      password: 'secret123',
    })

    pendingRequest.resolve()
    await flushPromises()

    expect(toastState.success).toHaveBeenCalledWith('Your account is ready.')
    expect(routerState.push).toHaveBeenCalledWith('/products')
  })
})
