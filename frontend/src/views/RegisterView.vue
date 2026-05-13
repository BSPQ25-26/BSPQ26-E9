<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useAuth } from '@/composables/useAuth'
import { useToastStore } from '@/stores/toast'
import { createFieldErrors, normalizeApiFormError } from '@/utils/api-errors'

const { t } = useI18n()
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
      fieldErrors.email = t('register.errorEmail')
      return false
    }

    if (!emailPattern.test(value)) {
      fieldErrors.email = t('register.errorEmailInvalid')
      return false
    }

    fieldErrors.email = ''
    return true
  }

  if (field === 'password') {
    if (!value) {
      fieldErrors.password = t('register.errorPassword')
      return false
    }

    if (value.length < passwordMinLength) {
      fieldErrors.password = t('register.errorPasswordShort', { n: passwordMinLength })
      return false
    }

    fieldErrors.password = ''

    if (form.confirmPassword && form.confirmPassword !== form.password) {
      fieldErrors.confirmPassword = t('register.errorPasswordMatch')
      return false
    }

    if (fieldErrors.confirmPassword === t('register.errorPasswordMatch')) {
      fieldErrors.confirmPassword = ''
    }

    return true
  }

  if (!value) {
    fieldErrors.confirmPassword = t('register.errorPasswordAgain')
    return false
  }

  if (form.confirmPassword !== form.password) {
    fieldErrors.confirmPassword = t('register.errorPasswordMatch')
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

    toastStore.success(t('register.accountReady'))
    await router.push('/products')
  } catch (error) {
    const normalizedError = normalizeApiFormError(
      error,
      ['email', 'password'],
      t('register.errorGeneric'),
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
      <h1>{{ $t('register.heroTitle') }}</h1>
      <p class="muted">
        {{ $t('register.heroDesc') }}
      </p>
    </div>

    <BaseCard
      class="auth-card"
      :title="$t('register.cardTitle')"
      :description="$t('register.cardDesc')"
    >
      <form class="responsive-form responsive-form--desktop-two" novalidate @submit.prevent="handleSubmit">
        <BaseInput
          class="form-field form-field--full"
          :model-value="form.email"
          autocomplete="email"
          :error="fieldErrors.email"
          :label="$t('register.email')"
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
          :label="$t('register.createPassword')"
          name="password"
          :placeholder="$t('register.atLeast8')"
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
          :label="$t('register.repeatPassword')"
          name="confirm-password"
          :placeholder="$t('register.enterAgain')"
          required
          type="password"
          @blur="validateField('confirmPassword')"
          @update:model-value="setFieldValue('confirmPassword', $event)"
        />

        <p class="muted form-hint">
          {{ $t('register.minCharsHint', { n: passwordMinLength }) }}
        </p>

        <p v-if="formError" class="status-message error">
          {{ formError }}
        </p>

        <div class="form-actions">
          <BaseButton :disabled="isSubmitting" block type="submit">
            {{ isSubmitting ? $t('register.creating') : $t('register.create') }}
          </BaseButton>
        </div>
      </form>
    </BaseCard>
  </section>
</template>
