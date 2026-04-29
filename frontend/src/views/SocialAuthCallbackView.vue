<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import {
  consumeSocialLoginRedirect,
  extractAuthToken,
} from '@/services/auth.service'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const toastStore = useToastStore()
const hasError = ref(false)
const statusMessage = ref('Completing sign in...')

const getFirstQueryValue = (value) => (Array.isArray(value) ? value[0] : value)

const normalizeRedirectTarget = (value) =>
  typeof value === 'string' && value.startsWith('/') ? value : '/products'

const readTokenPayload = () => ({
  access_token: getFirstQueryValue(route.query.access_token),
  accessToken: getFirstQueryValue(route.query.accessToken),
  token: getFirstQueryValue(route.query.token),
  token_type: getFirstQueryValue(route.query.token_type),
})

const completeSocialLogin = async () => {
  try {
    const authError = getFirstQueryValue(route.query.error)

    if (authError) {
      throw new Error(authError)
    }

    const token = extractAuthToken(readTokenPayload())

    if (!token) {
      throw new Error('Missing social login token')
    }

    authStore.setToken(token)
    toastStore.success('You are signed in.')

    await router.replace(normalizeRedirectTarget(consumeSocialLoginRedirect()))
  } catch {
    authStore.logout()
    hasError.value = true
    statusMessage.value = 'We could not finish social sign in.'
  }
}

onMounted(completeSocialLogin)
</script>

<template>
  <section class="page-shell auth-shell callback-shell">
    <BaseCard
      class="auth-card callback-card"
      title="Social sign in"
      :description="statusMessage"
    >
      <BaseButton
        v-if="hasError"
        to="/login"
        variant="secondary"
      >
        Back to sign in
      </BaseButton>
    </BaseCard>
  </section>
</template>

<style scoped>
.callback-shell {
  max-width: 34rem;
}

.callback-card :deep(.base-button) {
  margin-top: var(--space-5);
}
</style>
