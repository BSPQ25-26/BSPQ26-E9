<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useAuth } from '@/composables/useAuth'
import { beginSocialLogin } from '@/services/auth.service'
import { useToastStore } from '@/stores/toast'
import { createFieldErrors, normalizeApiFormError } from '@/utils/api-errors'

const form = reactive({
  email: '',
  password: '',
})

const fieldErrors = reactive(
  createFieldErrors(['email', 'password']),
)
const formError = ref('')
const isSubmitting = ref(false)
const isRedirectingProvider = ref('')
const route = useRoute()
const router = useRouter()
const { login } = useAuth()
const toastStore = useToastStore()

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const socialProviders = [
  {
    id: 'google',
    label: 'Google',
  },
  {
    id: 'facebook',
    label: 'Facebook',
  },
]

const redirectTarget = computed(() =>
  typeof route.query.redirect === 'string' ? route.query.redirect : '/products',
)
const isSocialLoginPending = computed(() => Boolean(isRedirectingProvider.value))

const setFieldValue = (field, value) => {
  form[field] = value
  fieldErrors[field] = ''
  formError.value = ''
}

const validateField = (field) => {
  const value = form[field].trim()

  if (field === 'email') {
    if (!value) {
      fieldErrors.email = 'Enter your email.'
      return false
    }

    if (!emailPattern.test(value)) {
      fieldErrors.email = 'Enter a valid email.'
      return false
    }

    fieldErrors.email = ''
    return true
  }

  if (!value) {
    fieldErrors.password = 'Enter your password.'
    return false
  }

  fieldErrors.password = ''
  return true
}

const validateForm = () => ['email', 'password'].map(validateField).every(Boolean)

const handleSocialLogin = (provider) => {
  formError.value = ''
  isRedirectingProvider.value = provider

  try {
    beginSocialLogin(provider, redirectTarget.value)
  } catch {
    isRedirectingProvider.value = ''
    formError.value = 'We could not start social sign in. Please try again.'
  }
}

const getSocialButtonLabel = (provider) =>
  isRedirectingProvider.value === provider.id
    ? `Opening ${provider.label}...`
    : `Continue with ${provider.label}`

const handleSubmit = async () => {
  formError.value = ''

  if (!validateForm()) {
    return
  }

  isSubmitting.value = true

  try {
    await login({
      email: form.email.trim(),
      password: form.password,
    })

    toastStore.success('You are signed in.')

    await router.push(redirectTarget.value)
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      ['email', 'password'],
      'We could not sign you in. Check your details and try again.',
    )

    Object.assign(fieldErrors, normalizedError.fieldErrors)
    formError.value = normalizedError.formError
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="page-shell auth-shell">
    <div class="page-hero">
      <h1>Sign in to keep browsing and selling.</h1>
      <p class="muted">
        Use the account you prefer to continue.
      </p>
    </div>

    <BaseCard
      class="auth-card"
      title="Good to see you again"
      description="Enter your details below."
    >
      <form class="responsive-form responsive-form--desktop-two" novalidate @submit.prevent="handleSubmit">
        <BaseInput
          class="form-field"
          :model-value="form.email"
          autocomplete="email"
          :error="fieldErrors.email"
          label="Email"
          name="email"
          placeholder="you@example.com"
          required
          type="email"
          @blur="validateField('email')"
          @update:model-value="setFieldValue('email', $event)"
        />

        <BaseInput
          class="form-field"
          :model-value="form.password"
          autocomplete="current-password"
          :error="fieldErrors.password"
          label="Password"
          name="password"
          placeholder="Your password"
          required
          type="password"
          @blur="validateField('password')"
          @update:model-value="setFieldValue('password', $event)"
        />

        <p v-if="formError" class="status-message error">
          {{ formError }}
        </p>

        <div class="form-actions">
          <BaseButton :disabled="isSubmitting || isSocialLoginPending" block type="submit">
            {{ isSubmitting ? 'Signing in...' : 'Sign in' }}
          </BaseButton>
        </div>
      </form>

      <div class="auth-divider" aria-hidden="true">
        <span>or</span>
      </div>

      <div class="social-login" aria-label="Social sign in options">
        <BaseButton
          v-for="provider in socialProviders"
          :key="provider.id"
          class="social-login__button"
          :data-testid="`social-login-${provider.id}`"
          :disabled="isSubmitting || isSocialLoginPending"
          block
          type="button"
          variant="secondary"
          @click="handleSocialLogin(provider.id)"
        >
          <span
            class="social-login__icon"
            aria-hidden="true"
          >
            <svg
              v-if="provider.id === 'google'"
              viewBox="0 0 18 18"
              role="img"
            >
              <path fill="#4285f4" d="M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.482h4.844a4.14 4.14 0 0 1-1.796 2.716v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615" />
              <path fill="#34a853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.331A9 9 0 0 0 9 18" />
              <path fill="#fbbc05" d="M3.964 10.711A5.4 5.4 0 0 1 3.682 9c0-.594.103-1.17.282-1.711V4.958H.957A9 9 0 0 0 0 9c0 1.452.348 2.827.957 4.042z" />
              <path fill="#ea4335" d="M9 3.579c1.321 0 2.508.454 3.44 1.346l2.582-2.581C13.463.892 11.426 0 9 0A9 9 0 0 0 .957 4.958l3.007 2.331C4.672 5.162 6.656 3.58 9 3.58" />
            </svg>
            <svg
              v-else-if="provider.id === 'facebook'"
              viewBox="0 0 24 24"
              role="img"
            >
              <circle cx="12" cy="12" r="12" fill="#1877f2" />
              <path fill="#fff" d="m16.671 15.469.533-3.469h-3.328V9.749c0-.949.465-1.875 1.956-1.875h1.513V4.922s-1.373-.234-2.686-.234c-2.741 0-4.533 1.661-4.533 4.669V12H7.078v3.469h3.048v8.385a12.1 12.1 0 0 0 3.75 0v-8.385z" />
            </svg>
          </span>
          <span>
            {{ getSocialButtonLabel(provider) }}
          </span>
        </BaseButton>
      </div>
    </BaseCard>
  </section>
</template>

<style scoped>
.social-login {
  display: grid;
  gap: var(--space-3);
}

.social-login :deep(.base-button) {
  justify-content: flex-start;
  min-height: 3.25rem;
}

.social-login__icon {
  display: inline-grid;
  width: 1.55rem;
  height: 1.55rem;
  flex: 0 0 auto;
  place-items: center;
  line-height: 1;
}

.social-login__icon svg {
  display: block;
  width: 100%;
  height: 100%;
}

.auth-divider {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-5) 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  font-weight: 800;
  text-transform: uppercase;
}

.auth-divider::before,
.auth-divider::after {
  display: block;
  height: 1px;
  flex: 1;
  background: var(--color-border);
  content: '';
}
</style>
