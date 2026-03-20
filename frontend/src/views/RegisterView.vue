<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useAuth } from '@/composables/useAuth'
import { useToastStore } from '@/stores/toast'
import { createFieldErrors, normalizeApiFormError } from '@/utils/api-errors'

const router = useRouter()
const { register } = useAuth()
const toastStore = useToastStore()

const form = reactive({
  confirmPassword: '',
  email: '',
  password: '',
})

const fieldErrors = reactive(
  createFieldErrors(['email', 'password', 'confirmPassword']),
)
const formError = ref('')
const isSubmitting = ref(false)
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const passwordMinLength = 8

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

  if (field === 'password') {
    if (!value) {
      fieldErrors.password = 'Create a password.'
      return false
    }

    if (value.length < passwordMinLength) {
      fieldErrors.password = `Use at least ${passwordMinLength} characters.`
      return false
    }

    fieldErrors.password = ''

    if (form.confirmPassword && form.confirmPassword !== form.password) {
      fieldErrors.confirmPassword = 'These passwords do not match.'
      return false
    }

    if (fieldErrors.confirmPassword === 'These passwords do not match.') {
      fieldErrors.confirmPassword = ''
    }

    return true
  }

  if (!value) {
    fieldErrors.confirmPassword = 'Enter your password again.'
    return false
  }

  if (form.confirmPassword !== form.password) {
    fieldErrors.confirmPassword = 'These passwords do not match.'
    return false
  }

  fieldErrors.confirmPassword = ''
  return true
}

const validateForm = () =>
  ['email', 'password', 'confirmPassword'].map(validateField).every(Boolean)

const handleSubmit = async () => {
  formError.value = ''

  if (!validateForm()) {
    return
  }

  isSubmitting.value = true

  try {
    await register({
      email: form.email.trim(),
      password: form.password,
    })

    toastStore.success('Your account is ready.')
    await router.push('/products')
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      ['email', 'password'],
      'We could not create your account right now. Please try again in a moment.',
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
      <h1>Create your account.</h1>
      <p class="muted">
        It only takes a minute.
      </p>
    </div>

    <BaseCard
      class="auth-card"
      title="Start selling in a few steps"
      description="Add your email and choose a password."
    >
      <form class="responsive-form responsive-form--desktop-two" novalidate @submit.prevent="handleSubmit">
        <BaseInput
          class="form-field form-field--full"
          :model-value="form.email"
          autocomplete="email"
          :error="fieldErrors.email"
          label="Email"
          name="email"
          placeholder="seller@example.com"
          required
          type="email"
          @blur="validateField('email')"
          @update:model-value="setFieldValue('email', $event)"
        />

        <BaseInput
          class="form-field"
          :model-value="form.password"
          autocomplete="new-password"
          :error="fieldErrors.password"
          label="Create password"
          name="password"
          placeholder="At least 8 characters"
          required
          type="password"
          @blur="validateField('password')"
          @update:model-value="setFieldValue('password', $event)"
        />

        <BaseInput
          class="form-field"
          :model-value="form.confirmPassword"
          autocomplete="new-password"
          :error="fieldErrors.confirmPassword"
          label="Repeat password"
          name="confirm-password"
          placeholder="Enter it again"
          required
          type="password"
          @blur="validateField('confirmPassword')"
          @update:model-value="setFieldValue('confirmPassword', $event)"
        />

        <p class="muted form-hint">
          Use at least {{ passwordMinLength }} characters.
        </p>

        <p v-if="formError" class="status-message error">
          {{ formError }}
        </p>

        <div class="form-actions">
          <BaseButton :disabled="isSubmitting" block type="submit">
            {{ isSubmitting ? 'Creating account...' : 'Create account' }}
          </BaseButton>
        </div>
      </form>
    </BaseCard>
  </section>
</template>
