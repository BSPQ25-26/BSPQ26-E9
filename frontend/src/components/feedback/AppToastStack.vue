<script setup>
import { storeToRefs } from 'pinia'
import { useToastStore } from '@/stores/toast'

const toastStore = useToastStore()
const { toasts } = storeToRefs(toastStore)

const getToastLabel = (type) => (type === 'error' ? 'Please check' : 'Done')
</script>

<template>
  <Teleport to="body">
    <TransitionGroup
      class="toast-stack"
      name="toast"
      tag="aside"
      aria-label="Messages"
    >
      <section
        v-for="toast in toasts"
        :key="toast.id"
        class="toast-item"
        :class="`is-${toast.type}`"
        :role="toast.type === 'error' ? 'alert' : 'status'"
      >
        <div class="toast-copy">
          <span class="toast-label">
            {{ toast.title || getToastLabel(toast.type) }}
          </span>
          <p>{{ toast.message }}</p>
        </div>

        <button
          class="toast-close"
          type="button"
          aria-label="Close message"
          @click="toastStore.dismiss(toast.id)"
        >
          Close
        </button>
      </section>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  z-index: 40;
  display: grid;
  gap: var(--space-3);
  width: min(24rem, calc(100vw - 2rem));
}

.toast-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 1.45rem;
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(24px);
}

.toast-item.is-success {
  background: rgba(241, 247, 243, 0.96);
}

.toast-item.is-error {
  background: rgba(249, 239, 236, 0.98);
}

.toast-copy {
  display: grid;
  gap: var(--space-1);
}

.toast-copy p {
  font-size: var(--font-size-sm);
}

.toast-label {
  font-size: var(--font-size-xs);
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.toast-item.is-success .toast-label {
  color: var(--color-success);
}

.toast-item.is-error .toast-label {
  color: var(--color-danger);
}

.toast-close {
  min-height: var(--tap-target-size);
  min-width: var(--tap-target-size);
  padding: 0.5rem 0.75rem;
  border-radius: 0.9rem;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 1rem;
  font-weight: 700;
}

.toast-enter-active,
.toast-leave-active {
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(0.5rem);
}

@media (max-width: 720px) {
  .toast-stack {
    right: 0.5rem;
    bottom: 0.5rem;
    width: calc(100vw - 1rem);
  }
}
</style>
