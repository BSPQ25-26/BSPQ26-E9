<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useAuth } from '@/composables/useAuth'
import { useToastStore } from '@/stores/toast'
import { useWalletStore } from '@/stores/wallet'

const route = useRoute()
const router = useRouter()
const { isAuthenticated, logout, user } = useAuth()
const walletStore = useWalletStore()
const toastStore = useToastStore()
const {
  balance,
  error: walletError,
  isLoading: isWalletLoading,
  isTopUpLoading,
} = storeToRefs(walletStore)

const appName = import.meta.env.VITE_APP_NAME || 'Wallabot'
const currencyFormatter = new Intl.NumberFormat('en-US', {
  currency: 'USD',
  style: 'currency',
})
const isTopUpModalOpen = ref(false)
const topUpForm = reactive({
  amount: '',
})
const topUpError = ref('')

const links = computed(() =>
  isAuthenticated.value
    ? [
        { label: 'Home', to: '/products', exact: true },
      ]
    : [
        { label: 'Sign in', to: '/login', exact: true },
        { label: 'Create account', to: '/register', exact: true },
      ],
)
const formattedBalance = computed(() => {
  if (walletError.value) {
    return 'Unavailable'
  }

  if (isWalletLoading.value) {
    return 'Loading...'
  }

  return currencyFormatter.format(balance.value)
})
const balanceButtonLabel = computed(() => {
  if (walletError.value) {
    return 'Wallet balance unavailable. Top up wallet.'
  }

  if (isWalletLoading.value) {
    return 'Wallet balance loading. Top up wallet.'
  }

  return `Wallet balance ${currencyFormatter.format(balance.value)}. Top up wallet.`
})

const visibleLinks = computed(() => links.value.filter((link) => !isLinkActive(link)))

const isLinkActive = (link) => {
  if (link.exact) {
    return route.path === link.to
  }

  return route.path === link.to || route.path.startsWith(`${link.to}/`)
}

const resolveTopUpError = (error) => {
  const detail = error?.response?.data?.detail

  if (Array.isArray(detail)) {
    const amountIssue = detail.find((issue) => issue?.loc?.includes?.('amount'))
    return amountIssue?.msg || detail[0]?.msg || 'Enter a valid amount.'
  }

  if (typeof detail === 'string') {
    return detail
  }

  if (error?.message === 'Network Error') {
    return 'We cannot reach the wallet service right now.'
  }

  return 'We could not top up your wallet. Please try again.'
}

const openTopUpModal = () => {
  topUpError.value = ''
  isTopUpModalOpen.value = true
}

const closeTopUpModal = () => {
  if (isTopUpLoading.value) {
    return
  }

  isTopUpModalOpen.value = false
  topUpForm.amount = ''
  topUpError.value = ''
}

const updateTopUpAmount = (value) => {
  topUpForm.amount = value
  topUpError.value = ''
}

const validateTopUpAmount = () => {
  const amount = Number(topUpForm.amount)

  if (!Number.isFinite(amount) || amount <= 0) {
    topUpError.value = 'Enter an amount greater than 0.'
    return null
  }

  return amount
}

const handleTopUp = async () => {
  const amount = validateTopUpAmount()

  if (amount === null) {
    return
  }

  try {
    await walletStore.topUp(amount)
    toastStore.success('Wallet topped up.')
    closeTopUpModal()
  } catch (error) {
    topUpError.value = resolveTopUpError(error)
  }
}

const handleLogout = async () => {
  logout()
  walletStore.reset()

  if (route.path !== '/login') {
    await router.push('/login')
  }
}

watch(
  isAuthenticated,
  (nextIsAuthenticated) => {
    if (!nextIsAuthenticated) {
      walletStore.reset()
      return
    }

    walletStore.fetchBalance().catch(() => {})
  },
  {
    immediate: true,
  },
)
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink class="brand" to="/">
        <img
          alt=""
          aria-hidden="true"
          class="brand-logo"
          height="48"
          src="/wallbot_icon.png"
          width="48"
        />
        <span>
          {{ appName }}
        </span>
      </RouterLink>

      <nav v-if="visibleLinks.length" class="header-nav" aria-label="Main navigation">
        <RouterLink
          v-for="link in visibleLinks"
          :key="link.to"
          class="nav-link"
          :to="link.to"
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="header-actions">
        <button
          v-if="isAuthenticated"
          class="wallet-indicator"
          type="button"
          :aria-busy="isWalletLoading"
          :aria-label="balanceButtonLabel"
          @click="openTopUpModal"
        >
          <span class="wallet-indicator__label">Wallet</span>
          <span class="wallet-indicator__balance">{{ formattedBalance }}</span>
        </button>

        <p v-if="isAuthenticated && user?.email" class="header-user muted">
          {{ user.email }}
        </p>

        <BaseButton
          v-if="isAuthenticated"
          variant="secondary"
          size="sm"
          @click="handleLogout"
        >
          Sign out
        </BaseButton>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="isTopUpModalOpen"
        class="wallet-modal-backdrop"
        role="presentation"
        @click.self="closeTopUpModal"
      >
        <section
          aria-labelledby="wallet-topup-title"
          aria-modal="true"
          class="wallet-modal"
          role="dialog"
        >
          <header class="wallet-modal__header">
            <div>
              <p class="wallet-modal__eyebrow">Wallet balance</p>
              <h2 id="wallet-topup-title">Top Up Wallet</h2>
            </div>

            <button
              class="wallet-modal__close"
              type="button"
              aria-label="Close top up wallet"
              :disabled="isTopUpLoading"
              @click="closeTopUpModal"
            >
              X
            </button>
          </header>

          <div class="wallet-modal__balance">
            <span>Current balance</span>
            <strong>{{ currencyFormatter.format(balance) }}</strong>
          </div>

          <form class="wallet-modal__form" novalidate @submit.prevent="handleTopUp">
            <BaseInput
              :model-value="topUpForm.amount"
              autocomplete="off"
              :error="topUpError"
              inputmode="decimal"
              label="Amount"
              min="0.01"
              name="wallet-topup-amount"
              placeholder="25.00"
              required
              step="0.01"
              type="number"
              @update:model-value="updateTopUpAmount"
            />

            <div class="wallet-modal__actions">
              <BaseButton
                :disabled="isTopUpLoading"
                type="button"
                variant="secondary"
                @click="closeTopUpModal"
              >
                Cancel
              </BaseButton>

              <BaseButton :disabled="isTopUpLoading" type="submit">
                {{ isTopUpLoading ? 'Adding funds...' : 'Top Up Wallet' }}
              </BaseButton>
            </div>
          </form>
        </section>
      </div>
    </Teleport>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 0.9rem 0 0.75rem;
  background: rgba(242, 241, 238, 0.96);
  box-shadow: 0 1px 0 rgba(17, 17, 17, 0.05);
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
  isolation: isolate;
}

.app-header__inner {
  width: min(var(--page-max-width), calc(100% - (var(--page-padding-inline) * 2)));
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.66);
  border-radius: calc(var(--radius-xl) - 0.2rem);
  background: rgba(255, 255, 255, 0.66);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(22px);
  min-width: 0;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  min-height: var(--tap-target-size);
  min-width: var(--tap-target-size);
  font-family: var(--font-body);
  font-size: 0.98rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.brand-logo {
  width: 2.7rem;
  height: 2.7rem;
  flex: 0 0 auto;
  object-fit: contain;
}

.header-nav {
  display: inline-flex;
  min-width: 0;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--tap-target-size);
  min-width: var(--tap-target-size);
  padding: 0.65rem 0.95rem;
  border: 1px solid transparent;
  border-radius: 1rem;
  color: var(--color-text-muted);
  background: transparent;
  font-size: 1rem;
  font-weight: 700;
  transition:
    background-color 0.24s ease,
    border-color 0.24s ease,
    color 0.24s ease,
    transform 0.24s ease;
}

.nav-link.active,
.nav-link:hover {
  background: #111111;
  border-color: #111111;
  color: #f7f6f2;
  transform: translateY(-1px);
}

.header-actions {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.wallet-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: var(--tap-target-size);
  min-width: var(--tap-target-size);
  padding: 0.55rem 0.95rem;
  border: 1px solid rgba(17, 17, 17, 0.12);
  border-radius: 1rem;
  background: #111111;
  color: #f7f6f2;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition:
    background-color 0.24s ease,
    border-color 0.24s ease,
    transform 0.24s ease;
}

.wallet-indicator:hover {
  background: var(--color-primary-strong);
  border-color: var(--color-primary-strong);
  transform: translateY(-1px);
}

.wallet-indicator__label {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  line-height: 1;
  text-transform: uppercase;
  color: rgba(247, 246, 242, 0.72);
}

.wallet-indicator__balance {
  font-size: 0.98rem;
  font-weight: 800;
  line-height: 1.1;
  white-space: nowrap;
}

.header-user {
  max-width: 100%;
  padding: 0.65rem 0.95rem;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.65);
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  overflow-wrap: anywhere;
}

.wallet-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: rgba(17, 17, 17, 0.36);
  backdrop-filter: blur(10px);
}

.wallet-modal {
  width: min(100%, 28rem);
  display: grid;
  gap: var(--space-5);
  padding: clamp(1.2rem, 4vw, 1.6rem);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 247, 243, 0.94));
  box-shadow: var(--shadow-lg);
}

.wallet-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.wallet-modal__eyebrow {
  margin-bottom: var(--space-1);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.wallet-modal h2 {
  font-size: clamp(2rem, 8vw, 2.8rem);
  line-height: 0.94;
}

.wallet-modal__close {
  flex: 0 0 auto;
  width: 2.4rem;
  height: 2.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(17, 17, 17, 0.1);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  color: var(--color-text);
  font-size: 0.9rem;
  font-weight: 900;
  cursor: pointer;
}

.wallet-modal__close:disabled {
  cursor: wait;
  opacity: 0.6;
}

.wallet-modal__balance {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0.9rem 1rem;
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.72);
}

.wallet-modal__balance span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.wallet-modal__balance strong {
  font-size: 1.15rem;
}

.wallet-modal__form {
  display: grid;
  gap: var(--space-5);
}

.wallet-modal__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-3);
}

@media (max-width: 767px) {
  .app-header__inner {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: var(--space-3);
    padding: 0.85rem;
  }

  .brand {
    min-width: 0;
    font-size: 1rem;
  }

  .header-nav {
    grid-column: 1 / -1;
    display: flex;
    width: 100%;
  }

  .nav-link {
    flex: 1 1 100%;
    width: 100%;
    padding: 0.75rem 0.9rem;
  }

  .header-actions {
    grid-column: 2;
    width: auto;
    justify-content: flex-end;
    flex-wrap: nowrap;
    gap: var(--space-2);
  }

  .wallet-indicator {
    max-width: 8.5rem;
    padding-inline: 0.75rem;
  }

  .wallet-indicator__label {
    display: none;
  }

  .wallet-indicator__balance {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-user {
    display: none;
  }

  .header-actions :deep(.base-button) {
    min-width: auto;
    padding-inline: 0.75rem;
  }

  .wallet-modal {
    gap: var(--space-4);
    border-radius: 1.4rem;
  }

  .wallet-modal__balance,
  .wallet-modal__actions {
    align-items: stretch;
    flex-direction: column;
  }

  .wallet-modal__actions :deep(.base-button) {
    width: 100%;
  }
}

@media (min-width: 768px) {
  .app-header__inner {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
  }

  .header-nav {
    grid-column: 1 / -1;
  }
}

@media (min-width: 1024px) {
  .app-header__inner {
    min-height: 5rem;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    padding: 0.9rem 1rem;
  }

  .header-nav {
    grid-column: auto;
    justify-content: center;
  }

  .header-actions {
    justify-content: flex-end;
  }
}
</style>
