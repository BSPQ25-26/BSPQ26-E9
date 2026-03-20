<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseButton from '@/components/base/BaseButton.vue'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const router = useRouter()
const { isAuthenticated, logout, user } = useAuth()

const appName = import.meta.env.VITE_APP_NAME || 'Wallabot'

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

const visibleLinks = computed(() => links.value.filter((link) => !isLinkActive(link)))

const isLinkActive = (link) => {
  if (link.exact) {
    return route.path === link.to
  }

  return route.path === link.to || route.path.startsWith(`${link.to}/`)
}

const handleLogout = async () => {
  logout()

  if (route.path !== '/login') {
    await router.push('/login')
  }
}
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">W</span>
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
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  padding-top: 0.9rem;
  background: linear-gradient(180deg, rgba(242, 241, 238, 0.94), rgba(242, 241, 238, 0.7), transparent);
  backdrop-filter: blur(18px);
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

.brand-mark {
  width: 2.4rem;
  height: 2.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  background: linear-gradient(180deg, #1f1f1f, #090909);
  color: #fff;
  box-shadow: 0 12px 26px rgba(17, 17, 17, 0.18);
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

  .header-user {
    display: none;
  }

  .header-actions :deep(.base-button) {
    min-width: auto;
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
