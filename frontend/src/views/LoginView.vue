<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useAuth } from '@/composables/useAuth'
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
const route = useRoute()
const router = useRouter()
const { login } = useAuth()
const toastStore = useToastStore()

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

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

    const redirectTarget =
      typeof route.query.redirect === 'string' ? route.query.redirect : '/products'

    await router.push(redirectTarget)
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
        Use your email and password to continue.
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
          <BaseButton :disabled="isSubmitting" block type="submit">
            {{ isSubmitting ? 'Signing in...' : 'Sign in' }}
          </BaseButton>
        </div>
      </form>
    </BaseCard>
  </section>
</template>
